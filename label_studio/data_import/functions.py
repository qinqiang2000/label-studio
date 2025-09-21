import logging
import time
import traceback
from typing import Callable, Optional

from core.utils.common import conditional_atomic, db_is_not_sqlite, load_func
from django.conf import settings
from django.db import transaction
from projects.models import ProjectImport, ProjectReimport, ProjectSummary
from tasks.models import Task, Annotation, Prediction
from users.models import User
from webhooks.models import WebhookAction
from webhooks.utils import emit_webhooks_for_instance

from .models import FileUpload
from .serializers import ImportApiSerializer
from .uploader import load_tasks_for_async_import

logger = logging.getLogger(__name__)


def async_import_background(
    import_id, user_id, recalculate_stats_func: Optional[Callable[..., None]] = None, **kwargs
):
    with conditional_atomic(predicate=db_is_not_sqlite):
        try:
            project_import = ProjectImport.objects.get(id=import_id)
        except ProjectImport.DoesNotExist:
            logger.error(f'ProjectImport with id {import_id} not found, import processing failed')
            return
        if project_import.status != ProjectImport.Status.CREATED:
            logger.error(f'Processing import with id {import_id} already started')
            return
        project_import.status = ProjectImport.Status.IN_PROGRESS
        project_import.save(update_fields=['status'])

    user = User.objects.get(id=user_id)

    start = time.time()
    project = project_import.project
    tasks = None
    # upload files from request, and parse all tasks
    # TODO: Stop passing request to load_tasks function, make all validation before
    tasks, file_upload_ids, found_formats, data_columns = load_tasks_for_async_import(project_import, user)

    if project_import.preannotated_from_fields:
        # turn flat task JSONs {"column1": value, "column2": value} into {"data": {"column1"..}, "predictions": [{..."column2"}]
        tasks = reformat_predictions(tasks, project_import.preannotated_from_fields)

    if project_import.commit_to_project:
        with conditional_atomic(predicate=db_is_not_sqlite):
            # Lock summary for update to avoid race conditions
            summary = ProjectSummary.objects.select_for_update().get(project=project)

            # Immediately create project tasks and update project states and counters
            serializer = ImportApiSerializer(
                data=tasks,
                many=True,
                context={
                    'project': project,
                    'user': user,
                    'merge_strategy': project_import.merge_strategy
                }
            )
            serializer.is_valid(raise_exception=True)
            tasks = serializer.save(project_id=project.id)
            emit_webhooks_for_instance(user.active_organization, project, WebhookAction.TASKS_CREATED, tasks)

            task_count = len(tasks)
            annotation_count = len(serializer.db_annotations)
            prediction_count = len(serializer.db_predictions)
            # Update counters (like total_annotations) for new tasks and after bulk update tasks stats. It should be a
            # single operation as counters affect bulk is_labeled update

            recalculate_stats_counts = {
                'task_count': task_count,
                'annotation_count': annotation_count,
                'prediction_count': prediction_count,
            }

            project.update_tasks_counters_and_task_states(
                tasks_queryset=tasks,
                maximum_annotations_changed=False,
                overlap_cohort_percentage_changed=False,
                tasks_number_changed=True,
                recalculate_stats_counts=recalculate_stats_counts,
            )
            logger.info('Tasks bulk_update finished (async import)')

            summary.update_data_columns(tasks)
            # TODO: summary.update_created_annotations_and_labels
    else:
        # Do nothing - just output file upload ids for further use
        task_count = len(tasks)
        annotation_count = None
        prediction_count = None

    duration = time.time() - start

    project_import.task_count = task_count or 0
    project_import.annotation_count = annotation_count or 0
    project_import.prediction_count = prediction_count or 0
    project_import.duration = duration
    project_import.file_upload_ids = file_upload_ids
    project_import.found_formats = found_formats
    project_import.data_columns = data_columns
    if project_import.return_task_ids:
        project_import.task_ids = [task.id for task in tasks]

    project_import.status = ProjectImport.Status.COMPLETED
    project_import.save()


def set_import_background_failure(job, connection, type, value, _):
    import_id = job.args[0]
    ProjectImport.objects.filter(id=import_id).update(
        status=ProjectImport.Status.FAILED, traceback=traceback.format_exc(), error=str(value)
    )


def set_reimport_background_failure(job, connection, type, value, _):
    reimport_id = job.args[0]
    ProjectReimport.objects.filter(id=reimport_id).update(
        status=ProjectReimport.Status.FAILED,
        traceback=traceback.format_exc(),
        error=str(value),
    )


def reformat_predictions(tasks, preannotated_from_fields):
    new_tasks = []
    for task in tasks:
        if 'data' in task:
            task = task['data']
        predictions = [{'result': task.pop(field)} for field in preannotated_from_fields]
        new_tasks.append({'data': task, 'predictions': predictions})
    return new_tasks


post_process_reimport = load_func(settings.POST_PROCESS_REIMPORT)


def async_reimport_background(reimport_id, organization_id, user, **kwargs):

    with conditional_atomic(predicate=db_is_not_sqlite):
        try:
            reimport = ProjectReimport.objects.get(id=reimport_id)
        except ProjectReimport.DoesNotExist:
            logger.error(f'ProjectReimport with id {reimport_id} not found, import processing failed')
            return
        if reimport.status != ProjectReimport.Status.CREATED:
            logger.error(f'Processing reimport with id {reimport_id} already started')
            return
        reimport.status = ProjectReimport.Status.IN_PROGRESS
        reimport.save(update_fields=['status'])

    project = reimport.project

    tasks, found_formats, data_columns = FileUpload.load_tasks_from_uploaded_files(
        reimport.project, reimport.file_upload_ids, files_as_tasks_list=reimport.files_as_tasks_list
    )

    with conditional_atomic(predicate=db_is_not_sqlite):
        # Lock summary for update to avoid race conditions
        summary = ProjectSummary.objects.select_for_update().get(project=project)

        project.remove_tasks_by_file_uploads(reimport.file_upload_ids)
        serializer = ImportApiSerializer(data=tasks, many=True, context={'project': project, 'user': user})
        serializer.is_valid(raise_exception=True)
        tasks = serializer.save(project_id=project.id)
        emit_webhooks_for_instance(organization_id, project, WebhookAction.TASKS_CREATED, tasks)

        task_count = len(tasks)
        annotation_count = len(serializer.db_annotations)
        prediction_count = len(serializer.db_predictions)

        recalculate_stats_counts = {
            'task_count': task_count,
            'annotation_count': annotation_count,
            'prediction_count': prediction_count,
        }

        # Update counters (like total_annotations) for new tasks and after bulk update tasks stats. It should be a
        # single operation as counters affect bulk is_labeled update
        project.update_tasks_counters_and_task_states(
            tasks_queryset=tasks,
            maximum_annotations_changed=False,
            overlap_cohort_percentage_changed=False,
            tasks_number_changed=True,
            recalculate_stats_counts=recalculate_stats_counts,
        )
        logger.info('Tasks bulk_update finished (async reimport)')

        summary.update_data_columns(tasks)
        # TODO: summary.update_created_annotations_and_labels

    reimport.task_count = task_count
    reimport.annotation_count = annotation_count
    reimport.prediction_count = prediction_count
    reimport.found_formats = found_formats
    reimport.data_columns = list(data_columns)
    reimport.status = ProjectReimport.Status.COMPLETED
    reimport.save()

    post_process_reimport(reimport)


def check_task_conflicts(project, task_data_list):
    """
    Check which tasks from import data already exist in the project

    Args:
        project: Project instance
        task_data_list: List of task dictionaries to import

    Returns:
        dict: {
            'conflicts': [list of conflicting task IDs],
            'conflict_details': {task_id: existing_task_data},
            'new_tasks': [list of new task data]
        }
    """
    # Extract task IDs from import data
    import_task_ids = []
    tasks_with_ids = []
    tasks_without_ids = []

    for task_data in task_data_list:
        if 'id' in task_data:
            import_task_ids.append(task_data['id'])
            tasks_with_ids.append(task_data)
        else:
            tasks_without_ids.append(task_data)

    # Find existing tasks with matching IDs
    existing_tasks = Task.objects.filter(
        project=project,
        id__in=import_task_ids
    ).values('id', 'data', 'meta')

    existing_task_ids = {task['id'] for task in existing_tasks}
    conflict_details = {task['id']: task for task in existing_tasks}

    # Separate conflicting and new tasks
    conflicting_tasks = [task for task in tasks_with_ids if task['id'] in existing_task_ids]
    new_tasks_with_ids = [task for task in tasks_with_ids if task['id'] not in existing_task_ids]

    return {
        'conflicts': [task['id'] for task in conflicting_tasks],
        'conflict_details': conflict_details,
        'conflicting_tasks': conflicting_tasks,
        'new_tasks': new_tasks_with_ids + tasks_without_ids
    }


def merge_predictions(existing_predictions, new_predictions):
    """
    Merge predictions, replacing existing ones with same ID or appending new ones

    Args:
        existing_predictions: List of existing prediction dicts
        new_predictions: List of new prediction dicts to merge

    Returns:
        list: Merged predictions
    """
    # Create a dict of existing predictions by ID
    existing_by_id = {}
    predictions_without_id = []

    for pred in existing_predictions:
        if 'id' in pred:
            existing_by_id[pred['id']] = pred
        else:
            predictions_without_id.append(pred)

    # Process new predictions
    for new_pred in new_predictions:
        if 'id' in new_pred:
            # Replace existing prediction with same ID
            existing_by_id[new_pred['id']] = new_pred
        else:
            # Append prediction without ID
            predictions_without_id.append(new_pred)

    # Combine all predictions
    merged = list(existing_by_id.values()) + predictions_without_id
    return merged


def merge_annotations(existing_annotations, new_annotations):
    """
    Merge annotations, replacing existing ones with same ID or appending new ones

    Args:
        existing_annotations: List of existing annotation dicts
        new_annotations: List of new annotation dicts to merge

    Returns:
        list: Merged annotations
    """
    # Create a dict of existing annotations by ID
    existing_by_id = {}
    annotations_without_id = []

    for ann in existing_annotations:
        if 'id' in ann:
            existing_by_id[ann['id']] = ann
        else:
            annotations_without_id.append(ann)

    # Process new annotations
    for new_ann in new_annotations:
        if 'id' in new_ann:
            # Replace existing annotation with same ID
            existing_by_id[new_ann['id']] = new_ann
        else:
            # Append annotation without ID
            annotations_without_id.append(new_ann)

    # Combine all annotations
    merged = list(existing_by_id.values()) + annotations_without_id
    return merged


def merge_task_data(existing_task, new_task_data):
    """
    Merge task data, predictions, and annotations

    Args:
        existing_task: Task model instance
        new_task_data: Dict with new task data to merge

    Returns:
        dict: Merged task data ready for serializer
    """
    # Get existing predictions and annotations
    existing_predictions = list(
        existing_task.predictions.values(
            'id', 'result', 'score', 'model_version', 'prompt_name', 'created_at', 'updated_at'
        )
    )
    existing_annotations = list(
        existing_task.annotations.values(
            'id', 'result', 'completed_by_id', 'created_at', 'updated_at', 'was_cancelled'
        )
    )

    # Merge predictions and annotations
    merged_predictions = merge_predictions(
        existing_predictions,
        new_task_data.get('predictions', [])
    )
    merged_annotations = merge_annotations(
        existing_annotations,
        new_task_data.get('annotations', [])
    )

    # Create merged task data
    merged_task = {
        'id': existing_task.id,
        'data': new_task_data.get('data', existing_task.data),
        'meta': {**existing_task.meta, **new_task_data.get('meta', {})},
        'predictions': merged_predictions,
        'annotations': merged_annotations
    }

    return merged_task

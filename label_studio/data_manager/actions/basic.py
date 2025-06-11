"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
from datetime import datetime

from core.permissions import AllPermissions
from core.redis import start_job_async_or_sync
from core.utils.common import load_func
from data_manager.functions import evaluate_predictions
from django.conf import settings
from projects.models import Project
from tasks.functions import update_tasks_counters
from tasks.models import Annotation, AnnotationDraft, Prediction, Task
from webhooks.models import WebhookAction
from webhooks.utils import emit_webhooks_for_instance

all_permissions = AllPermissions()
logger = logging.getLogger(__name__)


def retrieve_tasks_predictions_form(user, project):
    """Form for retrieve predictions action with prompt selection"""
    # 构建 prompt 选项
    prompt_options = [{"label": "None", "value": ""}]  # 默认"无"选项
    
    # 安全地获取所有可用的 prompts
    try:
        from prompts.models import Prompt
        prompts = Prompt.objects.all().order_by('-updated_at')
        for prompt in prompts:
            prompt_options.append({
                "label": prompt.name,
                "value": prompt.name
            })
        logger.debug(f"Found {len(prompts)} prompts for selection")
    except (ImportError, AttributeError, Exception):
        # 如果 prompts 模块不存在或有其他错误，只显示"无"选项
        logger.debug("Prompts model not available, using empty prompt list")
    
    # 安全地获取用户和项目的默认选择
    default_value = ""
    try:
        from users.models import UserPreference
        preference = UserPreference.objects.filter(
            user=user,
            project=project,
            preference_key='last_selected_prompt'
        ).first()
        if preference:
            default_value = preference.preference_value
    except (ImportError, AttributeError, Exception):
        # 如果 UserPreference 模型不存在或有其他错误，使用空默认值
        logger.debug("UserPreference model not available, using empty default")
    
    return [
        {
            'columnCount': 1,
            'fields': [
                {
                    'type': 'select',
                    'name': 'prompt_name',
                    'label': 'Choose Prompt (Optional)',
                    'options': prompt_options,
                    'value': default_value,
                    'placeholder': 'Select a prompt or leave empty'
                }
            ],
        }
    ]


def retrieve_tasks_predictions(project, queryset, **kwargs):
    """Retrieve predictions by tasks ids

    :param project: project instance
    :param queryset: filtered tasks db queryset
    """
    request = kwargs.get('request')
    prompt_name = None
    
    # 从请求中获取 prompt_name
    if request and hasattr(request, 'data'):
        prompt_name = request.data.get('prompt_name')
        
        # 安全地保存用户的 prompt 选择
        if prompt_name and request.user.is_authenticated:
            try:
                from users.models import UserPreference
                preference, created = UserPreference.objects.get_or_create(
                    user=request.user,
                    project=project,
                    preference_key='last_selected_prompt',
                    defaults={'preference_value': prompt_name}
                )
                if not created:
                    preference.preference_value = prompt_name
                    preference.save()
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f'Failed to save user preference (this is safe to ignore): {e}')
    
    # 调用 evaluate_predictions 并传递 prompt_name
    logger.info(f"🎯 [PROMPT DEBUG] Calling evaluate_predictions with prompt_name: '{prompt_name}' for {queryset.count()} tasks")
    evaluate_predictions(queryset, prompt_name=prompt_name)
    return {'processed_items': queryset.count(), 'detail': 'Retrieved ' + str(queryset.count()) + ' predictions'}


def delete_tasks(project, queryset, **kwargs):
    """Delete tasks by ids

    :param project: project instance
    :param queryset: filtered tasks db queryset
    """
    tasks_ids = list(queryset.values('id'))
    count = len(tasks_ids)
    tasks_ids_list = [task['id'] for task in tasks_ids]
    project_count = project.tasks.count()
    # unlink tasks from project
    queryset = Task.objects.filter(id__in=tasks_ids_list)
    queryset.update(project=None)
    # delete all project tasks
    if count == project_count:
        start_job_async_or_sync(Task.delete_tasks_without_signals_from_task_ids, tasks_ids_list)
        logger.info(f'calling reset project_id={project.id} delete_tasks()')
        project.summary.reset()

    # delete only specific tasks
    else:
        # update project summary and delete tasks
        start_job_async_or_sync(async_project_summary_recalculation, tasks_ids_list, project.id)

    project.update_tasks_states(
        maximum_annotations_changed=False, overlap_cohort_percentage_changed=False, tasks_number_changed=True
    )
    # emit webhooks for project
    emit_webhooks_for_instance(project.organization, project, WebhookAction.TASKS_DELETED, tasks_ids)

    # remove all tabs if there are no tasks in project
    reload = False
    if not project.tasks.exists():
        project.views.all().delete()
        reload = True

    # Execute actions after delete tasks
    Task.after_bulk_delete_actions(tasks_ids_list, project)

    return {'processed_items': count, 'reload': reload, 'detail': 'Deleted ' + str(count) + ' tasks'}


def delete_tasks_annotations(project, queryset, **kwargs):
    """Delete all annotations and drafts by tasks ids

    :param project: project instance
    :param queryset: filtered tasks db queryset
    """
    task_ids = queryset.values_list('id', flat=True)
    annotations = Annotation.objects.filter(task__id__in=task_ids)
    count = annotations.count()

    # take only tasks where annotations were deleted
    real_task_ids = set(list(annotations.values_list('task__id', flat=True)))
    annotations_ids = list(annotations.values('id'))
    # remove deleted annotations from project.summary
    project.summary.remove_created_annotations_and_labels(annotations)
    # also remove drafts for the task. This includes task and annotation level
    # drafts by design.
    drafts = AnnotationDraft.objects.filter(task__id__in=task_ids)
    project.summary.remove_created_drafts_and_labels(drafts)

    annotations.delete()
    drafts.delete()  # since task-level annotation drafts will not have been deleted by CASCADE
    emit_webhooks_for_instance(project.organization, project, WebhookAction.ANNOTATIONS_DELETED, annotations_ids)
    request = kwargs['request']

    tasks = Task.objects.filter(id__in=real_task_ids)
    tasks.update(updated_at=datetime.now(), updated_by=request.user)
    # Update tasks counter and is_labeled. It should be a single operation as counters affect bulk is_labeled update
    project.update_tasks_counters_and_is_labeled(tasks_queryset=real_task_ids)

    # LSE postprocess
    postprocess = load_func(settings.DELETE_TASKS_ANNOTATIONS_POSTPROCESS)
    if postprocess is not None:
        tasks = Task.objects.filter(id__in=task_ids)
        postprocess(project, tasks, **kwargs)

    return {'processed_items': count, 'detail': 'Deleted ' + str(count) + ' annotations'}


def delete_tasks_predictions(project, queryset, **kwargs):
    """Delete all predictions by tasks ids

    :param project: project instance
    :param queryset: filtered tasks db queryset
    """
    task_ids = queryset.values_list('id', flat=True)
    predictions = Prediction.objects.filter(task__id__in=task_ids)
    real_task_ids = set(list(predictions.values_list('task__id', flat=True)))
    count = predictions.count()
    predictions.delete()
    start_job_async_or_sync(update_tasks_counters, Task.objects.filter(id__in=real_task_ids))
    return {'processed_items': count, 'detail': 'Deleted ' + str(count) + ' predictions'}


def async_project_summary_recalculation(tasks_ids_list, project_id):
    queryset = Task.objects.filter(id__in=tasks_ids_list)
    project = Project.objects.get(id=project_id)
    project.summary.remove_created_annotations_and_labels(Annotation.objects.filter(task__in=queryset))
    project.summary.remove_data_columns(queryset)
    Task.delete_tasks_without_signals(queryset)


actions = [
    {
        'entry_point': retrieve_tasks_predictions,
        'permission': all_permissions.predictions_any,
        'title': 'Retrieve Predictions',
        'order': 90,
        'dialog': {
            'title': 'Retrieve Predictions',
            'text': 'Send the selected tasks to all ML backends connected to the project. '
            'You can optionally select a prompt to use for prediction generation. '
            'This operation might be abruptly interrupted due to a timeout. '
            'The recommended way to get predictions is to update tasks using the Label Studio API. '
            'Please confirm your action.',
            'type': 'confirm',
            'form': retrieve_tasks_predictions_form,
        },
    },
    {
        'entry_point': delete_tasks,
        'permission': all_permissions.tasks_delete,
        'title': 'Delete Tasks',
        'order': 100,
        'reload': True,
        'dialog': {
            'text': 'You are going to delete the selected tasks. Please confirm your action.',
            'type': 'confirm',
        },
    },
    {
        'entry_point': delete_tasks_annotations,
        'permission': all_permissions.tasks_delete,
        'title': 'Delete Annotations',
        'order': 101,
        'dialog': {
            'text': 'You are going to delete all annotations from the selected tasks. Please confirm your action.',
            'type': 'confirm',
        },
    },
    {
        'entry_point': delete_tasks_predictions,
        'permission': all_permissions.predictions_any,
        'title': 'Delete Predictions',
        'order': 102,
        'dialog': {
            'text': 'You are going to delete all predictions from the selected tasks. Please confirm your action.',
            'type': 'confirm',
        },
    },
]

"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
import os
import pathlib

import drf_yasg.openapi as openapi
from core.filters import ListFilter
from core.label_config import config_essential_data_has_changed
from core.mixins import GetParentObjectMixin
from core.permissions import ViewClassPermission, all_permissions
from core.redis import start_job_async_or_sync
from core.utils.common import paginator, paginator_help, temporary_disconnect_all_signals
from core.utils.exceptions import LabelStudioDatabaseException, ProjectExistException
from core.utils.io import find_dir, find_file, read_yaml
from data_manager.functions import filters_ordering_selected_items_exist, get_prepared_queryset
from django.conf import settings
from django.db import IntegrityError
from django.db.models import F
from django.http import Http404
from django.utils.decorators import method_decorator
from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from label_studio_sdk.label_interface.interface import LabelInterface
from ml.serializers import MLBackendSerializer
from projects.functions.next_task import get_next_task
from projects.functions.stream_history import get_label_stream_history
from projects.functions.utils import recalculate_created_annotations_and_labels_from_scratch
from projects.models import Project, ProjectImport, ProjectManager, ProjectReimport, ProjectSummary
from projects.serializers import (
    GetFieldsSerializer,
    ProjectCountsSerializer,
    ProjectImportSerializer,
    ProjectLabelConfigSerializer,
    ProjectModelVersionExtendedSerializer,
    ProjectReimportSerializer,
    ProjectSerializer,
    ProjectSummarySerializer,
)
from rest_framework import filters, generics, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError as RestValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler
from tasks.models import Task, Annotation, Prediction
from tasks.serializers import (
    NextTaskSerializer,
    TaskSerializer,
    TaskSimpleSerializer,
    TaskWithAnnotationsAndPredictionsAndDraftsSerializer,
)
from webhooks.models import WebhookAction
from webhooks.utils import api_webhook, api_webhook_for_delete, emit_webhooks_for_instance

from label_studio.core.utils.common import load_func

logger = logging.getLogger(__name__)

ProjectImportPermission = load_func(settings.PROJECT_IMPORT_PERMISSION)

_result_schema = openapi.Schema(
    title='Labeling result',
    description='Labeling result (choices, labels, bounding boxes, etc.)',
    type=openapi.TYPE_OBJECT,
    properties={
        'from_name': openapi.Schema(
            title='from_name',
            description='The name of the labeling tag from the project config',
            type=openapi.TYPE_STRING,
        ),
        'to_name': openapi.Schema(
            title='to_name',
            description='The name of the labeling tag from the project config',
            type=openapi.TYPE_STRING,
        ),
        'value': openapi.Schema(
            title='value',
            description='Labeling result value. Format depends on chosen ML backend',
            type=openapi.TYPE_OBJECT,
        ),
    },
    example={'from_name': 'image_class', 'to_name': 'image', 'value': {'labels': ['Cat']}},
)

_task_data_schema = openapi.Schema(
    title='Task data',
    description='Task data',
    type=openapi.TYPE_OBJECT,
    example={'id': 1, 'my_image_url': '/static/samples/kittens.jpg'},
)

_project_schema = openapi.Schema(
    title='Project',
    description='Project',
    type=openapi.TYPE_OBJECT,
    properties={
        'title': openapi.Schema(
            title='title',
            description='Project title',
            type=openapi.TYPE_STRING,
            example='My project',
        ),
        'description': openapi.Schema(
            title='description',
            description='Project description',
            type=openapi.TYPE_STRING,
            example='My first project',
        ),
        'label_config': openapi.Schema(
            title='label_config',
            description='Label config in XML format',
            type=openapi.TYPE_STRING,
            example='<View>[...]</View>',
        ),
        'expert_instruction': openapi.Schema(
            title='expert_instruction',
            description='Labeling instructions to show to the user',
            type=openapi.TYPE_STRING,
            example='Label all cats',
        ),
        'show_instruction': openapi.Schema(
            title='show_instruction',
            description='Show labeling instructions',
            type=openapi.TYPE_BOOLEAN,
        ),
        'show_skip_button': openapi.Schema(
            title='show_skip_button',
            description='Show skip button',
            type=openapi.TYPE_BOOLEAN,
        ),
        'enable_empty_annotation': openapi.Schema(
            title='enable_empty_annotation',
            description='Allow empty annotations',
            type=openapi.TYPE_BOOLEAN,
        ),
        'show_annotation_history': openapi.Schema(
            title='show_annotation_history',
            description='Show annotation history',
            type=openapi.TYPE_BOOLEAN,
        ),
        'reveal_preannotations_interactively': openapi.Schema(
            title='reveal_preannotations_interactively',
            description='Reveal preannotations interactively. If set to True, predictions will be shown to the user only after selecting the area of interest',
            type=openapi.TYPE_BOOLEAN,
        ),
        'show_collab_predictions': openapi.Schema(
            title='show_collab_predictions',
            description='Show predictions to annotators',
            type=openapi.TYPE_BOOLEAN,
        ),
        'maximum_annotations': openapi.Schema(
            title='maximum_annotations',
            description='Maximum annotations per task',
            type=openapi.TYPE_INTEGER,
        ),
        'color': openapi.Schema(
            title='color',
            description='Project color in HEX format',
            type=openapi.TYPE_STRING,
            default='#FFFFFF',
        ),
        'control_weights': openapi.Schema(
            title='control_weights',
            description='Dict of weights for each control tag in metric calculation. Each control tag (e.g. label or choice) will '
            'have its own key in control weight dict with weight for each label and overall weight. '
            'For example, if a bounding box annotation with a control tag named my_bbox should be included with 0.33 weight in agreement calculation, '
            'and the first label Car should be twice as important as Airplane, then you need to specify: '
            "{'my_bbox': {'type': 'RectangleLabels', 'labels': {'Car': 1.0, 'Airplane': 0.5}, 'overall': 0.33}",
            type=openapi.TYPE_OBJECT,
            example={
                'my_bbox': {'type': 'RectangleLabels', 'labels': {'Car': 1.0, 'Airplaine': 0.5}, 'overall': 0.33}
            },
        ),
    },
)


class ProjectListPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'


class ProjectFilterSet(FilterSet):
    ids = ListFilter(field_name='id', lookup_expr='in')
    title = CharFilter(field_name='title', lookup_expr='icontains')


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='list',
        x_fern_audiences=['public'],
        x_fern_pagination={
            'offset': '$request.page',
            'results': '$response.results',
        },
        operation_summary='List your projects',
        operation_description="""
    Return a list of the projects that you've created.

    To perform most tasks with the Label Studio API, you must specify the project ID, sometimes referred to as the `pk`.
    To retrieve a list of your Label Studio projects, update the following command to match your own environment.
    Replace the domain name, port, and authorization token, then run the following from the command line:
    ```bash
    curl -X GET {}/api/projects/ -H 'Authorization: Token abc123'
    ```
    """.format(
            settings.HOSTNAME or 'https://localhost:8080'
        ),
    ),
)
@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        operation_summary='Create new project',
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='create',
        x_fern_audiences=['public'],
        operation_description="""
    Create a project and set up the labeling interface in Label Studio using the API.

    ```bash
    curl -H Content-Type:application/json -H 'Authorization: Token abc123' -X POST '{}/api/projects' \
    --data '{{"title": "My project", "label_config": "<View></View>"}}'
    ```
    """.format(
            settings.HOSTNAME or 'https://localhost:8080'
        ),
        request_body=_project_schema,
    ),
)
class ProjectListAPI(generics.ListCreateAPIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    serializer_class = ProjectSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = ProjectFilterSet
    permission_required = ViewClassPermission(
        GET=all_permissions.projects_view,
        POST=all_permissions.projects_create,
    )
    pagination_class = ProjectListPagination

    def get_queryset(self):
        from django.db.models import Q
        serializer = GetFieldsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data.get('include')
        filter = serializer.validated_data.get('filter')
        projects = Project.objects.filter(organization=self.request.user.active_organization).order_by(
            F('pinned_at').desc(nulls_last=True), '-created_at'
        )
        
        # Filter projects based on workspace membership (unless user is superuser)
        if not self.request.user.is_superuser:
            projects = projects.filter(
                Q(workspace__isnull=True) |  # Projects without workspace
                Q(workspace__members=self.request.user)  # Projects in workspaces where user is a member
            )
        
        if filter in ['pinned_only', 'exclude_pinned']:
            projects = projects.filter(pinned_at__isnull=filter == 'exclude_pinned')
        return ProjectManager.with_counts_annotate(projects, fields=fields).prefetch_related('members', 'created_by')

    def get_serializer_context(self):
        context = super(ProjectListAPI, self).get_serializer_context()
        context['created_by'] = self.request.user
        return context

    def perform_create(self, ser):
        try:
            ser.save(organization=self.request.user.active_organization)
        except IntegrityError as e:
            if str(e) == 'UNIQUE constraint failed: project.title, project.created_by_id':
                raise ProjectExistException(
                    'Project with the same name already exists: {}'.format(ser.validated_data.get('title', ''))
                )
            raise LabelStudioDatabaseException('Database error during project creation. Try again.')
        except Exception as e:
            # Enhanced error handling for project creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Project creation failed: {str(e)}")
            logger.error(f"Request data: {self.request.data}")
            
            # Provide more specific error messages
            if 'JSON' in str(e) or 'json' in str(e).lower():
                raise RestValidationError({
                    'detail': 'Invalid JSON format in request data',
                    'error_type': 'json_parse_error',
                    'original_error': str(e)
                })
            elif 'validation' in str(e).lower():
                raise RestValidationError({
                    'detail': 'Data validation failed',
                    'error_type': 'validation_error',
                    'original_error': str(e)
                })
            else:
                raise RestValidationError({
                    'detail': 'Project creation failed due to server error',
                    'error_type': 'server_error',
                    'original_error': str(e)
                })

    def get(self, request, *args, **kwargs):
        return super(ProjectListAPI, self).get(request, *args, **kwargs)

    @api_webhook(WebhookAction.PROJECT_CREATED)
    def post(self, request, *args, **kwargs):
        return super(ProjectListAPI, self).post(request, *args, **kwargs)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='counts',
        x_fern_audiences=['public'],
        x_fern_pagination={
            'offset': '$request.page',
            'results': '$response.results',
        },
        operation_summary="List project's counts",
        operation_description='Returns a list of projects with their counts. For example, task_number which is the total task number in project',
    ),
)
class ProjectCountsListAPI(generics.ListAPIView):
    serializer_class = ProjectCountsSerializer
    filterset_class = ProjectFilterSet
    permission_required = ViewClassPermission(
        GET=all_permissions.projects_view,
    )
    pagination_class = ProjectListPagination

    def get_queryset(self):
        from django.db.models import Q
        serializer = GetFieldsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data.get('include')
        projects = Project.objects.with_counts(fields=fields).filter(organization=self.request.user.active_organization)
        
        # Filter projects based on workspace membership (unless user is superuser)  
        if not self.request.user.is_superuser:
            projects = projects.filter(
                Q(workspace__isnull=True) |  # Projects without workspace
                Q(workspace__members=self.request.user)  # Projects in workspaces where user is a member
            )
        
        return projects


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='get',
        x_fern_audiences=['public'],
        operation_summary='Get project by ID',
        operation_description='Retrieve information about a project by project ID.',
        responses={
            '200': openapi.Response(
                description='Project information',
                schema=ProjectSerializer,
                examples={
                    'application/json': {
                        'id': 1,
                        'title': 'My project',
                        'description': 'My first project',
                        'label_config': '<View>[...]</View>',
                        'expert_instruction': 'Label all cats',
                        'show_instruction': True,
                        'show_skip_button': True,
                        'enable_empty_annotation': True,
                        'show_annotation_history': True,
                        'organization': 1,
                        'color': '#FF0000',
                        'maximum_annotations': 1,
                        'is_published': True,
                        'model_version': '1.0.0',
                        'is_draft': False,
                        'created_by': {
                            'id': 1,
                            'first_name': 'Jo',
                            'last_name': 'Doe',
                            'email': 'manager@humansignal.com',
                        },
                        'created_at': '2023-08-24T14:15:22Z',
                        'min_annotations_to_start_training': 0,
                        'start_training_on_annotation_update': True,
                        'show_collab_predictions': True,
                        'num_tasks_with_annotations': 10,
                        'task_number': 100,
                        'useful_annotation_number': 10,
                        'ground_truth_number': 5,
                        'skipped_annotations_number': 0,
                        'total_annotations_number': 10,
                        'total_predictions_number': 0,
                        'sampling': 'Sequential sampling',
                        'show_ground_truth_first': True,
                        'show_overlap_first': True,
                        'overlap_cohort_percentage': 100,
                        'task_data_login': 'user',
                        'task_data_password': 'secret',
                        'control_weights': {},
                        'parsed_label_config': '{"tag": {...}}',
                        'evaluate_predictions_automatically': False,
                        'config_has_control_tags': True,
                        'skip_queue': 'REQUEUE_FOR_ME',
                        'reveal_preannotations_interactively': True,
                        'pinned_at': '2023-08-24T14:15:22Z',
                        'finished_task_number': 10,
                        'queue_total': 10,
                        'queue_done': 100,
                    }
                },
            )
        },
    ),
)
@method_decorator(
    name='delete',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='delete',
        x_fern_audiences=['public'],
        operation_summary='Delete project',
        operation_description='Delete a project by specified project ID.',
    ),
)
@method_decorator(
    name='patch',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='update',
        x_fern_audiences=['public'],
        operation_summary='Update project',
        operation_description='Update the project settings for a specific project.',
        request_body=_project_schema,
    ),
)
class ProjectAPI(generics.RetrieveUpdateDestroyAPIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    queryset = Project.objects.with_counts()
    permission_required = ViewClassPermission(
        GET=all_permissions.projects_view,
        DELETE=all_permissions.projects_delete,
        PATCH=all_permissions.projects_change,
        PUT=all_permissions.projects_change,
        POST=all_permissions.projects_create,
    )
    serializer_class = ProjectSerializer

    redirect_route = 'projects:project-detail'
    redirect_kwarg = 'pk'

    def get_queryset(self):
        from django.db.models import Q
        serializer = GetFieldsSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        fields = serializer.validated_data.get('include')
        projects = Project.objects.with_counts(fields=fields).filter(organization=self.request.user.active_organization)
        
        # Filter projects based on workspace membership (unless user is superuser)  
        if not self.request.user.is_superuser:
            projects = projects.filter(
                Q(workspace__isnull=True) |  # Projects without workspace
                Q(workspace__members=self.request.user)  # Projects in workspaces where user is a member
            )
        
        return projects

    def get(self, request, *args, **kwargs):
        return super(ProjectAPI, self).get(request, *args, **kwargs)

    @api_webhook_for_delete(WebhookAction.PROJECT_DELETED)
    def delete(self, request, *args, **kwargs):
        return super(ProjectAPI, self).delete(request, *args, **kwargs)

    @api_webhook(WebhookAction.PROJECT_UPDATED)
    def patch(self, request, *args, **kwargs):
        project = self.get_object()
        label_config = self.request.data.get('label_config')

        # config changes can break view, so we need to reset them
        if label_config:
            try:
                _has_changes = config_essential_data_has_changed(label_config, project.label_config)
            except KeyError:
                pass

        return super(ProjectAPI, self).patch(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # we don't need to relaculate counters if we delete whole project
        with temporary_disconnect_all_signals():
            instance.delete()

    @swagger_auto_schema(auto_schema=None)
    @api_webhook(WebhookAction.PROJECT_UPDATED)
    def put(self, request, *args, **kwargs):
        return super(ProjectAPI, self).put(request, *args, **kwargs)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='duplicate',
        x_fern_audiences=['public'],
        operation_summary='Duplicate project',
        operation_description='Create a complete copy of a project including all tasks, annotations and predictions.',
        manual_parameters=[
            openapi.Parameter(
                name='id',
                type=openapi.TYPE_INTEGER,
                in_=openapi.IN_PATH,
                description='A unique integer value identifying the source project to duplicate.',
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'title': openapi.Schema(
                    title='title',
                    description='Title for the new project',
                    type=openapi.TYPE_STRING,
                    example='My project (Copy)',
                ),
                'workspace': openapi.Schema(
                    title='workspace',
                    description='Workspace ID for the new project (optional)',
                    type=openapi.TYPE_INTEGER,
                    example=1,
                ),
            },
            required=['title'],
        ),
        responses={
            201: openapi.Response(
                description='Project duplicated successfully',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'title': openapi.Schema(type=openapi.TYPE_STRING),
                        'task_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'annotation_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'prediction_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: openapi.Response(description='Invalid request data'),
            404: openapi.Response(description='Source project not found'),
        },
    ),
)
class ProjectDuplicateAPI(generics.CreateAPIView):
    """Duplicate a project with all tasks, annotations and predictions"""
    
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_required = ViewClassPermission(
        POST=all_permissions.projects_create,
    )
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        """Filter projects based on user permissions"""
        from django.db.models import Q
        projects = Project.objects.filter(organization=self.request.user.active_organization)
        
        # Filter projects based on workspace membership (unless user is superuser)
        if not self.request.user.is_superuser:
            projects = projects.filter(
                Q(workspace__isnull=True) |  # Projects without workspace
                Q(workspace__members=self.request.user)  # Projects in workspaces where user is a member
            )
        
        return projects

    def post(self, request, *args, **kwargs):
        """Duplicate a project with all its data"""
        from django.db import transaction
        
        source_project_id = kwargs.get('pk')
        source_project = generics.get_object_or_404(self.get_queryset(), pk=source_project_id)
        self.check_object_permissions(request, source_project)
        
        # Get request data
        new_title = request.data.get('title')
        workspace_id = request.data.get('workspace')
        
        if not new_title:
            return Response(
                {'error': 'title is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Step 1: Duplicate the project
                new_project = self._duplicate_project(source_project, new_title, workspace_id, request.user)
                
                # Step 2: Duplicate all tasks
                task_count = self._duplicate_tasks(source_project, new_project)
                
                # Step 3: Duplicate annotations and predictions
                annotation_count, prediction_count = self._duplicate_annotations_and_predictions(
                    source_project, new_project
                )
                
                # Step 4: Update project summary/stats
                new_project.summary.reset()
                
                logger.info(
                    f'Successfully duplicated project {source_project.id} -> {new_project.id}: '
                    f'{task_count} tasks, {annotation_count} annotations, {prediction_count} predictions'
                )
                
                return Response({
                    'id': new_project.id,
                    'title': new_project.title,
                    'task_count': task_count,
                    'annotation_count': annotation_count,
                    'prediction_count': prediction_count,
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f'Failed to duplicate project {source_project_id}: {str(e)}')
            return Response(
                {'error': f'Failed to duplicate project: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _duplicate_project(self, source_project, new_title, workspace_id, user):
        """Create a new project with copied settings"""
        from workspaces.models import Workspace
        
        # Create new project with copied settings
        new_project = Project(
            title=new_title,
            description=source_project.description,
            label_config=source_project.label_config,
            expert_instruction=source_project.expert_instruction,
            show_instruction=source_project.show_instruction,
            show_skip_button=source_project.show_skip_button,
            enable_empty_annotation=source_project.enable_empty_annotation,
            show_annotation_history=source_project.show_annotation_history,
            reveal_preannotations_interactively=source_project.reveal_preannotations_interactively,
            show_collab_predictions=source_project.show_collab_predictions,
            maximum_annotations=source_project.maximum_annotations,
            color=source_project.color,
            control_weights=source_project.control_weights,
            organization=user.active_organization,
            created_by=user,
            # Copy other relevant fields
            min_annotations_to_start_training=source_project.min_annotations_to_start_training,
            show_ground_truth_first=source_project.show_ground_truth_first,
            show_overlap_first=source_project.show_overlap_first,
            overlap_cohort_percentage=source_project.overlap_cohort_percentage,
            task_data_login=source_project.task_data_login,
            task_data_password=source_project.task_data_password,
            evaluate_predictions_automatically=source_project.evaluate_predictions_automatically,
            skip_queue=source_project.skip_queue,
            sampling=source_project.sampling,
        )
        
        # Set workspace if provided
        if workspace_id:
            workspace = generics.get_object_or_404(
                Workspace.objects.filter(organization=user.active_organization), 
                pk=workspace_id
            )
            new_project.workspace = workspace
        
        new_project.save()
        return new_project

    def _duplicate_tasks(self, source_project, new_project):
        """Duplicate all tasks from source to new project"""
        tasks = Task.objects.filter(project=source_project)
        task_count = 0
        
        for task in tasks:
            # Create new task with copied data
            new_task = Task(
                data=task.data,
                meta=task.meta,
                project=new_project,
                overlap=task.overlap,
                is_labeled=False,  # Reset labeling status
                # Copy file upload reference if exists
                file_upload=task.file_upload,
            )
            new_task.save()
            task_count += 1
        
        return task_count

    def _duplicate_annotations_and_predictions(self, source_project, new_project):
        """Duplicate annotations and predictions for all tasks"""
        annotation_count = 0
        prediction_count = 0
        
        # Get task mappings (source task ID -> new task)
        source_tasks = Task.objects.filter(project=source_project).order_by('id')
        new_tasks = Task.objects.filter(project=new_project).order_by('id')
        
        # Create task mapping based on order (should match 1:1)
        task_mapping = {}
        for source_task, new_task in zip(source_tasks, new_tasks):
            task_mapping[source_task.id] = new_task
        
        # Duplicate annotations
        for source_task_id, new_task in task_mapping.items():
            # Copy annotations
            annotations = Annotation.objects.filter(task_id=source_task_id)
            for annotation in annotations:
                new_annotation = Annotation(
                    task=new_task,
                    result=annotation.result,
                    completed_by=annotation.completed_by,
                    was_cancelled=annotation.was_cancelled,
                    ground_truth=annotation.ground_truth,
                    parent_annotation=None,  # Don't copy parent relationship
                    parent_prediction=None,  # Don't copy parent relationship
                    project=new_project,
                    # Note: created_at and updated_at will be set automatically
                )
                new_annotation.save()
                annotation_count += 1
            
            # Copy predictions
            predictions = Prediction.objects.filter(task_id=source_task_id)
            for prediction in predictions:
                new_prediction = Prediction(
                    task=new_task,
                    result=prediction.result,
                    score=prediction.score,
                    model_version=prediction.model_version,
                    prompt_name=prediction.prompt_name,
                    model=prediction.model,
                    model_run=prediction.model_run,
                    cluster=prediction.cluster,
                    neighbors=prediction.neighbors,
                    mislabeling=prediction.mislabeling,
                    project=new_project,
                )
                new_prediction.save()
                prediction_count += 1
        
        return annotation_count, prediction_count


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        operation_summary='Get next task to label',
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='next_task',
        x_fern_audiences=['public'],
        operation_description="""
    Get the next task for labeling. If you enable Machine Learning in
    your project, the response might include a "predictions"
    field. It contains a machine learning prediction result for
    this task.
    """,
        responses={200: TaskWithAnnotationsAndPredictionsAndDraftsSerializer()},
    ),
)  # leaving this method decorator info in case we put it back in swagger API docs
class ProjectNextTaskAPI(generics.RetrieveAPIView):
    permission_required = all_permissions.tasks_view
    serializer_class = TaskWithAnnotationsAndPredictionsAndDraftsSerializer  # using it for swagger API docs
    queryset = Project.objects.all()
    swagger_schema = None  # this endpoint doesn't need to be in swagger API docs

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        dm_queue = filters_ordering_selected_items_exist(request.data)
        prepared_tasks = get_prepared_queryset(request, project)

        next_task, queue_info = get_next_task(request.user, prepared_tasks, project, dm_queue)

        if next_task is None:
            raise NotFound(
                f'There are still some tasks to complete for the user={request.user}, '
                f'but they seem to be locked by another user.'
            )

        # serialize task
        context = {'request': request, 'project': project, 'resolve_uri': True, 'annotations': False}
        serializer = NextTaskSerializer(next_task, context=context)
        response = serializer.data

        response['queue'] = queue_info
        return Response(response)


class LabelStreamHistoryAPI(generics.RetrieveAPIView):
    permission_required = all_permissions.tasks_view
    queryset = Project.objects.all()
    swagger_schema = None  # this endpoint doesn't need to be in swagger API docs

    def get(self, request, *args, **kwargs):
        project = self.get_object()

        history = get_label_stream_history(request.user, project)

        return Response(history)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_audiences=['internal'],
        operation_summary='Validate label config',
        operation_description='Validate an arbitrary labeling configuration.',
        responses={204: 'Validation success'},
        request_body=ProjectLabelConfigSerializer,
    ),
)
class LabelConfigValidateAPI(generics.CreateAPIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_classes = (AllowAny,)
    serializer_class = ProjectLabelConfigSerializer

    def post(self, request, *args, **kwargs):
        return super(LabelConfigValidateAPI, self).post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except RestValidationError as exc:
            context = self.get_exception_handler_context()
            response = exception_handler(exc, context)
            response = self.finalize_response(request, response)
            return response

        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        operation_id='api_projects_validate_label_config',
        operation_summary='Validate project label config',
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='validate_config',
        x_fern_audiences=['public'],
        operation_description="""
        Determine whether the label configuration for a specific project is valid.
        """,
        manual_parameters=[
            openapi.Parameter(
                name='id',
                type=openapi.TYPE_INTEGER,
                in_=openapi.IN_PATH,
                description='A unique integer value identifying this project.',
            ),
        ],
        request_body=ProjectLabelConfigSerializer,
    ),
)
class ProjectLabelConfigValidateAPI(generics.RetrieveAPIView):
    """Validate label config"""

    parser_classes = (JSONParser, FormParser, MultiPartParser)
    serializer_class = ProjectLabelConfigSerializer
    permission_required = all_permissions.projects_change
    queryset = Project.objects.all()

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        label_config = self.request.data.get('label_config')
        if not label_config:
            raise RestValidationError('Label config is not set or is empty')

        # check new config includes meaningful changes
        has_changed = config_essential_data_has_changed(label_config, project.label_config)
        project.validate_config(label_config, strict=True)
        return Response({'config_essential_data_has_changed': has_changed}, status=status.HTTP_200_OK)

    @swagger_auto_schema(auto_schema=None)
    def get(self, request, *args, **kwargs):
        return super(ProjectLabelConfigValidateAPI, self).get(request, *args, **kwargs)


class ProjectSummaryAPI(generics.RetrieveAPIView):
    parser_classes = (JSONParser,)
    serializer_class = ProjectSummarySerializer
    permission_required = all_permissions.projects_view
    queryset = ProjectSummary.objects.all()

    @swagger_auto_schema(auto_schema=None)
    def get(self, *args, **kwargs):
        return super(ProjectSummaryAPI, self).get(*args, **kwargs)


class ProjectSummaryResetAPI(GetParentObjectMixin, generics.CreateAPIView):
    """This API is useful when we need to reset project.summary.created_labels and created_labels_drafts
    and recalculate them from scratch. It's hard to correctly follow all changes in annotation region
    labels and these fields aren't calculated properly after some time. Label config changes are not allowed
    when these changes touch any labels from these created_labels* dictionaries.
    """

    parser_classes = (JSONParser,)
    parent_queryset = Project.objects.all()
    permission_required = ViewClassPermission(
        POST=all_permissions.projects_change,
    )

    @swagger_auto_schema(auto_schema=None)
    def post(self, *args, **kwargs):
        project = self.parent_object
        summary = project.summary
        start_job_async_or_sync(
            recalculate_created_annotations_and_labels_from_scratch,
            project,
            summary,
            organization_id=self.request.user.active_organization.id,
        )
        return Response(status=status.HTTP_200_OK)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='tasks',
        x_fern_sdk_method_name='create_many_status',
        x_fern_audiences=['public'],
        operation_summary='Get project import info',
        operation_description='Return data related to async project import operation',
        manual_parameters=[
            openapi.Parameter(
                name='id',
                type=openapi.TYPE_INTEGER,
                in_=openapi.IN_PATH,
                description='A unique integer value identifying this project import.',
            ),
        ],
    ),
)
class ProjectImportAPI(generics.RetrieveAPIView):
    permission_required = all_permissions.projects_change
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [ProjectImportPermission]
    parser_classes = (JSONParser,)
    serializer_class = ProjectImportSerializer
    queryset = ProjectImport.objects.all()
    lookup_url_kwarg = 'import_pk'


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_audiences=['internal'],
        operation_summary='Get project reimport info',
        operation_description='Return data related to async project reimport operation',
        manual_parameters=[
            openapi.Parameter(
                name='id',
                type=openapi.TYPE_INTEGER,
                in_=openapi.IN_PATH,
                description='A unique integer value identifying this project reimport.',
            ),
        ],
    ),
)
class ProjectReimportAPI(generics.RetrieveAPIView):
    permission_required = all_permissions.projects_change
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES + [ProjectImportPermission]
    parser_classes = (JSONParser,)
    serializer_class = ProjectReimportSerializer
    queryset = ProjectReimport.objects.all()
    lookup_url_kwarg = 'reimport_pk'


@method_decorator(
    name='delete',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_sdk_group_name='projects',
        x_fern_sdk_method_name='delete_all_tasks',
        x_fern_audiences=['public'],
        operation_summary='Delete all tasks',
        operation_description='Delete all tasks from a specific project.',
        manual_parameters=[
            openapi.Parameter(
                name='id',
                type=openapi.TYPE_INTEGER,
                in_=openapi.IN_PATH,
                description='A unique integer value identifying this project.',
            ),
        ],
        responses={204: 'Tasks deleted'},
    ),
)
@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Projects'],
        x_fern_audiences=['internal'],  # TODO: deprecate this endpoint in favor of tasks:tasks-list
        operation_summary='List project tasks',
        operation_description="""
            Retrieve a paginated list of tasks for a specific project. For example, use the following cURL command:
            ```bash
            curl -X GET {}/api/projects/{{id}}/tasks/?page=1&page_size=10 -H 'Authorization: Token abc123'
            ```
        """.format(
            settings.HOSTNAME or 'https://localhost:8080'
        ),
        manual_parameters=[
            openapi.Parameter(
                name='id',
                type=openapi.TYPE_INTEGER,
                in_=openapi.IN_PATH,
                description='A unique integer value identifying this project.',
            ),
        ]
        + paginator_help('tasks', 'Projects')['manual_parameters'],
    ),
)
class ProjectTaskListAPI(GetParentObjectMixin, generics.ListCreateAPIView, generics.DestroyAPIView):
    parser_classes = (JSONParser, FormParser)
    queryset = Task.objects.all()
    parent_queryset = Project.objects.all()
    permission_required = ViewClassPermission(
        GET=all_permissions.tasks_view,
        POST=all_permissions.tasks_change,
        DELETE=all_permissions.tasks_delete,
    )
    serializer_class = TaskSerializer
    redirect_route = 'projects:project-settings'
    redirect_kwarg = 'pk'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TaskSimpleSerializer
        else:
            return TaskSerializer

    def filter_queryset(self, queryset):
        project = generics.get_object_or_404(Project.objects.for_user(self.request.user), pk=self.kwargs.get('pk', 0))
        # ordering is deprecated here
        tasks = Task.objects.filter(project=project).order_by('-updated_at')
        page = paginator(tasks, self.request)
        if page:
            return page
        else:
            raise Http404

    def delete(self, request, *args, **kwargs):
        project = generics.get_object_or_404(Project.objects.for_user(self.request.user), pk=self.kwargs['pk'])
        task_ids = list(Task.objects.filter(project=project).values('id'))
        Task.delete_tasks_without_signals(Task.objects.filter(project=project))
        logger.info(f'calling reset project_id={project.id} ProjectTaskListAPI.delete()')
        project.summary.reset()
        emit_webhooks_for_instance(request.user.active_organization, None, WebhookAction.TASKS_DELETED, task_ids)
        return Response(status=204)

    def get(self, *args, **kwargs):
        return super(ProjectTaskListAPI, self).get(*args, **kwargs)

    @swagger_auto_schema(auto_schema=None)
    def post(self, *args, **kwargs):
        return super(ProjectTaskListAPI, self).post(*args, **kwargs)

    def get_serializer_context(self):
        context = super(ProjectTaskListAPI, self).get_serializer_context()
        context['project'] = self.parent_object
        return context

    def perform_create(self, serializer):
        project = self.parent_object
        instance = serializer.save(project=project)
        emit_webhooks_for_instance(
            self.request.user.active_organization, project, WebhookAction.TASKS_CREATED, [instance]
        )
        return instance


def read_templates_and_groups():
    annotation_templates_dir = find_dir('annotation_templates')
    configs = []
    for config_file in pathlib.Path(annotation_templates_dir).glob('**/*.yml'):
        config = read_yaml(config_file)
        if settings.VERSION_EDITION == 'Community':
            if settings.VERSION_EDITION.lower() != config.get('type', 'community'):
                continue
        if config.get('image', '').startswith('/static') and settings.HOSTNAME:
            # if hostname set manually, create full image urls
            config['image'] = settings.HOSTNAME + config['image']
        configs.append(config)
    template_groups_file = find_file(os.path.join('annotation_templates', 'groups.txt'))
    with open(template_groups_file, encoding='utf-8') as f:
        groups = f.read().splitlines()
    logger.debug(f'{len(configs)} templates found.')
    return {'templates': configs, 'groups': groups}


class TemplateListAPI(generics.ListAPIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    permission_required = all_permissions.projects_view
    swagger_schema = None
    # load this once in memory for performance
    templates_and_groups = read_templates_and_groups()

    def list(self, request, *args, **kwargs):
        return Response(self.templates_and_groups)


class ProjectSampleTask(generics.RetrieveAPIView):
    parser_classes = (JSONParser,)
    queryset = Project.objects.all()
    permission_required = all_permissions.projects_view
    serializer_class = ProjectSerializer
    swagger_schema = None

    def post(self, request, *args, **kwargs):
        label_config = self.request.data.get('label_config')
        include_annotation_and_prediction = self.request.data.get('include_annotation_and_prediction', False)

        if not label_config:
            raise RestValidationError('Label config is not set or is empty')

        project = self.get_object()

        if include_annotation_and_prediction:
            try:
                label_interface = LabelInterface(label_config)
                complete_task = label_interface.generate_complete_sample_task(raise_on_failure=True)
                # set the annotation's user id to the current user instead of -1
                user_id = request.user.id
                for annotation in complete_task['annotations']:
                    annotation['completed_by'] = user_id
                return Response({'sample_task': complete_task}, status=200)
            except Exception as e:
                logger.error(
                    f'Error generating enhanced sample task, falling back to original method: {str(e)}. Label config: {label_config}'
                )
                # Fallback to project.get_sample_task if LabelInterface.generate_complete_sample_task failed
                return Response({'sample_task': project.get_sample_task(label_config)}, status=200)
        else:
            # Use the simple sample task generation method
            return Response({'sample_task': project.get_sample_task(label_config)}, status=200)


class ProjectModelVersions(generics.RetrieveAPIView):
    parser_classes = (JSONParser,)
    swagger_schema = None
    permission_required = all_permissions.projects_view
    queryset = Project.objects.all()

    def get(self, request, *args, **kwargs):
        # TODO make sure "extended" is the right word and is
        # consistent with other APIs we've got
        extended = self.request.query_params.get('extended', False)
        include_live_models = self.request.query_params.get('include_live_models', False)
        project = self.get_object()
        data = project.get_model_versions(with_counters=True, extended=extended)

        if extended:
            serializer_models = None
            serializer = ProjectModelVersionExtendedSerializer(data, many=True)

            if include_live_models:
                ml_models = project.get_ml_backends()
                serializer_models = MLBackendSerializer(ml_models, many=True)

            # serializer.is_valid(raise_exception=True)
            return Response({'static': serializer.data, 'live': serializer_models and serializer_models.data})
        else:
            return Response(data=data)

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        model_version = request.data.get('model_version', None)

        if not model_version:
            raise RestValidationError('model_version param is required')

        count = project.delete_predictions(model_version=model_version)

        return Response(data=count)

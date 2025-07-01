"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging
from collections import OrderedDict
from typing import Any, Iterable, Tuple
from urllib.parse import unquote

import ujson as json
from core.utils.common import int_from_request
from data_manager.models import View
from data_manager.prepare_params import PrepareParams
from django.conf import settings
from rest_framework.generics import get_object_or_404
from tasks.models import Task

TASKS = 'tasks:'
logger = logging.getLogger(__name__)


class DataManagerException(Exception):
    pass


def get_all_columns(project, *_):
    """Make columns info for the frontend data manager"""
    result = {'columns': []}

    # frontend uses MST data model, so we need two directional referencing parent <-> child
    task_data_children = []
    i = 0

    data_types = OrderedDict()

    # add data types from config again
    project_data_types = {}
    for key, value in project.data_types.items():
        # skip keys from Repeater tag, because we already have its base data,
        # e.g.: skip 'image[{{idx}}]' because we have 'image' list already
        if '[' not in key:
            project_data_types[key] = value
    data_types.update(project_data_types.items())

    # all data types from import data
    all_data_columns = project.summary.all_data_columns
    logger.info(f'get_all_columns: project_id={project.id} {all_data_columns=} {data_types=}')
    if all_data_columns:
        data_types.update({key: 'Unknown' for key in all_data_columns if key not in data_types})
    logger.info(f'get_all_columns: project_id={project.id} {data_types=}')

    # remove $undefined$ if there is one type at least in labeling config, because it will be resolved automatically
    if len(project_data_types) > 0:
        data_types.pop(settings.DATA_UNDEFINED_NAME, None)
    logger.info(f'get_all_columns: project_id={project.id} {data_types=} {project_data_types=}')

    for key, data_type in list(data_types.items()):  # make data types from labeling config first
        column = {
            'id': key,
            'title': key if key != settings.DATA_UNDEFINED_NAME else 'data',
            'type': data_type if data_type in ['Image', 'Audio', 'AudioPlus', 'Video', 'Unknown'] else 'String',
            'target': 'tasks',
            'parent': 'data',
            'visibility_defaults': {
                'explore': True,
                'labeling': key in project_data_types or key == settings.DATA_UNDEFINED_NAME,
            },
            'project_defined': True,
        }
        result['columns'].append(column)
        task_data_children.append(column['id'])
        i += 1

    # --- Data root ---
    data_root = {
        'id': 'data',
        'title': 'data',
        'type': 'List',
        'target': 'tasks',
        'children': task_data_children,
        'project_defined': False,
    }

    result['columns'] += [
        # --- Tasks ---
        {
            'id': 'id',
            'title': 'ID',
            'type': 'Number',
            'help': 'Task ID',
            'target': 'tasks',
            'visibility_defaults': {'explore': True, 'labeling': False},
            'project_defined': False,
        }
    ]

    result['columns'] += [
        {
            'id': 'inner_id',
            'title': 'Inner ID',
            'type': 'Number',
            'help': 'Internal task ID starting from 1 for the current project',
            'target': 'tasks',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        }
    ]

    project_members = project.all_members.values_list('id', flat=True)

    result['columns'] += [
        {
            'id': 'completed_at',
            'title': 'Completed',
            'type': 'Datetime',
            'target': 'tasks',
            'help': 'Last annotation date',
            'visibility_defaults': {'explore': True, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'total_annotations',
            'title': 'Annotations',
            'type': 'Number',
            'target': 'tasks',
            'help': 'Total annotations per task',
            'visibility_defaults': {'explore': True, 'labeling': True},
            'project_defined': False,
        },
        {
            'id': 'cancelled_annotations',
            'title': 'Cancelled',
            'type': 'Number',
            'target': 'tasks',
            'help': 'Total cancelled (skipped) annotations',
            'visibility_defaults': {'explore': True, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'total_predictions',
            'title': 'Predictions',
            'type': 'Number',
            'target': 'tasks',
            'help': 'Total predictions per task',
            'visibility_defaults': {'explore': True, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'annotators',
            'title': 'Annotated by',
            'type': 'List',
            'target': 'tasks',
            'help': 'All users who completed the task',
            'schema': {'items': project_members},
            'visibility_defaults': {'explore': True, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'annotations_results',
            'title': 'Annotation results',
            'type': 'String',
            'target': 'tasks',
            'help': 'Annotation results stacked over all annotations',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'annotations_ids',
            'title': 'Annotation IDs',
            'type': 'String',
            'target': 'tasks',
            'help': 'Annotation IDs stacked over all annotations',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'predictions_score',
            'title': 'Prediction score',
            'type': 'Number',
            'target': 'tasks',
            'help': 'Average prediction score over all task predictions',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'predictions_model_versions',
            'title': 'Prediction model versions',
            'type': 'List',
            'target': 'tasks',
            'help': 'Model versions aggregated over all predictions',
            'schema': {'items': project.get_model_versions()},
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'predictions_results',
            'title': 'Prediction results',
            'type': 'String',
            'target': 'tasks',
            'help': 'Prediction results stacked over all predictions',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'predictions_prompt_names',
            'title': 'Prediction prompt names',
            'type': 'List',
            'target': 'tasks',
            'help': 'Prompt names used for predictions',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'file_upload',
            'title': 'Upload filename',
            'type': 'String',
            'target': 'tasks',
            'help': 'Filename of uploaded file',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'storage_filename',
            'title': 'Storage filename',
            'type': 'String',
            'target': 'tasks',
            'help': 'Filename from import storage',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'created_at',
            'title': 'Created at',
            'type': 'Datetime',
            'target': 'tasks',
            'help': 'Task creation time',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'updated_at',
            'title': 'Updated at',
            'type': 'Datetime',
            'target': 'tasks',
            'help': 'Task update time',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'updated_by',
            'title': 'Updated by',
            'type': 'List',
            'target': 'tasks',
            'help': 'User who did the last task update',
            'schema': {'items': project_members},
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'avg_lead_time',
            'title': 'Lead Time',
            'type': 'Number',
            'help': 'Average lead time over all annotations (seconds)',
            'target': 'tasks',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
        {
            'id': 'draft_exists',
            'title': 'Drafts',
            'type': 'Boolean',
            'help': 'True if at least one draft exists for the task',
            'target': 'tasks',
            'visibility_defaults': {'explore': False, 'labeling': False},
            'project_defined': False,
        },
    ]

    result['columns'].append(data_root)

    return result


def get_prepare_params(request, project):
    """This function extract prepare_params from
    * view_id if it's inside of request data
    * selectedItems, filters, ordering if they are in request and there is no view id
    """
    # use filters and selected items from view
    view_id = int_from_request(request.GET, 'view', 0) or int_from_request(request.data, 'view', 0)
    if view_id > 0:
        view = get_object_or_404(View, pk=view_id)
        if view.project.pk != project.pk:
            raise DataManagerException('Project and View mismatch')
        prepare_params = view.get_prepare_tasks_params(add_selected_items=True)
        prepare_params.request = request

    # use filters and selected items from request if it's specified
    else:
        # query arguments from url
        if 'query' in request.GET:
            data = json.loads(unquote(request.GET['query']))
        # data payload from body
        else:
            data = request.data

        selected = data.get('selectedItems', {'all': True, 'excluded': []})
        if not isinstance(selected, dict):
            if isinstance(selected, str):
                # try to parse JSON string
                try:
                    selected = json.loads(selected)
                except Exception as e:
                    logger.error(f'Error parsing selectedItems: {e}')
                    raise DataManagerException(
                        'selectedItems must be JSON encoded string for dict: {"all": [true|false], '
                        '"excluded | included": [...task_ids...]}. '
                        f'Found: {selected}'
                    )
            else:
                raise DataManagerException(
                    'selectedItems must be dict: {"all": [true|false], '
                    '"excluded | included": [...task_ids...]}. '
                    f'Found type: {type(selected)} with value: {selected}'
                )
        filters = data.get('filters', None)
        ordering = data.get('ordering', [])
        prepare_params = PrepareParams(
            project=project.id, selectedItems=selected, data=data, filters=filters, ordering=ordering, request=request
        )
    return prepare_params


def get_prepared_queryset(request, project):
    prepare_params = get_prepare_params(request, project)
    queryset = Task.prepared.only_filtered(prepare_params=prepare_params)
    return queryset


def evaluate_predictions(tasks, prompt_name=None, model_version=None, project=None):
    """
    Call the given ML backend to retrieve predictions with the task queryset as an input.
    If backend is not specified, we'll assume the tasks' project only has one associated
    ML backend, and use that backend.
    
    :param tasks: task queryset
    :param prompt_name: optional prompt name to use for prediction generation
    :param model_version: optional model version to use for prediction generation
    :param project: project instance (optional, will be derived from tasks if not provided)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 调试输出
    print(f"\n🔥 EVALUATE_PREDICTIONS CALLED:")
    print(f"🔥 prompt_name: '{prompt_name}'")
    print(f"🔥 model_version: '{model_version}'")
    try:
        tasks_count = tasks.count() if hasattr(tasks, 'count') and not isinstance(tasks, list) else len(tasks)
    except TypeError:
        tasks_count = len(tasks)
    print(f"🔥 tasks count: {tasks_count}")
    print(f"🔥 project: {project}")
    logger.info(f"🔥 [EVALUATE] RECEIVED: prompt_name='{prompt_name}', model_version='{model_version}'")
    
    if not tasks:
        logger.info("🎯 [PARAMS DEBUG] No tasks provided to evaluate_predictions")
        return

    # 使用传入的项目实例，如果没有则从 tasks 中获取
    if project is None:
        project = tasks[0].project
    
    logger.info(f"🎯 [PARAMS DEBUG] evaluate_predictions called for project '{project.title}' (ID: {project.id}) with prompt_name: '{prompt_name}', model_version: '{model_version}'")

    backend = project.ml_backend

    if backend:
        logger.info(f"🎯 [PARAMS DEBUG] Found ML backend '{backend.title}', calling predict_tasks")
        result = backend.predict_tasks(tasks=tasks, prompt_name=prompt_name, model_version=model_version)
        
        # 处理新的返回格式（包含错误信息）
        if isinstance(result, dict) and 'errors' in result:
            errors = result.get('errors', [])
            if errors:
                logger.warning(f"🎯 [ML ERRORS] evaluate_predictions收到 {len(errors)} 个ML错误")
                logger.info(f"🎯 [ML ERRORS] 错误详情: {errors}")
                # 将错误信息存储到项目实例中
                project._last_ml_errors = errors
                logger.info(f"🎯 [ML ERRORS] 已将错误信息存储到项目 {project.id}")
        elif result is None:
            # 处理没有ML backend的情况
            logger.info("🎯 [PARAMS DEBUG] No ML backend result")
        else:
            # 兼容旧格式（直接返回model_version字符串或instances列表）
            logger.info(f"🎯 [PARAMS DEBUG] 收到旧格式结果: {type(result)}")
            # 清除之前的错误信息
            if hasattr(project, '_last_ml_errors'):
                delattr(project, '_last_ml_errors')
        
        return result
    else:
        logger.warning(f"🎯 [PARAMS DEBUG] No ML backend found for project '{project.title}'")


def filters_ordering_selected_items_exist(data):
    return data.get('filters') or data.get('ordering') or data.get('selectedItems')


def custom_filter_expressions(*args, **kwargs):
    pass


def preprocess_filter(_filter, *_):
    return _filter


def preprocess_field_name(raw_field_name, project) -> Tuple[str, bool]:
    """Transform a field name (as specified in the datamanager views endpoint) to
    a django ORM field name. Also handle dotted accesses to task.data.

    Edit with care; it's critical that this function not be changed in ways that
    introduce vulnerabilities in the vein of the ORM Leak (see #5012). In particular
    it is not advisable to use `replace` or other calls that replace all instances
    of a string within this function.

    Returns: Django ORM field name: str, Sort is ascending: bool
    """

    field_name = raw_field_name
    ascending = True

    # Descending marker `-` may come at the beginning of the string
    if field_name.startswith('-'):
        ascending = False
        field_name = field_name[1:]

    # For security reasons, these must only be removed when they fall at the beginning of the string (or after `-`).
    optional_prefixes = ['filter:', 'tasks:']
    for prefix in optional_prefixes:
        if field_name.startswith(prefix):
            field_name = field_name[len(prefix) :]

    # Descending marker may also come after other prefixes. Double negative is not allowed.
    if ascending and field_name.startswith('-'):
        ascending = False
        field_name = field_name[1:]

    if field_name.startswith('data.'):
        # process as $undefined$ only if real_name is from labeling config, not from task.data
        real_name = field_name.replace('data.', '')
        common_data_columns = project.summary.common_data_columns
        real_name_suitable = (
            # there is only one object tag in labeling config
            # and requested filter name == value from object tag
            len(project.data_types.keys()) == 1
            and real_name in project.data_types.keys()
            # file was uploaded before labeling config is set, `data.data` is system predefined name
            or len(project.data_types.keys()) == 0
            and real_name == 'data'
        )
        if (
            real_name_suitable
            # common data columns are not None
            and common_data_columns
            # $undefined$ is in common data columns, in all tasks
            and settings.DATA_UNDEFINED_NAME in common_data_columns
        ):
            field_name = f'data__{settings.DATA_UNDEFINED_NAME}'
        else:
            field_name = field_name.replace('data.', 'data__')
    return field_name, ascending


def intersperse(items: Iterable, separator: Any) -> list:
    """
    Create a list with a separator between each item in the passed iterable `items`

    for example, intersperse(['one', 'two', 'three'], 0) == ['one', 0, 'two', 0, 'three']
    """

    output = []
    for item in items:
        output.append(item)
        output.append(separator)
    # if there are no items, there will be no last separator to remove
    if output:
        output.pop()
    return output

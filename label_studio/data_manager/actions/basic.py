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
    """Form for retrieve predictions action with prompt and model version selection"""
    # 构建 prompt 选项
    prompt_options = [{"label": "None", "value": ""}]  # 默认"无"选项
    default_prompt_value = ""
    
    # 安全地获取可用的 prompts（限制数量）
    try:
        from prompts.models import Prompt
        # 限制最多显示10个最新的prompts
        prompts = Prompt.objects.all().order_by('-updated_at')[:10]
        for prompt in prompts:
            prompt_options.append({
                "label": prompt.name,
                "value": prompt.name
            })
        logger.debug(f"Found {len(prompts)} prompts for selection (limited to 10)")
        
        # 如果有可用的 prompts，默认选择第一个（最新的）
        if prompts:
            default_prompt_value = prompts[0].name
            logger.debug(f"Setting default prompt to: {default_prompt_value}")
            
    except (ImportError, AttributeError, Exception):
        # 如果 prompts 模块不存在或有其他错误，只显示"无"选项
        logger.debug("Prompts model not available, using empty prompt list")
    
    # 如果用户有保存的偏好，使用用户偏好而不是默认值
    try:
        from users.models import UserPreference
        preference = UserPreference.objects.filter(
            user=user,
            project=project,
            preference_key='last_selected_prompt'
        ).first()
        if preference and preference.preference_value:
            # 检查用户偏好的prompt是否还存在
            if any(option['value'] == preference.preference_value for option in prompt_options):
                default_prompt_value = preference.preference_value
                logger.debug(f"Using user preference: {default_prompt_value}")
    except (ImportError, AttributeError, Exception):
        # 如果 UserPreference 模型不存在或有其他错误，使用默认值
        logger.debug("UserPreference model not available, using default prompt")
    
    # 构建 model version 选项
    model_version_options = [{"label": "Use Default", "value": ""}]  # 默认选项
    default_model_version = ""
    
    # 从当前ML backend获取版本信息
    if project.ml_backend:
        try:
            # 获取可用的处理器版本
            versions_response = project.ml_backend.get_versions()
            if not versions_response.is_error:
                available_versions = versions_response.response.get('versions', [])
                for version_info in available_versions:
                    processor_type = version_info.get('processor_type', 'Unknown')
                    model_name = version_info.get('model_name', 'Unknown')
                    description = version_info.get('description', f'{processor_type} {model_name}')
                    version_string = version_info.get('version_string', f"{processor_type}|{model_name}")
                    
                    model_version_options.append({
                        "label": description,
                        "value": version_string
                    })
                
                logger.debug(f"Found {len(available_versions)} model versions from ML backend")
            else:
                logger.debug(f"ML backend get_versions failed: {versions_response.error_message}")
        except Exception as e:
            logger.debug(f"Could not fetch ML backend versions: {e}")
    
    # 从项目历史预测中获取已使用的版本（限制数量）
    try:
        existing_versions = project.get_model_versions()
        current_values = [opt['value'] for opt in model_version_options]
        
        logger.debug(f"Historical versions found: {existing_versions}")
        logger.debug(f"Current option values: {current_values}")
        
        # 只添加不在当前版本列表中的历史版本，并限制数量
        historical_count = 0
        max_historical = 3  # 最多显示3个历史版本
        
        for version in existing_versions:
            if (version and 
                version not in current_values and 
                historical_count < max_historical):
                
                # 创建用户友好的显示标签
                display_label = version
                logger.debug(f"Processing historical version: '{version}' (type: {type(version)})")
                
                if '|' in str(version):
                    # 解析格式为 "processor_type|model_name" 的版本字符串
                    try:
                        processor_type, model_name = str(version).split('|', 1)
                        display_label = f"{processor_type.title()} {model_name}"
                        logger.debug(f"Parsed version: {processor_type} | {model_name} -> {display_label}")
                    except ValueError:
                        # 如果分割失败，使用原始字符串
                        display_label = str(version)
                        logger.debug(f"Failed to parse version, using raw: {display_label}")
                else:
                    display_label = str(version)
                    logger.debug(f"No pipe delimiter, using raw: {display_label}")
                
                final_option = {
                    "label": f"{display_label} (Historical)",
                    "value": str(version)
                }
                model_version_options.append(final_option)
                logger.debug(f"Added historical option: {final_option}")
                historical_count += 1
        
        logger.debug(f"Added {historical_count} historical model versions (max: {max_historical})")
    except Exception as e:
        logger.debug(f"Could not fetch historical model versions: {e}")
    
    # 获取用户的model version偏好
    try:
        from users.models import UserPreference
        preference = UserPreference.objects.filter(
            user=user,
            project=project,
            preference_key='last_selected_model_version'
        ).first()
        if preference and preference.preference_value:
            # 检查用户偏好的model version是否还存在
            if any(option['value'] == preference.preference_value for option in model_version_options):
                default_model_version = preference.preference_value
                logger.debug(f"Using user model version preference: {default_model_version}")
    except (ImportError, AttributeError, Exception):
        logger.debug("UserPreference model not available for model version")
    
    return [
        {
            'columnCount': 2,  # 改为2列布局
            'fields': [
                {
                    'type': 'select',
                    'name': 'prompt_name',
                    'label': 'Prompt',
                    'options': prompt_options,
                    'value': default_prompt_value,
                    'placeholder': 'Select prompt'
                },
                {
                    'type': 'select',
                    'name': 'model_version',
                    'label': 'Model Version',
                    'options': model_version_options,
                    'value': default_model_version,
                    'placeholder': 'Select model'
                }
            ],
        }
    ]


def retrieve_tasks_predictions(project, queryset, **kwargs):
    """Retrieve predictions by tasks ids

    :param project: project instance
    :param queryset: filtered tasks db queryset
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("🔥" * 50)
    logger.info(f"🚀 [ACTION] retrieve_tasks_predictions STARTED")
    logger.info(f"🚀 [ACTION] Project: {project.title} (ID: {project.id})")
    logger.info(f"🚀 [ACTION] Queryset count: {queryset.count()}")
    logger.info(f"🚀 [ACTION] Kwargs keys: {list(kwargs.keys())}")
    
    request = kwargs.get('request')
    prompt_name = None
    
    if request:
        logger.info(f"🚀 [ACTION] Request method: {request.method}")
        logger.info(f"🚀 [ACTION] Request data: {getattr(request, 'data', {})}")
        logger.info(f"🚀 [ACTION] Request GET: {getattr(request, 'GET', {})}")
        logger.info(f"🚀 [ACTION] Request POST: {getattr(request, 'POST', {})}")
    else:
        logger.info(f"🚀 [ACTION] No request object found!")
    
    logger.info("🔥" * 50)
    
    # 首先检查项目是否有ML后端配置
    if not project.has_ml_backend():
        logger.warning(f"Project '{project.title}' (ID: {project.id}) has no ML backend configured")
        return {
            'processed_items': 0,
            'detail': 'No ML backend configured for this project. Please configure an ML backend in project settings.',
            'error': 'no_ml_backend',
            'error_message': 'No ML backend configured for this project. Please configure an ML backend in project settings.'
        }
    
    # 检查ML后端状态
    ml_backend = project.ml_backend
    if ml_backend:
        from ml.models import MLBackendState
        if ml_backend.state == MLBackendState.DISCONNECTED:
            logger.warning(f"ML backend '{ml_backend.title}' for project '{project.title}' is disconnected")
            return {
                'processed_items': 0,
                'detail': f'ML backend "{ml_backend.title}" is disconnected. Please check the backend connection.',
                'error': 'ml_backend_disconnected',
                'error_message': f'ML backend "{ml_backend.title}" is disconnected. Please check the backend connection in project settings.'
            }
        elif ml_backend.state == MLBackendState.ERROR:
            error_msg = ml_backend.error_message or 'Unknown error'
            logger.warning(f"ML backend '{ml_backend.title}' for project '{project.title}' has error: {error_msg}")
            return {
                'processed_items': 0,
                'detail': f'ML backend "{ml_backend.title}" has an error: {error_msg}',
                'error': 'ml_backend_error',
                'error_message': f'ML backend "{ml_backend.title}" has an error: {error_msg}'
            }
        elif ml_backend.state not in [MLBackendState.CONNECTED, MLBackendState.TRAINING, MLBackendState.PREDICTING]:
            logger.warning(f"ML backend '{ml_backend.title}' for project '{project.title}' is not ready (state: {ml_backend.state})")
            return {
                'processed_items': 0,
                'detail': f'ML backend "{ml_backend.title}" is not ready (state: {ml_backend.get_state_display()}). Please wait or check the backend status.',
                'error': 'ml_backend_not_ready',
                'error_message': f'ML backend "{ml_backend.title}" is not ready (state: {ml_backend.get_state_display()}). Please wait or check the backend status.'
            }
    
    # 从请求中获取 prompt_name 和 model_version
    logger.info(f"🎯 [PARAMS] Extracting parameters from request...")
    prompt_name = None
    model_version = None
    
    if request and hasattr(request, 'data'):
        prompt_name = request.data.get('prompt_name')
        model_version = request.data.get('model_version')
        logger.info(f"🎯 [PARAMS] Found prompt_name in request.data: '{prompt_name}'")
        logger.info(f"🎯 [PARAMS] Found model_version in request.data: '{model_version}'")
        
        # 安全地保存用户的 prompt 选择
        if prompt_name and request.user.is_authenticated:
            logger.info(f"🎯 [PROMPT] Saving user preference for prompt: '{prompt_name}'")
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
                logger.info(f"🎯 [PROMPT] User preference saved successfully")
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f'Failed to save user prompt preference (this is safe to ignore): {e}')
        
        # 安全地保存用户的 model version 选择
        if model_version and request.user.is_authenticated:
            logger.info(f"🎯 [MODEL_VERSION] Saving user preference for model_version: '{model_version}'")
            try:
                from users.models import UserPreference
                preference, created = UserPreference.objects.get_or_create(
                    user=request.user,
                    project=project,
                    preference_key='last_selected_model_version',
                    defaults={'preference_value': model_version}
                )
                if not created:
                    preference.preference_value = model_version
                    preference.save()
                logger.info(f"🎯 [MODEL_VERSION] User preference saved successfully")
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f'Failed to save user model version preference (this is safe to ignore): {e}')
        
        if not prompt_name and not model_version:
            logger.info(f"🎯 [PARAMS] No parameters found, authenticated: {request.user.is_authenticated if request else False}")
    else:
        logger.info(f"🎯 [PARAMS] No request.data found or request is None")
        logger.info(f"🎯 [PARAMS] Request exists: {request is not None}")
        logger.info(f"🎯 [PARAMS] Request has data attr: {hasattr(request, 'data') if request else False}")
        
    logger.info(f"🎯 [PARAMS] Final values - prompt_name: '{prompt_name}', model_version: '{model_version}'")
    
    # 额外的调试输出，强制打印
    print(f"\n🔥 ACTION DEBUG:")
    print(f"🔥 prompt_name: '{prompt_name}'")
    print(f"🔥 model_version: '{model_version}'")
    print(f"🔥 About to call evaluate_predictions with these values")
    print(f"🔥 END ACTION DEBUG\n")
    
    # 调用 evaluate_predictions 并传递 prompt_name 和 model_version
    logger.info("=" * 80)
    logger.info(f"🔥 [EVALUATE] About to call evaluate_predictions")
    logger.info(f"🔥 [EVALUATE] prompt_name: '{prompt_name}'")
    logger.info(f"🔥 [EVALUATE] model_version: '{model_version}'")
    logger.info(f"🔥 [EVALUATE] tasks count: {queryset.count()}")
    logger.info(f"🔥 [EVALUATE] project: {project.title} (ID: {project.id})")
    logger.info("=" * 80)
    
    # 清除之前的错误信息
    if hasattr(project, '_last_ml_errors'):
        delattr(project, '_last_ml_errors')
    
    result = evaluate_predictions(queryset, prompt_name=prompt_name, model_version=model_version, project=project)
    
    logger.info("=" * 80)
    logger.info(f"🔥 [EVALUATE] evaluate_predictions returned")
    logger.info(f"🔥 [EVALUATE] result type: {type(result)}")
    logger.info(f"🔥 [EVALUATE] result: {result}")
    logger.info("=" * 80)
    
    # 检查是否有ML错误
    ml_errors = getattr(project, '_last_ml_errors', [])
    logger.info(f"🎯 [ML ERRORS] Action检查错误信息: 找到 {len(ml_errors)} 个错误")
    
    response = {
        'processed_items': queryset.count(), 
        'detail': 'Retrieved ' + str(queryset.count()) + ' predictions'
    }
    
    # 如果有错误，添加到响应中
    if ml_errors:
        logger.warning(f"🎯 [ML ERRORS] Action完成，发现 {len(ml_errors)} 个ML错误")
        logger.info(f"🎯 [ML ERRORS] 错误详情: {ml_errors}")
        response['ml_errors'] = ml_errors
        response['detail'] += f' (with {len(ml_errors)} errors from ML backend)'
        
        # 构建错误摘要
        error_summary = {}
        for error in ml_errors:
            error_type = error.get('error_type', 'unknown')
            error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        response['error_summary'] = error_summary
        logger.info(f"🎯 [ML ERRORS] 最终响应: {response}")
    else:
        logger.info(f"🎯 [ML ERRORS] 没有发现ML错误，返回标准响应")
    
    # 强制调试：直接检查项目对象
    logger.info(f"🎯 [DEBUG] 项目对象 ID: {project.id}, 类型: {type(project)}")
    logger.info(f"🎯 [DEBUG] 项目对象属性: {[attr for attr in dir(project) if attr.startswith('_last')]}")
    
    return response


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

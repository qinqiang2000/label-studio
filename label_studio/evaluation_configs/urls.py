from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import EvaluationFieldConfigViewSet, ProjectEvaluationConfigViewSet
from . import frontend_api

app_name = 'evaluation_configs'

router = DefaultRouter()
router.register(r'evaluation-configs', EvaluationFieldConfigViewSet, basename='evaluation-configs')
router.register(r'project-configs', ProjectEvaluationConfigViewSet, basename='project-configs')

urlpatterns = [
    path('api/', include(router.urls)),
    # Frontend-specific endpoints  
    path('api/frontend/evaluation-configs/active/', frontend_api.get_available_configs, name='frontend-get-available-configs'),
    path('api/frontend/evaluation-configs/project/<int:project_id>/', frontend_api.get_project_config, name='frontend-get-project-config'),
    path('api/frontend/evaluation-configs/key/<str:config_key>/', frontend_api.get_config_by_key, name='frontend-get-config-by-key'),
] 
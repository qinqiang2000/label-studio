from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import WorkspaceViewSet
from . import views

app_name = 'workspaces'

router = DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')

# API URLs
_api_urlpatterns = router.urls

# View URLs  
_urlpatterns = [
    path('', views.workspaces_list, name='workspaces-list'),
]

urlpatterns = [
    path('workspaces/', include(_urlpatterns)),
    path('api/', include(_api_urlpatterns)),
] 
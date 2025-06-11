from django.urls import include, path
from . import api, views

app_name = 'prompts'

# API URLs
_api_urlpatterns = [
    path('', api.PromptListAPI.as_view(), name='prompt-list'),
    path('<int:pk>/', api.PromptDetailAPI.as_view(), name='prompt-detail'),
]

# View URLs
_urlpatterns = [
    path('', views.prompts_list, name='prompts-list'),
]

urlpatterns = [
    path('prompts/', include(_urlpatterns)),
    path('api/prompts/', include((_api_urlpatterns, app_name), namespace='api')),
] 
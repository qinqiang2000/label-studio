from rest_framework import generics, permissions
from .models import Prompt
from .serializers import PromptSerializer
from .permissions import PromptsAccessPermission, IsPromptOwnerOrSuperuserForWrite


def _visible_prompts_for(user):
    """超管可见全部；普通用户仅可见所属 workspace 的 prompt。"""
    qs = Prompt.objects.select_related('workspace', 'created_by')
    if user.is_superuser:
        return qs
    return qs.filter(workspace__members=user).distinct()


class PromptListAPI(generics.ListCreateAPIView):
    """List visible prompts in the user's workspaces, or create a new prompt."""

    serializer_class = PromptSerializer
    permission_classes = [permissions.IsAuthenticated, PromptsAccessPermission]

    def get_queryset(self):
        return _visible_prompts_for(self.request.user)


class PromptDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a prompt.

    Read: workspace-member or superuser (queryset enforced).
    Write/Delete: creator or superuser (object-level permission).
    """

    serializer_class = PromptSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        PromptsAccessPermission,
        IsPromptOwnerOrSuperuserForWrite,
    ]

    def get_queryset(self):
        return _visible_prompts_for(self.request.user)

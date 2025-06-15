import logging
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.utils.common import create_hash

logger = logging.getLogger(__name__)


class Workspace(models.Model):
    """
    Workspace model for organizing projects
    """
    name = models.CharField(
        _('name'),
        max_length=256,
        help_text='Workspace name'
    )
    
    description = models.TextField(
        _('description'),
        blank=True,
        null=True,
        default='',
        help_text='Workspace description'
    )
    
    color = models.CharField(
        _('color'),
        max_length=16,
        default='#1976d2',
        help_text='Workspace color for UI'
    )
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='workspaces',
        help_text='Organization this workspace belongs to'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_workspaces',
        help_text='User who created this workspace'
    )
    
    is_archived = models.BooleanField(
        _('is archived'),
        default=False,
        help_text='Whether this workspace is archived'
    )
    
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='WorkspaceMember',
        related_name='workspaces',
        help_text='Users who have access to this workspace'
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'workspace'
        ordering = ['-created_at']
        unique_together = ['name', 'organization']
        
    def __str__(self):
        return f"{self.name} ({self.organization.title})"
    
    def has_member(self, user):
        """Check if user is a member of this workspace"""
        return self.members.filter(pk=user.pk).exists()
    
    def add_member(self, user):
        """Add user as a member of this workspace"""
        if not self.has_member(user):
            WorkspaceMember.objects.create(
                workspace=self,
                user=user
            )
    
    def remove_member(self, user):
        """Remove user from this workspace"""
        WorkspaceMember.objects.filter(
            workspace=self,
            user=user
        ).delete()
    
    def get_member_ids(self):
        """Get list of member user IDs"""
        return list(self.members.values_list('pk', flat=True))


class WorkspaceMember(models.Model):
    """
    Through model for workspace membership
    """
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='workspace_members',
        help_text='Workspace'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
        help_text='User'
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'workspace_member'
        unique_together = ['workspace', 'user']
        
    def __str__(self):
        return f"{self.user.email} - {self.workspace.name}"

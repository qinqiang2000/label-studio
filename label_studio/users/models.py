"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import datetime
from typing import Optional

from core.utils.common import load_func
from core.utils.db import fast_first
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization
from rest_framework.authtoken.models import Token
from users.functions import hash_upload

YEAR_START = 1980
YEAR_CHOICES = []
for r in range(YEAR_START, (datetime.datetime.now().year + 1)):
    YEAR_CHOICES.append((r, r))

year = models.IntegerField(_('year'), choices=YEAR_CHOICES, default=datetime.datetime.now().year)


class Role(models.Model):
    """动态角色模型，支持通过数据库配置角色"""
    name = models.CharField(_('role name'), max_length=50, unique=True)
    display_name = models.CharField(_('display name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'htx_role'
        verbose_name = _('role')
        verbose_name_plural = _('roles')

    def __str__(self):
        return self.display_name


class Permission(models.Model):
    """权限模型，定义系统中的各种权限"""
    name = models.CharField(_('permission name'), max_length=100, unique=True)
    display_name = models.CharField(_('display name'), max_length=150)
    description = models.TextField(_('description'), blank=True)
    category = models.CharField(_('category'), max_length=50, default='general')
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'htx_permission'
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.display_name})"


class RolePermission(models.Model):
    """角色权限关联模型"""
    role = models.ForeignKey(
        Role, 
        on_delete=models.CASCADE, 
        related_name='permissions'
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.CASCADE, 
        related_name='roles'
    )
    granted = models.BooleanField(_('granted'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions'
    )

    class Meta:
        db_table = 'htx_role_permission'
        unique_together = ['role', 'permission']
        verbose_name = _('role permission')
        verbose_name_plural = _('role permissions')


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError('Must specify an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class UserLastActivityMixin(models.Model):
    last_activity = models.DateTimeField(_('last activity'), default=timezone.now, editable=False)

    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    class Meta:
        abstract = True


UserMixin = load_func(settings.USER_MIXIN)


class User(UserMixin, AbstractBaseUser, PermissionsMixin, UserLastActivityMixin):
    """
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Username and password are required. Other fields are optional.
    """

    username = models.CharField(_('username'), max_length=256)
    email = models.EmailField(_('email address'), unique=True, blank=True)

    first_name = models.CharField(_('first name'), max_length=256, blank=True)
    last_name = models.CharField(_('last name'), max_length=256, blank=True)
    phone = models.CharField(_('phone'), max_length=256, blank=True)
    avatar = models.ImageField(upload_to=hash_upload, blank=True)

    is_staff = models.BooleanField(
        _('staff status'), default=False, help_text=_('Designates whether the user can log into this admin site.')
    )

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether to treat this user as active. Unselect this instead of deleting accounts.'),
    )

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    activity_at = models.DateTimeField(_('last annotation activity'), auto_now=True)

    active_organization = models.ForeignKey(
        'organizations.Organization', null=True, on_delete=models.SET_NULL, related_name='active_users'
    )

    allow_newsletters = models.BooleanField(
        _('allow newsletters'), null=True, default=None, help_text=_('Allow sending newsletters to user')
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('role'),
        help_text=_('User role that determines permissions')
    )

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ()

    class Meta:
        db_table = 'htx_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['first_name']),
            models.Index(fields=['last_name']),
            models.Index(fields=['date_joined']),
        ]

    @cached_property
    def avatar_url(self):
        if self.avatar:
            if settings.CLOUD_FILE_STORAGE_ENABLED:
                return self.avatar.url
            else:
                return settings.HOSTNAME + self.avatar.url

    def is_organization_admin(self, org_pk):
        return True

    def active_organization_annotations(self):
        return self.annotations.filter(project__organization=self.active_organization)

    def active_organization_contributed_project_number(self):
        annotations = self.active_organization_annotations()
        return annotations.values_list('project').distinct().count()

    @cached_property
    def own_organization(self) -> Optional[Organization]:
        return fast_first(Organization.objects.filter(created_by=self))

    @cached_property
    def has_organization(self):
        return Organization.objects.filter(created_by=self).exists()

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def name_or_email(self):
        name = self.get_full_name()
        if len(name) == 0:
            name = self.email

        return name

    def get_full_name(self):
        """
        Return the first_name and the last_name for a given user with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def get_token(self) -> Token:
        return Token.objects.filter(user=self).first()

    def reset_token(self) -> Token:
        Token.objects.filter(user=self).delete()
        return Token.objects.create(user=self)

    def get_initials(self, is_deleted=False):
        initials = '?'

        if is_deleted:
            return 'DU'

        if not self.first_name and not self.last_name:
            initials = self.email[0:2]
        elif self.first_name and not self.last_name:
            initials = self.first_name[0:1]
        elif self.last_name and not self.first_name:
            initials = self.last_name[0:1]
        elif self.first_name and self.last_name:
            initials = self.first_name[0:1] + self.last_name[0:1]
        return initials

    def get_role_name(self):
        """获取用户角色名称"""
        if self.is_superuser:
            return 'superuser'
        return self.role.name if self.role else 'annotator'
    
    def has_role(self, role_name):
        """检查用户是否具有指定角色"""
        if self.is_superuser and role_name == 'superuser':
            return True
        return self.role and self.role.name == role_name
    
    def is_role_annotator(self):
        """检查是否为标注员角色"""
        return self.has_role('annotator')
    
    @property
    def effective_role(self):
        """获取用户的有效角色（考虑is_superuser字段的兼容性）"""
        if self.is_superuser:
            return 'superuser'
        return self.role.name if self.role else 'annotator'
    
    def has_permission(self, permission_name):
        """检查用户是否具有指定权限"""
        # 超级管理员拥有所有权限
        if self.is_superuser:
            return True
        
        # 如果没有角色，使用默认的annotator角色权限
        if not self.role:
            try:
                default_role = Role.objects.get(name='annotator')
                return RolePermission.objects.filter(
                    role=default_role,
                    permission__name=permission_name,
                    permission__is_active=True,
                    granted=True
                ).exists()
            except Role.DoesNotExist:
                return False
        
        # 检查角色是否具有该权限
        return RolePermission.objects.filter(
            role=self.role,
            permission__name=permission_name,
            permission__is_active=True,
            granted=True
        ).exists()
    
    def get_permissions(self):
        """获取用户的所有权限列表"""
        if self.is_superuser:
            # 超级管理员拥有所有权限
            return Permission.objects.filter(is_active=True).values_list('name', flat=True)
        
        if not self.role:
            # 如果用户没有明确的角色，为其提供默认的annotator权限
            try:
                default_role = Role.objects.get(name='annotator')
                return Permission.objects.filter(
                    roles__role=default_role,
                    roles__granted=True,
                    is_active=True
                ).values_list('name', flat=True)
            except Role.DoesNotExist:
                return []
        
        return Permission.objects.filter(
            roles__role=self.role,
            roles__granted=True,
            is_active=True
        ).values_list('name', flat=True)


@receiver(post_save, sender=User)
def init_user(sender, instance=None, created=False, **kwargs):
    if created:
        # create token for user
        Token.objects.create(user=instance)


class UserPreference(models.Model):
    """Model for storing user preferences"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='user_preferences'
    )
    preference_key = models.CharField(max_length=255, help_text="Preference key")
    preference_value = models.TextField(help_text="Preference value")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'project', 'preference_key']
        
    def __str__(self):
        return f"{self.user.username} - {self.project.title} - {self.preference_key}"

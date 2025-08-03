"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import logging

import drf_yasg.openapi as openapi
from django.utils import timezone
from core.permissions import ViewClassPermission, all_permissions
from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework import generics, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.functions import check_avatar
from users.models import User, Role, Permission, RolePermission
from users.serializers import UserSerializer, UserSerializerUpdate

logger = logging.getLogger(__name__)

_user_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
        'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name of the user'),
        'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name of the user'),
        'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username of the user'),
        'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email of the user'),
        'avatar': openapi.Schema(type=openapi.TYPE_STRING, description='Avatar URL of the user'),
        'initials': openapi.Schema(type=openapi.TYPE_STRING, description='Initials of the user'),
        'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number of the user'),
        'allow_newsletters': openapi.Schema(
            type=openapi.TYPE_BOOLEAN, description='Whether the user allows newsletters'
        ),
    },
)


@method_decorator(
    name='update',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_audiences=['internal'],
        operation_summary='Save user details',
        operation_description="""
    Save details for a specific user, such as their name or contact information, in Label Studio.
    """,
        manual_parameters=[
            openapi.Parameter(name='id', type=openapi.TYPE_INTEGER, in_=openapi.IN_PATH, description='User ID'),
        ],
        request_body=UserSerializer,
    ),
)
@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='list',
        x_fern_audiences=['public'],
        operation_summary='List users',
        operation_description='List the users that exist on the Label Studio server.',
    ),
)
@method_decorator(
    name='create',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='create',
        x_fern_audiences=['public'],
        operation_summary='Create new user',
        operation_description='Create a user in Label Studio.',
        request_body=_user_schema,
        responses={201: UserSerializer},
    ),
)
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='get',
        x_fern_audiences=['public'],
        operation_summary='Get user info',
        operation_description='Get info about a specific Label Studio user, based on the user ID.',
        manual_parameters=[
            openapi.Parameter(name='id', type=openapi.TYPE_INTEGER, in_=openapi.IN_PATH, description='User ID'),
        ],
        request_body=no_body,
        responses={200: UserSerializer},
    ),
)
@method_decorator(
    name='partial_update',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='update',
        x_fern_audiences=['public'],
        operation_summary='Update user details',
        operation_description="""
        Update details for a specific user, such as their name or contact information, in Label Studio.
        """,
        manual_parameters=[
            openapi.Parameter(name='id', type=openapi.TYPE_INTEGER, in_=openapi.IN_PATH, description='User ID'),
        ],
        request_body=_user_schema,
        responses={200: UserSerializer},
    ),
)
@method_decorator(
    name='destroy',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='delete',
        x_fern_audiences=['public'],
        operation_summary='Delete user',
        operation_description='Delete a specific Label Studio user.',
        manual_parameters=[
            openapi.Parameter(name='id', type=openapi.TYPE_INTEGER, in_=openapi.IN_PATH, description='User ID'),
        ],
        request_body=no_body,
    ),
)
class UserAPI(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_required = ViewClassPermission(
        GET=all_permissions.organizations_change,
        PUT=all_permissions.organizations_change,
        POST=all_permissions.organizations_change,
        PATCH=all_permissions.organizations_view,
        DELETE=all_permissions.organizations_change,
    )
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']

    def get_queryset(self):
        return User.objects.filter(organizations=self.request.user.active_organization)

    @swagger_auto_schema(auto_schema=None, methods=['delete', 'post'])
    @action(detail=True, methods=['delete', 'post'], permission_required=all_permissions.avatar_any)
    def avatar(self, request, pk):
        if request.method == 'POST':
            avatar = check_avatar(request.FILES)
            request.user.avatar = avatar
            request.user.save()
            return Response({'detail': 'avatar saved'}, status=200)

        elif request.method == 'DELETE':
            request.user.avatar = None
            request.user.save()
            return Response(status=204)

    def get_serializer_class(self):
        if self.request.method in {'PUT', 'PATCH'}:
            return UserSerializerUpdate
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super(UserAPI, self).get_serializer_context()
        context['user'] = self.request.user
        return context

    def update(self, request, *args, **kwargs):
        return super(UserAPI, self).update(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        return super(UserAPI, self).list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super(UserAPI, self).create(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        self.request.user.active_organization.add_user(instance)

    def retrieve(self, request, *args, **kwargs):
        return super(UserAPI, self).retrieve(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        result = super(UserAPI, self).partial_update(request, *args, **kwargs)

        # throw MethodNotAllowed if read-only fields are attempted to be updated
        read_only_fields = self.get_serializer_class().Meta.read_only_fields
        for field in read_only_fields:
            if field in request.data:
                raise MethodNotAllowed('PATCH', detail=f'Cannot update read-only field: {field}')

        # newsletters
        if 'allow_newsletters' in request.data:
            user = User.objects.get(id=request.user.id)  # we need an updated user
            request.user.advanced_json = {  # request.user instance will be unchanged in request all the time
                'email': user.email,
                'allow_newsletters': user.allow_newsletters,
                'update-notifications': 1,
                'new-user': 0,
            }
        return result

    def destroy(self, request, *args, **kwargs):
        return super(UserAPI, self).destroy(request, *args, **kwargs)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='reset_token',
        x_fern_audiences=['public'],
        operation_summary='Reset user token',
        operation_description='Reset the user token for the current user.',
        request_body=no_body,
        responses={
            201: openapi.Response(
                description='User token response',
                schema=openapi.Schema(
                    description='User token',
                    type=openapi.TYPE_OBJECT,
                    properties={'token': openapi.Schema(description='Token', type=openapi.TYPE_STRING)},
                ),
            )
        },
    ),
)
class UserResetTokenAPI(APIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        token = user.reset_token()
        logger.debug(f'New token for user {user.pk} is {token.key}')
        return Response({'token': token.key}, status=201)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='get_token',
        x_fern_audiences=['public'],
        operation_summary='Get user token',
        operation_description='Get a user token to authenticate to the API as the current user.',
        request_body=no_body,
        responses={
            200: openapi.Response(
                description='User token response',
                schema=openapi.Schema(
                    description='User token',
                    type=openapi.TYPE_OBJECT,
                    properties={'detail': openapi.Schema(description='Token', type=openapi.TYPE_STRING)},
                ),
            )
        },
    ),
)
class UserGetTokenAPI(APIView):
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        token = Token.objects.get(user=user)
        return Response({'token': str(token)}, status=200)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Users'],
        x_fern_sdk_group_name='users',
        x_fern_sdk_method_name='whoami',
        x_fern_audiences=['public'],
        operation_summary='Retrieve my user',
        operation_description='Retrieve details of the account that you are using to access the API.',
        request_body=no_body,
        responses={200: UserSerializer},
    ),
)
class UserWhoAmIAPI(generics.RetrieveAPIView):
    parser_classes = (JSONParser, FormParser, MultiPartParser)
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        return super(UserWhoAmIAPI, self).get(request, *args, **kwargs)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Users'],
        operation_summary='Get current user permissions',
        operation_description='Get real-time permissions for the current user.',
        request_body=no_body,
        responses={
            200: openapi.Response(
                description='User permissions response',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'permissions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='List of permission names'
                        ),
                        'role_info': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Role information'
                        )
                    }
                ),
            )
        },
    ),
)
class UserPermissionsAPI(APIView):
    """实时获取用户权限的API"""
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = request.user
        
        # 获取用户权限
        permissions = list(user.get_permissions())
        
        # 获取角色信息
        role_info = {
            'name': user.effective_role,
            'display_name': user.role.display_name if user.role else 'Superuser' if user.is_superuser else 'Annotator',
            'description': user.role.description if user.role else ''
        }
        
        return Response({
            'permissions': permissions,
            'role_info': role_info,
            'timestamp': timezone.now().isoformat()
        }, status=200)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Admin'],
        operation_summary='Toggle role permission',
        operation_description='Toggle a specific permission for a role.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'role_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Role ID'),
                'permission_name': openapi.Schema(type=openapi.TYPE_STRING, description='Permission name'),
                'granted': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Grant or revoke permission')
            },
            required=['role_id', 'permission_name', 'granted']
        ),
    ),
)
class ToggleRolePermissionAPI(APIView):
    """切换角色权限的API"""
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'error': '需要管理员权限'}, status=403)
        
        role_id = request.data.get('role_id')
        permission_name = request.data.get('permission_name')
        granted = request.data.get('granted')
        
        try:
            role = Role.objects.get(id=role_id)
            permission = Permission.objects.get(name=permission_name)
            
            role_perm, created = RolePermission.objects.get_or_create(
                role=role,
                permission=permission,
                defaults={'granted': granted, 'created_by': request.user}
            )
            
            if not created:
                role_perm.granted = granted
                role_perm.save()
            
            return Response({
                'success': True,
                'message': f'权限 {permission.display_name} {"授予" if granted else "撤销"}成功',
                'role': role.display_name,
                'permission': permission.display_name,
                'granted': granted
            }, status=200)
            
        except Role.DoesNotExist:
            return Response({'error': '角色不存在'}, status=404)
        except Permission.DoesNotExist:
            return Response({'error': '权限不存在'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Admin'],
        operation_summary='Bulk add permissions to role',
        operation_description='Add multiple permissions to a role at once.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'role_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Role ID'),
                'permission_package': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    enum=['project_creation', 'workspace_management', 'annotation', 'admin_full'],
                    description='Permission package to add'
                )
            },
            required=['role_id', 'permission_package']
        ),
    ),
)
class BulkAddPermissionsAPI(APIView):
    """批量添加权限包的API"""
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)
    
    # 简化权限包 - 对应前端的SIMPLIFIED_PERMISSIONS
    SIMPLIFIED_PERMISSION_PACKAGES = {
        'project_create_full': [
            'view_projects',
            'create_project', 
            'show_create_project_button'
        ],
        'project_delete_full': [
            'view_project_danger_zone',
            'edit_project_danger_zone_fields', 
            'delete_project'
        ],
        'project_export_full': [
            'export_project_data',
            'show_export_project_button'
        ],
        'project_import_full': [
            'import_project_data',
            'show_import_project_button'
        ],
        'workspace_create_full': [
            'view_workspaces',
            'create_workspace',
            'show_create_workspace_button'
        ],
        'workspace_manage_full': [
            'manage_workspaces',
            'edit_workspace',
            'delete_workspace',
            'manage_workspace_members',
            'show_edit_workspace_button',
            'show_delete_workspace_button'
        ],
        'annotation_full': [
            'create_annotation',
            'edit_annotation',
            'delete_annotation',
            'review_annotation'
        ],
        'user_manage_full': [
            'manage_users',
            'manage_roles',
            'edit_user_role_assignment',
            'show_invite_users_button',
            'show_manage_user_roles'
        ],
        'organization_manage_full': [
            'view_organization',
            'manage_organization',
            'manage_permissions',
            'edit_organization_settings'
        ],
        'project_settings_basic': [
            'view_project_general_settings',
            'view_project_labeling_settings',
            'view_project_annotation_settings'
        ],
        'project_settings_advanced': [
            'view_project_machine_learning',
            'view_project_predictions',
            'view_project_cloud_storage',
            'view_project_webhooks',
            'edit_project_ml_settings',
            'edit_project_webhook_settings'
        ]
    }
    
    # 保留原有权限包用于向后兼容（标记为传统模式）
    LEGACY_PERMISSION_PACKAGES = {
        'project_creation': [
            'create_project',
            'show_create_project_button'
        ],
        'project_deletion': [
            'view_project_danger_zone',
            'edit_project_danger_zone_fields',
            'delete_project'
        ],
        'workspace_management': [
            'create_workspace',
            'edit_workspace',
            'delete_workspace',
            'show_create_workspace_button',
            'show_edit_workspace_button',
            'show_delete_workspace_button'
        ],
        'annotation': [
            'view_annotations',
            'create_annotation',
            'edit_annotation',
            'delete_annotation',
            'submit_annotation',
            'skip_annotation'
        ]
    }

    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'error': '需要管理员权限'}, status=403)
        
        role_id = request.data.get('role_id')
        permission_package = request.data.get('permission_package')
        
        try:
            role = Role.objects.get(id=role_id)
            
            if permission_package == 'admin_full':
                # 获取所有活跃权限
                permissions = Permission.objects.filter(is_active=True).values_list('name', flat=True)
            else:
                # 优先查找简化权限包，然后查找传统权限包
                permissions = (
                    self.SIMPLIFIED_PERMISSION_PACKAGES.get(permission_package) or 
                    self.LEGACY_PERMISSION_PACKAGES.get(permission_package, [])
                )
            
            if not permissions:
                return Response({'error': '无效的权限包'}, status=400)
            
            added_count = 0
            for perm_name in permissions:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                        defaults={'granted': True, 'created_by': request.user}
                    )
                    if created or not role_perm.granted:
                        role_perm.granted = True
                        role_perm.save()
                        added_count += 1
                except Permission.DoesNotExist:
                    continue
            
            return Response({
                'success': True,
                'message': f'成功为角色 {role.display_name} 添加 {added_count} 个权限',
                'role': role.display_name,
                'package': permission_package,
                'added_count': added_count
            }, status=200)
            
        except Role.DoesNotExist:
            return Response({'error': '角色不存在'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        tags=['Admin'],
        operation_summary='Get role permissions',
        operation_description='Get all permissions for a specific role.',
        manual_parameters=[
            openapi.Parameter('role_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Role ID'),
        ],
    ),
)
class RolePermissionsAPI(APIView):
    """获取角色权限的API"""
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'error': '需要管理员权限'}, status=403)
        
        role_id = request.query_params.get('role_id')
        
        try:
            role = Role.objects.get(id=role_id)
            
            # 获取所有活跃权限
            all_permissions = Permission.objects.filter(is_active=True).order_by('category', 'name')
            
            # 获取角色已授予的权限
            granted_permissions = set(
                RolePermission.objects.filter(
                    role=role, granted=True
                ).values_list('permission__name', flat=True)
            )
            
            permissions_by_category = {}
            for permission in all_permissions:
                category = permission.category or '未分类'
                if category not in permissions_by_category:
                    permissions_by_category[category] = []
                
                permissions_by_category[category].append({
                    'name': permission.name,
                    'display_name': permission.display_name,
                    'granted': permission.name in granted_permissions,
                    'category': permission.category
                })
            
            return Response({
                'role': {
                    'id': role.id,
                    'name': role.name,
                    'display_name': role.display_name
                },
                'permissions_by_category': permissions_by_category,
                'total_granted': len(granted_permissions),
                'total_permissions': all_permissions.count(),
                'permission_package_status': self._calculate_permission_package_status(granted_permissions),
            }, status=200)
        except Role.DoesNotExist:
            return Response({'error': '角色不存在'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    def _calculate_permission_package_status(self, granted_permissions):
        """计算权限包的状态"""
        package_status = {}
        
        # 检查简化权限包状态
        for package_name, required_permissions in BulkAddPermissionsAPI.SIMPLIFIED_PERMISSION_PACKAGES.items():
            granted_count = sum(1 for perm in required_permissions if perm in granted_permissions)
            total_count = len(required_permissions)
            
            package_status[package_name] = {
                'granted_count': granted_count,
                'total_count': total_count,
                'is_complete': granted_count == total_count,
                'is_partial': 0 < granted_count < total_count,
                'is_empty': granted_count == 0,
                'missing_permissions': [perm for perm in required_permissions if perm not in granted_permissions],
                'type': 'simplified'
            }
        
        # 检查传统权限包状态  
        for package_name, required_permissions in BulkAddPermissionsAPI.LEGACY_PERMISSION_PACKAGES.items():
            granted_count = sum(1 for perm in required_permissions if perm in granted_permissions)
            total_count = len(required_permissions)
            
            package_status[package_name] = {
                'granted_count': granted_count,
                'total_count': total_count,
                'is_complete': granted_count == total_count,
                'is_partial': 0 < granted_count < total_count,
                'is_empty': granted_count == 0,
                'missing_permissions': [perm for perm in required_permissions if perm not in granted_permissions],
                'type': 'legacy'
            }
            
        return package_status


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        tags=['Admin'],
        operation_summary='Bulk remove permissions from role',
        operation_description='Remove multiple permissions from a role at once.',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'role_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Role ID'),
                'permission_package': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Permission package to remove'
                )
            },
            required=['role_id', 'permission_package']
        ),
        responses={200: 'Success', 400: 'Bad Request', 403: 'Forbidden'}
    )
)
class BulkRemovePermissionsAPI(APIView):
    """批量移除权限包的API"""
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'error': '需要管理员权限'}, status=403)
        
        role_id = request.data.get('role_id')
        permission_package = request.data.get('permission_package')
        
        try:
            role = Role.objects.get(id=role_id)
            
            # 优先查找简化权限包，然后查找传统权限包
            permissions = (
                BulkAddPermissionsAPI.SIMPLIFIED_PERMISSION_PACKAGES.get(permission_package) or 
                BulkAddPermissionsAPI.LEGACY_PERMISSION_PACKAGES.get(permission_package, [])
            )
            
            if not permissions:
                return Response({'error': '无效的权限包'}, status=400)
            
            removed_count = 0
            for perm_name in permissions:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role_perm = RolePermission.objects.filter(
                        role=role,
                        permission=permission
                    ).first()
                    
                    if role_perm:
                        role_perm.granted = False
                        role_perm.save()
                        removed_count += 1
                    
                except Permission.DoesNotExist:
                    continue
            
            return Response({
                'success': True,
                'message': f'成功移除权限包 {permission_package}，共移除 {removed_count} 个权限',
                'role': role.display_name,
                'package': permission_package,
                'removed_count': removed_count
            }, status=200)
            
        except Role.DoesNotExist:
            return Response({'error': '角色不存在'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

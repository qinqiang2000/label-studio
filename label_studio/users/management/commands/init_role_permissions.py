"""
管理命令：初始化角色和权限数据
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import Role, Permission, RolePermission
from users.utils.permissions import (
    DEFAULT_ROLE_PERMISSIONS, 
    PERMISSION_CATEGORIES,
    PERMISSION_GROUPS,
    ROLE_PERMISSION_CONFIG,
    get_role_permissions_by_config
)


class Command(BaseCommand):
    help = '初始化系统角色和权限数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='重置现有的角色和权限数据'
        )

    def handle(self, *args, **options):
        reset = options['reset']
        
        if reset:
            self.stdout.write('正在重置角色和权限数据...')
            with transaction.atomic():
                RolePermission.objects.all().delete()
                Role.objects.all().delete()
                Permission.objects.all().delete()

        self.stdout.write('开始初始化权限数据...')
        self.create_permissions()
        
        self.stdout.write('开始初始化角色数据...')
        self.create_roles()
        
        self.stdout.write('开始配置角色权限关联...')
        self.assign_role_permissions()
        
        self.stdout.write(
            self.style.SUCCESS('✅ 角色权限系统初始化完成！')
        )

    def create_permissions(self):
        """基于权限组自动创建权限数据"""
        # 扩展的权限定义，包含更多新权限
        permissions_data = [
            # 基础菜单权限
            ('view_home', 'Home菜单查看', '查看首页菜单', 'menu'),
            ('view_projects', 'Projects菜单查看', '查看项目列表菜单', 'menu'),
            ('view_workspaces', 'Workspaces菜单查看', '查看工作空间菜单', 'menu'),
            ('view_prompts', 'Prompts菜单查看', '查看提示词菜单', 'menu'),
            ('view_organization', 'Organization菜单查看', '查看组织管理菜单', 'menu'),
            ('view_account_settings', '账户设置', '查看个人账户设置', 'menu'),
            ('view_permission_management', '权限管理中心', '查看权限管理中心页面', 'menu'),
            
            # 项目设置菜单权限
            ('view_project_general_settings', '项目基本设置', '查看项目基本设置页面', 'menu'),
            ('view_project_labeling_settings', '项目标注设置', '查看项目标注设置页面', 'menu'),
            ('view_project_annotation_settings', '项目注释设置', '查看项目注释设置页面', 'menu'),
            ('view_project_machine_learning', '项目机器学习设置', '查看项目机器学习设置页面', 'menu'),
            ('view_project_predictions', '项目预测设置', '查看项目预测设置页面', 'menu'),
            ('view_project_cloud_storage', '项目云存储设置', '查看项目云存储设置页面', 'menu'),
            ('view_project_webhooks', '项目Webhooks设置', '查看项目Webhooks设置页面', 'menu'),
            ('view_project_danger_zone', '项目危险操作区', '查看项目危险操作设置页面', 'menu'),
            
            # 标注操作权限
            ('create_annotation', '创建标注', '创建新标注的权限', 'action'),
            ('edit_annotation', '编辑标注', '编辑标注的权限', 'action'),
            ('delete_annotation', '删除标注', '删除标注的权限', 'action'),
            ('review_annotation', '审核标注', '审核标注的权限', 'action'),
            
            # 项目管理权限
            ('create_project', '创建项目', '创建新项目的权限', 'action'),
            ('edit_project', '编辑项目', '编辑项目信息的权限', 'action'),
            ('delete_project', '删除项目', '删除项目的权限', 'action'),
            ('export_project_data', '导出项目数据', '导出项目数据的权限', 'action'),
            ('import_project_data', '导入项目数据', '导入项目数据的权限', 'action'),
            
            # 工作空间管理权限
            ('manage_workspaces', '管理工作空间', '管理工作空间的权限', 'action'),
            ('create_workspace', '创建工作空间', '创建新工作空间的权限', 'action'),
            ('edit_workspace', '编辑工作空间', '编辑工作空间信息的权限', 'action'),
            ('delete_workspace', '删除工作空间', '删除工作空间的权限', 'action'),
            ('manage_workspace_members', '管理工作空间成员', '管理工作空间成员的权限', 'action'),
            
            # 管理权限
            ('manage_users', '用户管理', '管理系统用户的权限', 'admin'),
            ('manage_roles', '角色管理', '管理系统角色的权限', 'admin'),
            ('manage_permissions', '权限管理', '管理系统权限的权限', 'admin'),
            ('manage_organization', '组织管理', '管理组织的权限', 'admin'),
            
            # 页面操作权限
            ('show_create_project_button', '显示创建项目按钮', '控制创建项目按钮的显示', 'page_operation'),
            ('show_import_project_button', '显示导入项目按钮', '控制导入项目按钮的显示', 'page_operation'),
            ('show_export_project_button', '显示导出项目按钮', '控制导出项目按钮的显示', 'page_operation'),
            ('show_delete_project_button', '显示删除项目按钮', '控制删除项目按钮的显示', 'page_operation'),
            ('show_create_workspace_button', '显示创建工作空间按钮', '控制创建工作空间按钮的显示', 'page_operation'),
            ('show_edit_workspace_button', '显示编辑工作空间按钮', '控制编辑工作空间按钮的显示', 'page_operation'),
            ('show_delete_workspace_button', '显示删除工作空间按钮', '控制删除工作空间按钮的显示', 'page_operation'),
            ('show_invite_users_button', '显示邀请用户按钮', '控制邀请用户按钮的显示', 'page_operation'),
            ('show_manage_user_roles', '显示管理用户角色', '控制用户角色管理功能的显示', 'page_operation'),
            ('show_permission_management_button', '显示权限管理按钮', '控制权限管理按钮的显示', 'page_operation'),
            
            # 表单字段权限
            ('edit_project_danger_zone_fields', '编辑项目危险区域字段', '控制项目危险区域字段的编辑权限', 'field_permission'),
            ('edit_project_ml_settings', '编辑项目机器学习设置', '控制项目机器学习设置字段的编辑权限', 'field_permission'),
            ('edit_project_webhook_settings', '编辑项目Webhook设置', '控制项目Webhook设置字段的编辑权限', 'field_permission'),
            ('edit_user_role_assignment', '编辑用户角色分配', '控制用户角色分配字段的编辑权限', 'field_permission'),
            ('edit_organization_settings', '编辑组织设置', '控制组织设置字段的编辑权限', 'field_permission'),
        ]
        
        created_count = 0
        updated_count = 0
        
        for name, display_name, description, category in permissions_data:
            permission, created = Permission.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'category': category,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ 创建权限: {display_name}')
            else:
                # 更新现有权限的信息
                if (permission.display_name != display_name or 
                    permission.description != description or 
                    permission.category != category):
                    permission.display_name = display_name
                    permission.description = description
                    permission.category = category
                    permission.save()
                    updated_count += 1
                    self.stdout.write(f'  ↻ 更新权限: {display_name}')
                else:
                    self.stdout.write(f'  - 权限已存在: {display_name}')
        
        self.stdout.write(f'权限处理完成，共创建 {created_count} 个新权限，更新 {updated_count} 个权限')
        
        # 显示权限组统计
        self.stdout.write('\n=== 权限组统计 ===')
        for group_name, permissions in PERMISSION_GROUPS.items():
            self.stdout.write(f'{group_name}: {len(permissions)} 个权限')

    def create_roles(self):
        """创建角色数据"""
        roles_data = [
            ('superuser', '超级管理员', '系统超级管理员，拥有所有权限'),
            ('annotator', '标注员', '标注员，拥有基础的标注和项目访问权限'),
            ('workspace_admin', '工作空间管理员', '工作空间管理员，可以管理所属工作空间的项目和成员'),
        ]
        
        created_count = 0
        for name, display_name, description in roles_data:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={
                    'display_name': display_name,
                    'description': description,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ 创建角色: {display_name}')
            else:
                self.stdout.write(f'  - 角色已存在: {display_name}')
        
        self.stdout.write(f'角色创建完成，共创建 {created_count} 个新角色')

    def assign_role_permissions(self, reset=False):
        """分配角色权限"""
        for role_name, role_config in ROLE_PERMISSION_CONFIG.items():
            try:
                role = Role.objects.get(name=role_name)
                permissions = get_role_permissions_by_config(role_name)
                
                self.stdout.write(f'  分配 {role.display_name} 的权限...')
                self.stdout.write(f'    权限来源: {self._get_permission_source_info(role_name)}')
                
                # 清除现有权限分配（如果是重置模式）
                if reset:
                    old_count = RolePermission.objects.filter(role=role).count()
                    RolePermission.objects.filter(role=role).delete()
                    self.stdout.write(f'    - 清除了 {old_count} 个现有权限分配')
                
                # 分配权限
                assigned_count = 0
                skipped_count = 0
                for permission_name in permissions:
                    try:
                        permission = Permission.objects.get(name=permission_name)
                        role_permission, created = RolePermission.objects.get_or_create(
                            role=role,
                            permission=permission,
                            defaults={'granted': True}
                        )
                        if created:
                            assigned_count += 1
                    except Permission.DoesNotExist:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'    ⚠️  权限不存在: {permission_name}')
                        )
                
                self.stdout.write(f'    ✅ 分配了 {assigned_count} 个权限（总共 {len(permissions)} 个，跳过 {skipped_count} 个）')
                
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ 角色不存在: {role_name}')
                )
        
        self.stdout.write('角色权限分配完成')
    
    def _get_permission_source_info(self, role_name):
        """获取角色权限来源信息"""
        role_config = ROLE_PERMISSION_CONFIG.get(role_name, {})
        
        sources = []
        if role_config.get('inherit_from'):
            sources.append(f"继承自 {role_config['inherit_from']}")
        
        if role_config.get('groups') == 'all':
            sources.append("所有权限组")
        elif isinstance(role_config.get('groups'), list):
            sources.append(f"权限组: {', '.join(role_config['groups'])}")
        
        if role_config.get('additional_permissions'):
            sources.append(f"额外权限: {len(role_config['additional_permissions'])} 个")
        
        return ' + '.join(sources) if sources else '无特殊配置'

    def print_summary(self):
        """打印统计信息"""
        self.stdout.write('\n=== 系统权限统计 ===')
        
        total_permissions = Permission.objects.count()
        total_roles = Role.objects.count()
        total_assignments = RolePermission.objects.count()
        
        self.stdout.write(f'总权限数: {total_permissions}')
        self.stdout.write(f'总角色数: {total_roles}')
        self.stdout.write(f'总权限分配数: {total_assignments}')
        
        self.stdout.write('\n=== 各角色权限数量 ===')
        for role in Role.objects.all():
            permission_count = RolePermission.objects.filter(
                role=role, granted=True
            ).count()
            self.stdout.write(f'{role.display_name}: {permission_count} 个权限')
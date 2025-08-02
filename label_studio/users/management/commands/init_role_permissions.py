"""
管理命令：初始化角色和权限数据
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import Role, Permission, RolePermission
from users.utils.permissions import DEFAULT_ROLE_PERMISSIONS, PERMISSION_CATEGORIES


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
        """创建权限数据"""
        permissions_data = [
            # 菜单权限
            ('view_home', 'Home菜单查看', '查看首页菜单', 'menu'),
            ('view_projects', 'Projects菜单查看', '查看项目列表菜单', 'menu'),
            ('view_workspaces', 'Workspaces菜单查看', '查看工作空间菜单', 'menu'),
            ('view_prompts', 'Prompts菜单查看', '查看提示词菜单', 'menu'),
            ('view_organization', 'Organization菜单查看', '查看组织管理菜单', 'menu'),
            
            # 项目设置菜单权限
            ('view_project_general_settings', '项目基本设置', '查看项目基本设置页面', 'menu'),
            ('view_project_labeling_settings', '项目标注设置', '查看项目标注设置页面', 'menu'),
            ('view_project_annotation_settings', '项目注释设置', '查看项目注释设置页面', 'menu'),
            ('view_project_machine_learning', '项目机器学习设置', '查看项目机器学习设置页面', 'menu'),
            ('view_project_predictions', '项目预测设置', '查看项目预测设置页面', 'menu'),
            ('view_project_cloud_storage', '项目云存储设置', '查看项目云存储设置页面', 'menu'),
            ('view_project_webhooks', '项目Webhooks设置', '查看项目Webhooks设置页面', 'menu'),
            ('view_project_danger_zone', '项目危险操作区', '查看项目危险操作设置页面', 'menu'),
            
            # 账户设置权限
            ('view_account_settings', '账户设置', '查看个人账户设置', 'menu'),
            
            # 项目操作权限
            ('create_project', '创建项目', '创建新项目的权限', 'action'),
            ('edit_project', '编辑项目', '编辑项目信息的权限', 'action'),
            ('delete_project', '删除项目', '删除项目的权限', 'action'),
            ('export_project_data', '导出项目数据', '导出项目数据的权限', 'action'),
            
            # 标注操作权限
            ('create_annotation', '创建标注', '创建新标注的权限', 'action'),
            ('edit_annotation', '编辑标注', '编辑标注的权限', 'action'),
            ('delete_annotation', '删除标注', '删除标注的权限', 'action'),
            ('review_annotation', '审核标注', '审核标注的权限', 'action'),
            
            # 用户管理权限
            ('manage_users', '用户管理', '管理系统用户的权限', 'admin'),
            ('manage_roles', '角色管理', '管理系统角色的权限', 'admin'),
            ('manage_permissions', '权限管理', '管理系统权限的权限', 'admin'),
            
            # 组织管理权限
            ('manage_organization', '组织管理', '管理组织的权限', 'admin'),
            ('manage_workspaces', '工作空间管理', '管理工作空间的权限', 'admin'),
        ]
        
        created_count = 0
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
                self.stdout.write(f'  - 权限已存在: {display_name}')
        
        self.stdout.write(f'权限创建完成，共创建 {created_count} 个新权限')

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

    def assign_role_permissions(self):
        """分配角色权限"""
        from users.utils.permissions import DEFAULT_ROLE_PERMISSIONS
        
        for role_name, role_config in DEFAULT_ROLE_PERMISSIONS.items():
            try:
                role = Role.objects.get(name=role_name)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'角色 {role_name} 不存在，跳过权限分配')
                )
                continue
            
            assigned_count = 0
            for permission_name in role_config['permissions']:
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
                    self.stdout.write(
                        self.style.WARNING(f'权限 {permission_name} 不存在，跳过分配')
                    )
                    continue
            
            self.stdout.write(
                f'  ✓ 为角色 {role.display_name} 分配了 {assigned_count} 个新权限'
            )
        
        self.stdout.write('角色权限分配完成')

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
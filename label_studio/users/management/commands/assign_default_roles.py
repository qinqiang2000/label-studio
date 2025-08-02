"""
为现有用户分配默认角色的管理命令
"""
from django.core.management.base import BaseCommand
from users.models import User, Role


class Command(BaseCommand):
    help = '为现有用户分配默认角色'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只显示要修改的用户，不执行实际操作',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== 预览模式 - 不会执行实际修改 ==='))
        else:
            self.stdout.write(self.style.SUCCESS('=== 开始为用户分配默认角色 ==='))
        
        # 获取annotator角色
        try:
            annotator_role = Role.objects.get(name='annotator')
            self.stdout.write(f'✓ 找到annotator角色: {annotator_role.display_name}')
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ 未找到annotator角色，请先运行 init_role_permissions 命令'))
            return

        # 查找没有角色的用户（但不是超级管理员）
        users_without_roles = User.objects.filter(role__isnull=True, is_superuser=False)
        
        self.stdout.write(f'\n找到 {users_without_roles.count()} 个需要分配角色的用户:')
        
        updated_count = 0
        for user in users_without_roles:
            self.stdout.write(f'  - {user.email} ({user.username or "无用户名"})')
            
            if not dry_run:
                user.role = annotator_role
                user.save()
                updated_count += 1
        
        if dry_run:
            self.stdout.write(f'\n📊 预览完成: 将为 {users_without_roles.count()} 个用户分配annotator角色')
            self.stdout.write('使用 --no-dry-run 执行实际修改')
        else:
            self.stdout.write(f'\n✅ 成功为 {updated_count} 个用户分配了annotator角色')
            
            # 验证结果
            remaining_users = User.objects.filter(role__isnull=True, is_superuser=False)
            if remaining_users.count() == 0:
                self.stdout.write('🎉 所有普通用户都已分配角色')
            else:
                self.stdout.write(f'⚠️  仍有 {remaining_users.count()} 个用户未分配角色')
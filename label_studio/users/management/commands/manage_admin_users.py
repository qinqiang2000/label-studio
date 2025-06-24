from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction


User = get_user_model()


class Command(BaseCommand):
    help = '管理用户admin权限'
    
    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true', help='列出所有用户及其admin权限状态')
        parser.add_argument('--user', help='用户邮箱或用户名')
        parser.add_argument('--check', help='检查特定用户的admin权限')
        parser.add_argument('--grant-staff', action='store_true', help='授予用户员工权限(可登录admin)')
        parser.add_argument('--revoke-staff', action='store_true', help='撤销用户员工权限')
        parser.add_argument('--grant-superuser', action='store_true', help='授予用户超级用户权限')
        parser.add_argument('--revoke-superuser', action='store_true', help='撤销用户超级用户权限')
        parser.add_argument('--activate', action='store_true', help='激活用户账号')
        parser.add_argument('--deactivate', action='store_true', help='停用用户账号')
    
    def handle(self, *args, **options):
        if options['list']:
            self.list_users()
            return
            
        if options['check']:
            self.check_user(options['check'])
            return
            
        user_identifier = options.get('user')
        if not user_identifier:
            self.stdout.write(
                self.style.ERROR('请提供用户邮箱或用户名 (--user)')
            )
            return
            
        user = self.get_user(user_identifier)
        if not user:
            return
            
        changes_made = False
        
        with transaction.atomic():
            if options['grant_staff']:
                user.is_staff = True
                changes_made = True
                self.stdout.write(f'✓ 已授予 {user.email} 员工权限(可登录admin)')
                
            if options['revoke_staff']:
                user.is_staff = False
                changes_made = True
                self.stdout.write(f'✗ 已撤销 {user.email} 员工权限(无法登录admin)')
                
            if options['grant_superuser']:
                user.is_superuser = True
                user.is_staff = True  # 超级用户必须是员工
                changes_made = True
                self.stdout.write(f'✓ 已授予 {user.email} 超级用户权限')
                
            if options['revoke_superuser']:
                user.is_superuser = False
                changes_made = True
                self.stdout.write(f'✗ 已撤销 {user.email} 超级用户权限')
                
            if options['activate']:
                user.is_active = True
                changes_made = True
                self.stdout.write(f'✓ 已激活用户 {user.email}')
                
            if options['deactivate']:
                user.is_active = False
                changes_made = True
                self.stdout.write(f'✗ 已停用用户 {user.email}')
                
            if changes_made:
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'用户 {user.email} 权限已更新')
                )
                self.show_user_status(user)
            else:
                self.stdout.write(
                    self.style.WARNING('未指定任何操作')
                )
    
    def list_users(self):
        """列出所有用户及其权限状态"""
        users = User.objects.all().order_by('email')
        
        self.stdout.write('\n=== 用户admin权限状态 ===')
        self.stdout.write('-' * 80)
        self.stdout.write(f'{"邮箱":<30} {"用户名":<15} {"激活":<6} {"员工":<6} {"超级用户":<8} {"可登录admin":<12}')
        self.stdout.write('-' * 80)
        
        for user in users:
            can_login_admin = user.is_staff and user.is_active
            self.stdout.write(
                f'{user.email:<30} '
                f'{user.username or "无":<15} '
                f'{"是" if user.is_active else "否":<6} '
                f'{"是" if user.is_staff else "否":<6} '
                f'{"是" if user.is_superuser else "否":<8} '
                f'{"是" if can_login_admin else "否":<12}'
            )
    
    def check_user(self, user_identifier):
        """检查特定用户的admin权限"""
        user = self.get_user(user_identifier)
        if user:
            self.show_user_status(user)
    
    def get_user(self, user_identifier):
        """通过邮箱或用户名获取用户"""
        try:
            # 先尝试邮箱查找
            user = User.objects.get(email=user_identifier)
            return user
        except User.DoesNotExist:
            try:
                # 再尝试用户名查找
                user = User.objects.get(username=user_identifier)
                return user
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'用户不存在: {user_identifier}')
                )
                return None
    
    def show_user_status(self, user):
        """显示用户详细状态"""
        can_login_admin = user.is_staff and user.is_active
        
        self.stdout.write(f'\n用户详情: {user.email}')
        self.stdout.write('=' * 50)
        self.stdout.write(f'用户名: {user.username or "无"}')
        self.stdout.write(f'激活状态: {"是" if user.is_active else "否"}')
        self.stdout.write(f'员工权限: {"是" if user.is_staff else "否"}')
        self.stdout.write(f'超级用户: {"是" if user.is_superuser else "否"}')
        self.stdout.write(f'可登录admin: {"是" if can_login_admin else "否"}')
        
        if not can_login_admin:
            self.stdout.write(
                self.style.WARNING('\n⚠️  该用户无法登录admin界面')
            )
            if not user.is_active:
                self.stdout.write('   原因: 账号未激活')
            if not user.is_staff:
                self.stdout.write('   原因: 没有员工权限')
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✓ 该用户可以登录admin界面')
            ) 
"""初始化超级管理员账户。

用法：
  python manage.py init_admin [--username admin] [--password xxx] [--email a@b.com]

不指定参数时从环境变量读取：ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL
账户已存在时仅重置密码（除非指定 --no-reset）。
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = '初始化或重置超级管理员账户'

    def add_arguments(self, parser):
        parser.add_argument('--username', default=os.environ.get('ADMIN_USERNAME', 'admin'))
        parser.add_argument('--password', default=os.environ.get('ADMIN_PASSWORD', ''))
        parser.add_argument('--email', default=os.environ.get('ADMIN_EMAIL', 'admin@localhost'))
        parser.add_argument('--no-reset', action='store_true', help='账户已存在时不重置密码')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        password = options['password']
        email = options['email']

        if not password:
            self.stdout.write(self.style.ERROR('未提供密码，请通过 --password 或 ADMIN_PASSWORD 环境变量指定'))
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ 已创建超级管理员: {username}'))
        elif options['no_reset']:
            self.stdout.write(self.style.WARNING(f'⚠️  账户 {username} 已存在，未重置密码（--no-reset）'))
        else:
            user.set_password(password)
            user.email = email or user.email
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ 已重置超级管理员密码: {username}'))

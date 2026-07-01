"""命令行健康检查，用于 k8s sidecar 或脚本探针。

用法：
  python manage.py healthcheck

检查项：
  1. 数据库连通性
  2. Celery 连通性（若配置了 BROKER_URL）
  3. 待处理任务数

退出码：0 健康 / 1 不健康
"""
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = '命令行健康检查'

    def handle(self, *args, **options):
        errors = []

        # 1. 数据库连通性
        try:
            conn = connections['default']
            conn.ensure_connection()
            self.stdout.write('  ✅ 数据库连接正常')
        except Exception as e:
            errors.append(f'数据库连接失败: {e}')
            self.stdout.write(self.style.ERROR(f'  ❌ 数据库连接失败: {e}'))

        # 2. Celery 连通性（可选）
        import os
        broker_url = os.environ.get('CELERY_BROKER_URL', '')
        if broker_url:
            try:
                import redis
                r = redis.from_url(broker_url, socket_connect_timeout=3)
                r.ping()
                self.stdout.write('  ✅ Redis 连接正常')
            except ImportError:
                self.stdout.write(self.style.WARNING('  ⚠️  redis 库未安装，跳过 Redis 检查'))
            except Exception as e:
                errors.append(f'Redis 连接失败: {e}')
                self.stdout.write(self.style.ERROR(f'  ❌ Redis 连接失败: {e}'))
        else:
            self.stdout.write('  ℹ️  未配置 CELERY_BROKER_URL，跳过 Redis 检查')

        # 3. 待处理任务数
        try:
            from migration_app.models import MigrationTask
            pending = MigrationTask.objects.filter(status='pending').count()
            running = MigrationTask.objects.filter(status='running').count()
            self.stdout.write(f'  ℹ️  任务：{running} running / {pending} pending')
        except Exception:
            pass  # 表可能未创建

        if errors:
            self.stdout.write(self.style.ERROR('\n❌ 健康检查未通过'))
            exit(1)
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ 健康检查通过'))

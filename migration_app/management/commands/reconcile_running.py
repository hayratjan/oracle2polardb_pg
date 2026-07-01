"""重置孤儿 running 任务为 aborted。

服务异常退出后，状态为 running 的任务会遗留。本命令将它们标记为 aborted，
便于用户重新运行或继续迁移。

用法：
  python manage.py reconcile_running [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from migration_app.models import MigrationTask


class Command(BaseCommand):
    help = '重置孤儿 running 任务为 aborted'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='只统计不实际修改')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        qs = MigrationTask.objects.filter(status='running')

        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ 无孤儿 running 任务'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] 发现 {count} 个孤儿 running 任务：'
            ))
            for t in qs:
                self.stdout.write(f'  - #{t.id} {t.name} (started: {t.started_at})')
            return

        # 批量更新
        now = timezone.now()
        qs.update(status='aborted', completed_at=now)

        self.stdout.write(self.style.SUCCESS(
            f'✅ 已将 {count} 个孤儿 running 任务重置为 aborted'
        ))
        for t in qs:
            self.stdout.write(f'  - #{t.id} {t.name}')

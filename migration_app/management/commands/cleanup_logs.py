"""清理过期任务日志，释放存储空间。

用法：
  python manage.py cleanup_logs [--days 30] [--dry-run]

  --days N    清理 N 天前的日志（默认 30）
  --dry-run   只统计不实际删除
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from migration_app.models import MigrationTaskLog


class Command(BaseCommand):
    help = '清理过期任务日志'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='清理 N 天前的日志（默认 30）')
        parser.add_argument('--dry-run', action='store_true', help='只统计不实际删除')

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff = timezone.now() - timedelta(days=days)

        qs = MigrationTaskLog.objects.filter(created_at__lt=cutoff)
        count = qs.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] 将清理 {count} 条 {days} 天前的日志（{cutoff.strftime("%Y-%m-%d")} 之前）'
            ))
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'✅ 已清理 {deleted} 条 {days} 天前的日志（{cutoff.strftime("%Y-%m-%d")} 之前）'
        ))

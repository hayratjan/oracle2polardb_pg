"""
Celery 异步任务：数据库迁移执行与定时增量扫描。
"""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def celery_run_migration_task(self, task_id: int, postgres_database=None):
    """在 Worker 中执行单次迁移任务。"""
    from .runner import run_migration_task

    logger.info('Celery 开始执行迁移任务 task_id=%s', task_id)
    run_migration_task(task_id, postgres_database)
    logger.info('Celery 完成迁移任务 task_id=%s', task_id)


@shared_task(bind=True, ignore_result=True)
def beat_scan_scheduled_migrations(self):
    """
    Beat 周期任务：扫描启用定时且为时间戳增量模式的表任务，按最小间隔触发执行。
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import MigrationTask

    if not getattr(settings, 'CELERY_BROKER_URL', '').strip():
        return
    now = timezone.now()
    qs = MigrationTask.objects.filter(
        schedule_enabled=True,
        incremental_mode='timestamp',
        task_type='table',
    ).exclude(status='running').exclude(watermark_column='')
    for task in qs:
        interval = max(1, int(task.schedule_interval_minutes or 60))
        if task.last_schedule_run:
            if now - task.last_schedule_run < timedelta(minutes=interval):
                continue
        task.last_schedule_run = now
        task.save(update_fields=['last_schedule_run'])
        celery_run_migration_task.delay(task.id, task.postgres_database or None)


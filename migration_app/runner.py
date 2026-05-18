"""
迁移任务统一执行入口：供 Django 线程池与 Celery Worker 调用。
"""
import importlib


def run_migration_task(task_id: int, postgres_database=None) -> None:
    """
    根据任务类型分发到具体迁移实现（同步阻塞直至任务结束）。
    """
    from django.shortcuts import get_object_or_404

    from . import views
    from .models import MigrationTask
    from . import dashboard as dash
    from .task_lifecycle import run_with_lifecycle

    def _execute():
        task = get_object_or_404(MigrationTask, pk=task_id)
        tt = task.task_type
        pgdb = postgres_database
        if pgdb is None and task.postgres_connection:
            pgdb = task.postgres_database or task.postgres_connection.database

        if tt == 'table':
            views.migrate_table(task_id, pgdb)
        elif tt == 'materialized_view':
            views.migrate_materialized_view(task_id, pgdb)
        elif tt == 'view':
            views.migrate_view(task_id, pgdb)
        elif tt == 'routine':
            views.migrate_routine(task_id, pgdb)
        elif tt == 'all_tables':
            import migration_app.views as v
            importlib.reload(v)
            v.migrate_all_tables(task_id, pgdb)
        elif tt == 'view_to_table':
            dash.migrate_view_to_table(task_id, pgdb)
        elif tt == 'view_to_sqlite':
            dash.migrate_view_to_sqlite(task_id)
        elif tt == 'trigger':
            views.migrate_trigger(task_id, pgdb)
        elif tt == 'sequence':
            views.migrate_sequence(task_id, pgdb)
        elif tt == 'full_schema':
            views.migrate_schema_orchestration(task_id, pgdb)
        else:
            raise ValueError(f'未知任务类型: {tt}')

    run_with_lifecycle(task_id, _execute)

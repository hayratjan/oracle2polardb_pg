from django.apps import AppConfig


class MigrationAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'migration_app'
    verbose_name = '数据库迁移'

    def ready(self):
        # 避免迁移/测试命令时误改数据
        import sys
        skip = {'makemigrations', 'migrate', 'test', 'shell'}
        if any(cmd in sys.argv for cmd in skip):
            return
        try:
            from .task_lifecycle import reconcile_all_orphan_running_on_startup
            reconcile_all_orphan_running_on_startup()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('启动时修正遗留 running 任务失败: %s', exc)

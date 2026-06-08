# Generated migration: exported 状态、视图迁移模式
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('migration_app', '0009_migrationtask_pk_mirror_incremental'),
    ]

    operations = [
        migrations.AlterField(
            model_name='migrationtask',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', '待执行'),
                    ('running', '执行中'),
                    ('completed', '已完成'),
                    ('failed', '失败'),
                    ('partial', '部分完成'),
                    ('canceled', '已取消'),
                    ('aborted', '异常停止'),
                    ('exported', '已导出待人工处理'),
                ],
                default='pending',
                max_length=20,
                verbose_name='状态',
            ),
        ),
        migrations.AddField(
            model_name='migrationtask',
            name='view_migration_mode',
            field=models.CharField(
                blank=True,
                choices=[
                    ('materialize', '物化到表（快照）'),
                    ('definition', '创建视图定义'),
                ],
                default='materialize',
                help_text='materialize=将视图数据写入目标表；definition=在目标库创建 CREATE VIEW',
                max_length=20,
                verbose_name='视图迁移模式',
            ),
        ),
    ]

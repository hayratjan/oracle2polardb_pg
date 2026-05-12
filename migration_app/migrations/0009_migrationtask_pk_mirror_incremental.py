# Generated manually for 主键对齐增量

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('migration_app', '0008_enterprise_migration_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='migrationtask',
            name='sync_max_pkey_rows',
            field=models.PositiveIntegerField(
                default=500_000,
                help_text='超过则拒绝执行主键对齐，避免 OOM；大表请用水位列增量或调大该值',
                verbose_name='主键对齐单次最大行数',
            ),
        ),
        migrations.AlterField(
            model_name='migrationtask',
            name='incremental_mode',
            field=models.CharField(
                choices=[
                    ('none', '全量'),
                    ('timestamp', '按水位列增量'),
                    ('pk_mirror', '主键对齐增量(定时增删)'),
                ],
                default='none',
                max_length=20,
                verbose_name='增量模式',
            ),
        ),
    ]

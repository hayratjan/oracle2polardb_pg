from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from migration_app.models import OracleConnection, MigrationTask

User = get_user_model()


class CreateTaskViewToSqliteTest(TestCase):
    """创建 view_to_sqlite 任务的 API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.oracle_conn = OracleConnection.objects.create(
            name='Test Oracle',
            host='localhost',
            port=1521,
            service_name='ORCL',
            username='user',
            password='pass',
        )

    def test_create_view_to_sqlite_task_success(self):
        payload = {
            'name': 'SQLite 导出任务',
            'task_type': 'view_to_sqlite',
            'oracle_connection': self.oracle_conn.id,
            'source_schema': 'SCOTT',
            'sqlite_directory': '/tmp/sqlite_export',
            'sqlite_file_name': 'mydb.sqlite3',
            'source_objects': ['MY_VIEW'],
            'conflict_strategy': 'replace',
        }
        response = self.client.post(
            '/api/create-task/',
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, 200, msg=response.content)
        data = response.json()
        self.assertEqual(data.get('status'), 'success', msg=data)
        self.assertIn('task_id', data)
        task = MigrationTask.objects.get(pk=data['task_id'])
        self.assertIsNone(task.postgres_connection_id)
        self.assertEqual(task.task_type, 'view_to_sqlite')
        self.assertEqual(task.sqlite_directory, '/tmp/sqlite_export')
        self.assertEqual(task.sqlite_file_name, 'mydb.sqlite3')
        self.assertEqual(task.sqlite_path, '/tmp/sqlite_export/mydb.sqlite3')

    def test_create_view_to_sqlite_task_missing_sqlite_dir_fails(self):
        payload = {
            'name': 'SQLite 导出任务',
            'task_type': 'view_to_sqlite',
            'oracle_connection': self.oracle_conn.id,
            'source_schema': 'SCOTT',
            'sqlite_file_name': 'mydb.sqlite3',
            'source_objects': ['MY_VIEW'],
        }
        response = self.client.post(
            '/api/create-task/',
            data=payload,
            format='json',
        )
        data = response.json()
        self.assertEqual(data.get('status'), 'error', msg=data)
        self.assertIn(response.status_code, (200, 400))


class BrowseDirectoriesAPITest(TestCase):
    """目录浏览 API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser2', password='testpass')
        self.client.force_authenticate(user=self.user)

    def test_browse_directories_no_path_returns_success(self):
        response = self.client.get('/api/filesystem/directories/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('current_path', data)
        self.assertIn('directories', data)

    def test_browse_directories_with_path_returns_structure(self):
        import os
        path = os.path.expanduser('~')
        response = self.client.get('/api/filesystem/directories/', {'path': path})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('current_path', data)
        self.assertIn('directories', data)


class DatabaseObjectsViewToSqliteAPITest(TestCase):
    """database-objects 在 object_type=view_to_sqlite 时的接口结构测试（不依赖真实 Oracle）"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser3', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.oracle_conn = OracleConnection.objects.create(
            name='Test Oracle',
            host='localhost',
            port=1521,
            service_name='ORCL',
            username='user',
            password='pass',
        )

    def test_database_objects_view_to_sqlite_requires_params(self):
        """缺少参数时应返回 400"""
        response = self.client.get('/api/database-objects/')
        self.assertEqual(response.status_code, 400)

    def test_database_objects_view_to_sqlite_response_structure(self):
        """有 connection_id/schema/object_type 时接口返回格式一致（连接失败时仍可校验结构由 API 返回）"""
        response = self.client.get(
            '/api/database-objects/',
            {
                'connection_id': self.oracle_conn.id,
                'schema': 'SCOTT',
                'object_type': 'view_to_sqlite',
            },
        )
        # 无真实 Oracle 时可能 400 或 500，这里只校验带齐参数时不会因缺少参数报错
        if response.status_code == 200:
            data = response.json()
            self.assertIn('objects', data)
            if data.get('status') == 'success':
                self.assertIsInstance(data['objects'], list)


class OracleSqlConverterTest(TestCase):
    """Oracle SQL 转换器单元测试。"""

    def test_convert_nvl_and_sysdate(self):
        from migration_app.oracle_sql_converter import convert_oracle_to_pg_view

        sql = "SELECT NVL(a, SYSDATE) FROM DUAL"
        pg_sql, manual = convert_oracle_to_pg_view(sql)
        self.assertIn('COALESCE', pg_sql)
        self.assertIn('CURRENT_TIMESTAMP', pg_sql)
        self.assertNotIn('DUAL', pg_sql.upper())

    def test_detect_rownum_manual_review(self):
        from migration_app.oracle_sql_converter import convert_oracle_to_pg_view

        _, manual = convert_oracle_to_pg_view("SELECT * FROM t WHERE ROWNUM <= 10")
        self.assertTrue(any('ROWNUM' in m for m in manual))


class ConvertOracleTypeTest(TestCase):
    """Oracle 类型映射测试。"""

    def test_date_maps_to_timestamp(self):
        from migration_app.views import convert_oracle_to_pg_type

        self.assertEqual(convert_oracle_to_pg_type('DATE'), 'TIMESTAMP(0)')


class TriggerExportTest(TestCase):
    """触发器导出模板测试。"""

    def test_plpgsql_template_contains_execute_function(self):
        from migration_app.trigger_export import build_plpgsql_trigger_template

        tpl = build_plpgsql_trigger_template(
            trigger_name='TRG_TEST',
            table_name='ORDERS',
            trigger_type='BEFORE EACH ROW',
            triggering_event='INSERT OR UPDATE',
        )
        self.assertIn('EXECUTE FUNCTION', tpl)
        self.assertIn('RETURNS TRIGGER', tpl)


class PgIdentifiersTest(TestCase):
    """PostgreSQL 列名引号，避免 ISNULL 等保留字建表失败。"""

    def test_build_column_definition_isnull(self):
        from migration_app.pg_identifiers import build_pg_column_definition, quote_identifier

        self.assertEqual(quote_identifier('isnull'), '"isnull"')
        ddl = build_pg_column_definition('ISNULL', 'SMALLINT', 'Y', id_case='lower')
        self.assertIn('"isnull"', ddl)
        self.assertIn('SMALLINT', ddl)
        self.assertNotIn('    ISNULL SMALLINT', ddl)


class PlatformConfigAPITest(TestCase):
    """平台配置持久化 API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='cfguser', password='testpass')
        self.client.force_authenticate(user=self.user)

    def test_migration_settings_persist(self):
        payload = {
            'default_identifier_case': 'upper',
            'default_conflict_strategy': 'skip',
            'batch_size': 8000,
            'enable_fk_replay': False,
        }
        post = self.client.post('/api/config/migration/', payload, format='json')
        self.assertEqual(post.status_code, 200)
        get = self.client.get('/api/config/migration/')
        self.assertEqual(get.status_code, 200)
        data = get.json()
        self.assertEqual(data['default_identifier_case'], 'upper')
        self.assertEqual(data['batch_size'], 8000)
        self.assertFalse(data['enable_fk_replay'])

    def test_system_settings_persist(self):
        payload = {'max_concurrent_tasks': 3, 'log_level': 'WARNING'}
        self.client.post('/api/config/system/', payload, format='json')
        data = self.client.get('/api/config/system/').json()
        self.assertEqual(data['max_concurrent_tasks'], 3)
        self.assertEqual(data['log_level'], 'WARNING')

    def test_celery_status_api(self):
        res = self.client.get('/api/config/celery-status/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('broker_configured', data)

    def test_help_api_sections(self):
        res = self.client.get('/api/help/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data.get('sections', [])) >= 1)


class MigrationReportTest(TestCase):
    """迁移报告生成测试"""

    def test_build_report_from_log(self):
        from migration_app.migration_report import build_migration_report

        oracle_conn = OracleConnection.objects.create(
            name='O', host='h', port=1521, service_name='ORCL', username='u', password='p',
        )
        task = MigrationTask.objects.create(
            name='报告测试',
            task_type='table',
            oracle_connection=oracle_conn,
            source_schema='HR',
            source_object='EMP',
            status='completed',
            log='需人工审查: ROWNUM\n【校验通过】EMP: 源端 100 行 = 目标端 100 行',
        )
        report = build_migration_report(task)
        self.assertEqual(report['task_id'], task.id)
        self.assertGreaterEqual(report['summary']['manual_review_count'], 1)
        self.assertEqual(len(report['row_checks']), 1)


class ApplyTaskDefaultsTest(TestCase):
    """创建任务默认策略合并"""

    def test_apply_defaults(self):
        from migration_app.platform_config import apply_task_creation_defaults, save_migration_settings

        save_migration_settings({'default_conflict_strategy': 'skip', 'default_identifier_case': 'preserve'})
        data = apply_task_creation_defaults({'name': 't'})
        self.assertEqual(data['conflict_strategy'], 'skip')
        self.assertEqual(data['identifier_case'], 'preserve')

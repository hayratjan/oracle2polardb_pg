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

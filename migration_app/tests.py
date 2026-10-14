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
        """测试在白名单内的路径能正常返回结构（v2.2 文件浏览沙箱限制只允许白名单目录）。"""
        import os
        from django.conf import settings
        # 使用白名单内的项目根目录，避免被沙箱拒绝
        path = settings.BROWSE_DIRECTORIES_WHITELIST[0] if settings.BROWSE_DIRECTORIES_WHITELIST else os.path.dirname(__file__)
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
        # v2.3: SystemSettingsAPIView 需要 IsAdmin 权限,测试用户需为 staff
        self.user = User.objects.create_superuser(username='cfgadmin', password='testpass', email='admin@test.local')
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


class JwtAuthOnLegacyApiViewsTest(TestCase):
    """
    回归：前端只发 Authorization: Bearer（client.ts withCredentials=false，无 cookie），
    而连接管理端点曾是 session-only 的 @login_required 视图，
    导致 POST /api/oracle/test-connection/ 返回 302 → /accounts/login/ 而非执行测试。
    """

    def setUp(self):
        from rest_framework_simplejwt.tokens import RefreshToken

        self.user = User.objects.create_user(username='jwtuser', password='testpass')
        self.token = str(RefreshToken.for_user(self.user).access_token)

    def _post(self, path):
        return self.client.post(
            path,
            data={'connection_id': 999999},  # 不存在的连接：不触真实网络即可返回 JSON
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )

    def test_oracle_test_connection_accepts_bearer_token(self):
        resp = self._post('/api/oracle/test-connection/')
        self.assertNotEqual(resp.status_code, 302, f'被重定向到 {resp.get("Location")}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('status', resp.json())

    def test_postgres_test_connection_accepts_bearer_token(self):
        resp = self._post('/api/postgres/test-connection/')
        self.assertNotEqual(resp.status_code, 302, f'被重定向到 {resp.get("Location")}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('status', resp.json())

    def test_invalid_token_is_rejected(self):
        resp = self.client.post(
            '/api/oracle/test-connection/',
            data={'connection_id': 999999},
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer not-a-valid-token',
        )
        self.assertEqual(resp.status_code, 401)

    def test_anonymous_request_is_rejected(self):
        resp = self.client.post(
            '/api/oracle/test-connection/',
            data={'connection_id': 999999},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_session_authenticated_html_page_still_redirects_for_anonymous(self):
        """/app/ 模板页面对匿名用户仍应跳转登录页，不因 API 侧改动而退化。"""
        resp = self.client.get('/api/app/oracle/database/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_legacy_html_endpoint_not_downgraded_to_json_401(self):
        """同一视图的 /api/ 与 /app/ 两个入口行为应各自保持：HTML 入口保留重定向。"""
        resp = self.client.post(
            '/api/app/oracle/test_connection/',
            data={'connection_id': 999999},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])


class OracleConnectErrorDiagnosticsTest(TestCase):
    """连接失败必须给出可自助定位的中文诊断，而不是整坨原始 DPY/ORA 文本。"""

    TARGET = '192.0.2.10:1521/ORCL'

    def _diag(self, text):
        import oracledb
        from migration_app.oracle_diagnostics import diagnose_oracle_connect_error
        return diagnose_oracle_connect_error(
            oracledb.DatabaseError(text), target=self.TARGET
        )

    def test_always_returns_three_fields(self):
        for payload in (self._diag('ORA-99999: something odd'),):
            self.assertEqual(set(payload), {'message', 'hint', 'detail'})
            self.assertTrue(payload['message'])

    def test_dpy_3010_explains_thin_mode_version_floor(self):
        payload = self._diag(
            'DPY-3010: connections to this database server version are not '
            'supported by python-oracledb in thin mode'
        )
        self.assertIn('12.1', payload['message'])
        self.assertIn('thin', payload['message'])
        self.assertIn('ORACLE_CLIENT_LIB', payload['hint'])

    def test_dpy_6005_wrapping_3010_still_diagnosed(self):
        payload = self._diag(
            'DPY-6005: cannot connect to database (CONNECTION_ID=n5dtv1IJogF5R0pmJ3Bb/A==).\n'
            'DPY-3010: connections to this database server version are not supported by '
            'python-oracledb in thin mode\n'
            'Help: https://python-oracledb.readthedocs.io/en/latest/user_guide/troubleshooting.html#dpy-3010'
        )
        self.assertIn('12.1', payload['message'])
        self.assertIn('ORACLE_CLIENT_LIB', payload['hint'])

    def test_detail_strips_noise(self):
        payload = self._diag(
            'DPY-6005: cannot connect to database (CONNECTION_ID=n5dtv1IJogF5R0pmJ3Bb/A==).\n'
            'DPY-3010: unsupported\nHelp: https://example.com/long/help/url'
        )
        self.assertNotIn('CONNECTION_ID', payload['detail'])
        self.assertNotIn('Help:', payload['detail'])

    def test_ora_01017_credentials(self):
        self.assertIn('密码', self._diag('ORA-01017: invalid username/password; logon denied')['message'])

    def test_ora_12541_listener(self):
        self.assertIn('监听', self._diag('ORA-12541: TNS:no listener')['message'])

    def test_ora_12514_service_name(self):
        self.assertIn('服务名', self._diag('ORA-12514: TNS:listener does not currently know of service requested')['message'])

    def test_ora_12170_timeout_names_target(self):
        payload = self._diag('ORA-12170: TNS:Connect timeout occurred')
        self.assertIn('超时', payload['message'])
        self.assertIn(self.TARGET, payload['message'])

    def test_dpi_1047_arch_mismatch(self):
        payload = self._diag('DPI-1047: Oracle Client libraries are not loaded, or are incompatible architecture')
        self.assertIn('Instant Client', payload['message'])

    def test_unknown_error_falls_back_to_raw_text(self):
        payload = self._diag('ORA-28000: the account is locked')
        self.assertIn('ORA-28000', payload['detail'])


class OracleConnectResourceGuardTest(TestCase):
    """连不上的库不得挂住 Django worker：连接必须带网络超时，语句必须带调用超时。

    注意 oracledb 2.5.1 的 connect() 只接受 tcp_connect_timeout，call_timeout
    是连接对象属性，必须连接后再设置。
    """

    def test_connect_passes_timeouts(self):
        from unittest.mock import patch
        from migration_app import views

        class FakeConn:
            def __init__(self):
                self.call_timeout = 0
                self.closed = False

            def close(self):
                self.closed = True

        conn = FakeConn()
        with patch.object(views.oracledb, 'connect', return_value=conn) as m_connect:
            ok, err = views._test_oracle_connect_with_params(
                'h', 1521, 'svc', 'user', 'pw'
            )

        self.assertTrue(ok, msg=f'预期成功，实际 {err}')
        kwargs = m_connect.call_args.kwargs
        self.assertGreater(kwargs.get('tcp_connect_timeout', 0), 0)
        self.assertLessEqual(kwargs.get('tcp_connect_timeout'), 15)
        self.assertGreater(conn.call_timeout, 0)
        self.assertTrue(conn.closed)


class OracleTestConnectionErrorPayloadTest(TestCase):
    """接口须把诊断三件套透传给前端，供页面分层展示。"""

    def setUp(self):
        import oracledb
        from rest_framework_simplejwt.tokens import RefreshToken
        self.user = User.objects.create_user(username='diag', password='testpass')
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.error = oracledb.DatabaseError(
            'DPY-6005: cannot connect to database (CONNECTION_ID=abc==).\n'
            'DPY-3010: connections to this database server version are not supported by '
            'python-oracledb in thin mode\nHelp: https://example.com/help'
        )

    def test_endpoint_returns_structured_error(self):
        from unittest.mock import patch
        from migration_app import views
        with patch.object(views.oracledb, 'connect', side_effect=self.error):
            resp = self.client.post(
                '/api/oracle/test-connection/',
                data={'host': '192.0.2.10', 'port': 1521, 'service_name': 'ORCL',
                      'username': 'appuser', 'password': 'x'},
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {self.token}',
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['status'], 'error')
        self.assertIn('12.1', body['message'])
        self.assertIn('ORACLE_CLIENT_LIB', body['hint'])
        self.assertNotIn('Help:', body['detail'])

    def test_endpoint_returns_success_shape(self):
        from unittest.mock import patch, MagicMock
        from migration_app import views
        with patch.object(views.oracledb, 'connect', return_value=MagicMock()):
            resp = self.client.post(
                '/api/oracle/test-connection/',
                data={'host': 'h', 'port': 1521, 'service_name': 's',
                      'username': 'u', 'password': 'p'},
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {self.token}',
            )
        self.assertEqual(resp.json()['status'], 'success')


_EFMIS_SIZE = 128849018880      # 120 GiB
_EFMIS_FREE = 23068672000
_SYSTEM_SIZE = 62544445440      # 58.2 GiB
_SYSTEM_FREE = 4718592000
_EFMIS_USED = _EFMIS_SIZE - _EFMIS_FREE
_SYSTEM_USED = _SYSTEM_SIZE - _SYSTEM_FREE
_SGA_COMPONENTS = 34206334976   # 2270360+4093643624+30064771072+45649920
_SGA_TARGET = 34359738368
_PGA_TARGET = 17179869184
_PGA_ALLOC = 383040512


class _FakeCursor:
    """按 SQL 内的 /* o2p:marker */ 路由返回值，模拟 oracledb cursor。"""

    def __init__(self, routes, fail_markers=()):
        self.routes = routes
        self.fail_markers = fail_markers
        self.rows = []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append(sql)
        for marker in self.fail_markers:
            if marker in sql:
                raise _ora_error(942, 'ORA-00942: table or view does not exist')
        for marker, rows in self.routes.items():
            if marker in sql:
                self.rows = rows
                return
        self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class _FakeConn:
    def __init__(self, routes, fail_markers=()):
        self._cursor = _FakeCursor(routes, fail_markers)
        self.closed = False
        self.call_timeout = 0

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def _ora_error(code, message):
    class _ErrInfo:
        def __init__(self):
            self.code = code
            self.message = message

    import oracledb
    exc = oracledb.DatabaseError(message)
    exc.args = (_ErrInfo(),)
    return exc


def _routes(with_fallbacks=True):
    routes = {
        'o2p:version': [('Oracle Database 11g Enterprise Edition Release 11.2.0.4.0 - 64bit Production',)],
        'o2p:instance': [('orcl1', 'dbhost1', '11.2.0.4.0', 'OPEN', 'ACTIVE', '2026-09-07 18:27:15')],
        'o2p:ping': [(1,)],
        'o2p:sga_components': [('Fixed Size', 2270360), ('Variable Size', 4093643624),
                               ('Database Buffers', 30064771072), ('Redo Buffers', 45649920)],
        'o2p:sga_target': [(str(_SGA_TARGET),)],
        'o2p:pga_target': [(str(_PGA_TARGET),)],
        'o2p:pga_alloc': [(_PGA_ALLOC,)],
        'o2p:datafiles': [(27, 242687549440)],
        # 故意以 SYSTEM 开头返回：若采集端未按占用量降序排列，下面的断言就会失败
        'o2p:ts_size': [('SYSTEM', _SYSTEM_SIZE), ('EFMIS', _EFMIS_SIZE)],
        'o2p:ts_used': [('SYSTEM', _SYSTEM_USED), ('EFMIS', _EFMIS_USED)],
        'o2p:ts_count': [(24,)],
        'o2p:all_segments': [('EFMIS', _EFMIS_USED)],
        'o2p:resource': [('64', '93', '1000')],
        'o2p:sessions': [(59, 2, 33)],
        'o2p:users': [(71,)],
        'o2p:tables': [(96342,)],
        'o2p:owner_tables': [(1234,)],
        'o2p:database': [('ORCL',)],
    }
    if with_fallbacks:
        routes['o2p:all_users'] = [(88,)]
        routes['o2p:all_tables'] = [(5000,)]
    return routes


class OracleInfoCollectorTest(TestCase):
    """指标采集必须逐项降级：单个视图无权限不得让整块面板失败。"""

    def _collect(self, fail_markers=(), schema=None, routes=None):
        from migration_app.oracle_info import collect_database_info
        conn = _FakeConn(routes or _routes(), fail_markers)
        return collect_database_info(conn, schema=schema), conn

    def test_returns_all_sections(self):
        info, _ = self._collect()
        for key in ('version', 'instance', 'memory', 'storage', 'sessions', 'processes', 'counts'):
            self.assertIn(key, info, msg=f'缺少区块 {key}')
        self.assertIsInstance(info['ping_ms'], int)
        self.assertEqual(info['errors'], {})

    def test_version_and_instance(self):
        info, _ = self._collect()
        self.assertIn('11.2.0.4.0', info['version']['banner'])
        self.assertEqual(info['version']['release'], '11.2.0.4.0')
        self.assertEqual(info['instance']['instance_name'], 'orcl1')
        self.assertEqual(info['instance']['host_name'], 'dbhost1')
        self.assertEqual(info['instance']['status'], 'OPEN')
        self.assertEqual(info['instance']['startup_time'], '2026-09-07 18:27:15')

    def test_memory_sga_is_summed_from_components(self):
        info, _ = self._collect()
        self.assertEqual(info['memory']['sga_used_bytes'], _SGA_COMPONENTS)
        self.assertEqual(info['memory']['sga_target_bytes'], _SGA_TARGET)
        self.assertEqual(info['memory']['pga_allocated_bytes'], _PGA_ALLOC)
        self.assertEqual(info['memory']['pga_target_bytes'], _PGA_TARGET)

    def test_storage_totals_and_tablespace_usage(self):
        info, _ = self._collect()
        self.assertEqual(info['storage']['datafile_count'], 27)
        self.assertEqual(info['storage']['datafile_bytes'], 242687549440)
        self.assertEqual(info['storage']['tablespace_count'], 24)
        first, second = info['storage']['tablespaces']
        self.assertEqual(first['name'], 'EFMIS')
        self.assertEqual(first['size_bytes'], _EFMIS_SIZE)
        self.assertEqual(first['used_bytes'], _EFMIS_USED)
        self.assertEqual(first['used_pct'], round(_EFMIS_USED / _EFMIS_SIZE * 100, 1))
        self.assertEqual(second['name'], 'SYSTEM')
        # 按占用量降序：EFMIS 用量最大排首位（其使用率低于 SYSTEM，用于证明排序键是字节而非百分比）
        self.assertLess(first['used_pct'], second['used_pct'])

    def test_tablespace_used_falls_back_to_all_segments(self):
        info, _ = self._collect(fail_markers=('o2p:ts_used',))
        self.assertEqual(info['storage']['tablespaces'][0]['name'], 'EFMIS')
        self.assertEqual(info['storage']['tablespaces'][0]['used_bytes'], _EFMIS_USED)
        self.assertEqual(info['errors']['tablespaces'], 'ORA-00942')

    def test_tablespace_usage_absent_when_both_sources_denied(self):
        info, _ = self._collect(fail_markers=('o2p:ts_used', 'o2p:all_segments'))
        self.assertEqual(info['storage']['tablespaces'], [])
        self.assertEqual(info['storage']['tablespace_count'], 24)
        self.assertIn('tablespaces', info['errors'])

    def test_sessions_and_processes(self):
        info, _ = self._collect()
        self.assertEqual(info['sessions']['total'], 59)
        self.assertEqual(info['sessions']['active_user'], 2)
        self.assertEqual(info['sessions']['background'], 33)
        self.assertEqual(info['processes']['current'], 64)
        self.assertEqual(info['processes']['peak'], 93)
        self.assertEqual(info['processes']['limit'], 1000)

    def test_counts(self):
        info, _ = self._collect()
        self.assertEqual(info['counts']['users'], 71)
        self.assertEqual(info['counts']['tables'], 96342)
        self.assertEqual(info['counts']['database_name'], 'ORCL')

    def test_schema_scoped_table_count_skips_whole_database_scan(self):
        info, conn = self._collect(schema='EFMIS')
        self.assertEqual(info['counts']['tables'], 1234)
        self.assertEqual(info['counts']['schema'], 'EFMIS')
        executed = ' '.join(conn._cursor.executed)
        self.assertNotIn('o2p:tables ', executed)

    def test_users_denied_falls_back_to_all_users(self):
        info, _ = self._collect(fail_markers=('o2p:users',))
        self.assertEqual(info['counts']['users'], 88)
        self.assertEqual(info['errors']['users'], 'ORA-00942')

    def test_sga_denied_falls_back_to_sga_target(self):
        info, _ = self._collect(fail_markers=('o2p:sga_components',))
        self.assertEqual(info['memory']['sga_used_bytes'], _SGA_TARGET)
        self.assertEqual(info['errors']['sga_used'], 'ORA-00942')

    def test_metric_unavailable_when_all_sources_denied(self):
        info, _ = self._collect(fail_markers=('o2p:users', 'o2p:all_users', 'o2p:tables', 'o2p:all_tables'))
        self.assertIsNone(info['counts']['users'])
        self.assertIsNone(info['counts']['tables'])
        self.assertEqual(set(info['errors']) >= {'users', 'tables'}, True)

    def test_missing_optional_metric_is_not_an_error(self):
        """11g 无 v$pdbs：查不到属正常降级，不应记入 errors。"""
        info, _ = self._collect()
        self.assertNotIn('pdb_count', info['counts'])
        self.assertNotIn('pdbs', info['errors'])

    def test_tablespace_count_falls_back_to_datafile_groups(self):
        info, _ = self._collect(fail_markers=('o2p:ts_count',))
        self.assertEqual(info['storage']['tablespace_count'], 2)
        self.assertEqual(info['errors']['tablespace_count'], 'ORA-00942')

    def test_collector_does_not_close_connection(self):
        _, conn = self._collect()
        self.assertFalse(conn.closed)


class DatabaseInfoAPIViewTest(TestCase):
    """GET /api/database-info/ 原本是空 stub，现须返回真实指标并带资源守卫。"""

    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.user = User.objects.create_user(username='info', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.conn = OracleConnection.objects.create(
            name='ORCL', host='192.0.2.10', port=1521,
            service_name='ORCL', username='appuser', password='pw',
        )

    def _patch(self, conn=None, side_effect=None):
        from unittest.mock import patch
        target = conn if conn is not None else _FakeConn(_routes())
        return patch('migration_app.views.get_oracle_connection',
                     return_value=target, side_effect=side_effect), target

    def test_requires_connection_id(self):
        resp = self.client.get('/api/database-info/')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')

    def test_unknown_connection_returns_404(self):
        resp = self.client.get('/api/database-info/?connection_id=999999')
        self.assertEqual(resp.status_code, 404)

    def test_returns_metrics(self):
        ctx, fake = self._patch()
        with ctx:
            resp = self.client.get(f'/api/database-info/?connection_id={self.conn.pk}')
        self.assertEqual(resp.status_code, 200)
        body = resp.data
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['connection_name'], 'ORCL')
        self.assertEqual(body['counts']['users'], 71)
        self.assertEqual(body['memory']['sga_used_bytes'], _SGA_COMPONENTS)
        self.assertEqual(body['storage']['datafile_count'], 27)
        self.assertIsInstance(body['ping_ms'], int)

    def test_reports_both_latencies(self):
        """ping_ms 是池内热连接的查询往返，acquire_ms 是获取连接耗时（首次含握手）。
        只报一个会让用户把 1ms 误读成网络延迟。"""
        ctx, _ = self._patch()
        with ctx:
            resp = self.client.get(f'/api/database-info/?connection_id={self.conn.pk}')
        body = resp.data
        self.assertIsInstance(body['ping_ms'], int)
        self.assertIsInstance(body['acquire_ms'], int)
        self.assertGreaterEqual(body['acquire_ms'], 0)

    def test_connection_is_closed_after_request(self):
        ctx, fake = self._patch()
        with ctx:
            self.client.get(f'/api/database-info/?connection_id={self.conn.pk}')
        self.assertTrue(fake.closed, '请求结束必须归还/关闭连接')

    def test_uses_bounded_call_timeout(self):
        from unittest.mock import patch
        fake = _FakeConn(_routes())
        with patch('migration_app.views.get_oracle_connection', return_value=fake) as m:
            self.client.get(f'/api/database-info/?connection_id={self.conn.pk}')
        kwargs = m.call_args.kwargs
        self.assertLessEqual(kwargs.get('call_timeout_ms', 0), 20_000)

    def test_schema_param_scopes_table_count(self):
        ctx, _ = self._patch()
        with ctx:
            resp = self.client.get(f'/api/database-info/?connection_id={self.conn.pk}&schema=EFMIS')
        self.assertEqual(resp.data['counts']['tables'], 1234)
        self.assertEqual(resp.data['counts']['schema'], 'EFMIS')

    def test_connect_failure_returns_diagnosis(self):
        import oracledb
        _, _ = self._patch()
        err = oracledb.DatabaseError(
            'DPY-6005: cannot connect to database (CONNECTION_ID=abc==).\n'
            'DPY-3010: connections to this database server version are not supported by '
            'python-oracledb in thin mode\nHelp: https://example.com/help'
        )
        from unittest.mock import patch
        with patch('migration_app.views.get_oracle_connection', side_effect=err):
            resp = self.client.get(f'/api/database-info/?connection_id={self.conn.pk}')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('12.1', resp.data['message'])
        self.assertIn('ORACLE_CLIENT_LIB', resp.data['hint'])
        self.assertNotIn('Help:', resp.data['detail'])


class OracleDsnBuilderTest(TestCase):
    """oracledb 2.5.1 thick 模式会忽略 connect 的 tcp_connect_timeout（实测挂 60s），
    只有 Oracle Net 描述符参数 CONNECT_TIMEOUT / RETRY_COUNT 真正约束握手耗时。
    thin 模式相反，只认 tcp_connect_timeout，所以两者都要带上。"""

    def test_dsn_bounds_connect_timeout(self):
        from migration_app.oracle_dsn import build_dsn
        dsn = build_dsn('192.0.2.10', 1521, 'ORCL')
        self.assertIn('(HOST=192.0.2.10)', dsn)
        self.assertIn('(PORT=1521)', dsn)
        self.assertIn('(SERVICE_NAME=ORCL)', dsn)
        self.assertIn('(RETRY_COUNT=0)', dsn)

    def test_dsn_timeout_value_is_bounded(self):
        import re
        from migration_app.oracle_dsn import build_dsn
        match = re.search(r'\(CONNECT_TIMEOUT=(\d+)\)', build_dsn('h', 1521, 's'))
        self.assertIsNotNone(match, msg='DSN 缺少 CONNECT_TIMEOUT')
        self.assertGreater(int(match.group(1)), 0)
        self.assertLessEqual(int(match.group(1)), 15)

    def test_dsn_rejects_injectable_service_name(self):
        """host/service_name 来自用户录入的库配置，拼进描述符前必须经 oracledb 校验，
        否则一个带右括号的值就能注入任意 Oracle Net 参数。"""
        import oracledb
        from migration_app.oracle_dsn import build_dsn
        with self.assertRaises(oracledb.ProgrammingError):
            build_dsn('h', 1521, 'BAD)NAME')


class OracleDriverTimeoutTest(TestCase):
    """三处建连入口交给驱动的 DSN 都必须自带握手超时。"""

    class _FakeConn:
        def __init__(self):
            self.call_timeout = 0
            self.closed = False

        def close(self):
            self.closed = True

    def test_test_connection_passes_bounded_dsn(self):
        from unittest.mock import patch
        from migration_app import views

        conn = self._FakeConn()
        with patch.object(views.oracledb, 'connect', return_value=conn) as m_connect:
            ok, err = views._test_oracle_connect_with_params(
                '192.0.2.10', 1521, 'ORCL', 'user', 'pw'
            )

        self.assertTrue(ok, msg=f'预期成功，实际 {err}')
        dsn = m_connect.call_args.kwargs['dsn']
        self.assertIn('(CONNECT_TIMEOUT=', dsn)
        self.assertIn('(RETRY_COUNT=0)', dsn)
        # thin 模式仍依赖该参数
        self.assertGreater(m_connect.call_args.kwargs.get('tcp_connect_timeout', 0), 0)

    def test_direct_connection_passes_bounded_dsn(self):
        from unittest.mock import patch
        from migration_app import views

        conn_obj = OracleConnection.objects.create(
            name='direct', host='192.0.2.10', port=1521,
            service_name='ORCL', username='appuser', password='pw',
        )
        fake = self._FakeConn()
        with patch.object(views.oracledb, 'connect', return_value=fake) as m_connect:
            views._get_oracle_connection_direct(conn_obj.pk, call_timeout_ms=5000)

        self.assertIn('(CONNECT_TIMEOUT=', m_connect.call_args.kwargs['dsn'])
        self.assertIn('(RETRY_COUNT=0)', m_connect.call_args.kwargs['dsn'])
        self.assertEqual(fake.call_timeout, 5000)

    def test_pool_creation_passes_bounded_dsn(self):
        from unittest.mock import patch, MagicMock
        from migration_app import connection_pool as cp

        conn_obj = OracleConnection.objects.create(
            name='pool', host='192.0.2.10', port=1521,
            service_name='ORCL', username='appuser', password='pw',
        )
        self.addCleanup(cp._oracle_pools.pop, conn_obj.pk, None)
        pool = MagicMock()
        pool.acquire.return_value = self._FakeConn()
        with patch.object(cp.oracledb, 'create_pool', return_value=pool) as m_pool:
            cp.get_oracle_pooled_connection(conn_obj.pk)

        dsn = m_pool.call_args.kwargs['dsn']
        self.assertIn('(CONNECT_TIMEOUT=', dsn)
        self.assertIn('(RETRY_COUNT=0)', dsn)
        self.assertGreater(m_pool.call_args.kwargs.get('tcp_connect_timeout', 0), 0)

    def test_slow_host_does_not_block_other_hosts(self):
        """建池曾在全局锁内执行：一个不可达库会把所有 Oracle 请求串行拖住。

        连接配置用桩对象替代 ORM —— Django TestCase 的事务连接不能在子线程里复用。
        """
        import threading
        import time
        from types import SimpleNamespace
        from unittest.mock import patch, MagicMock
        from migration_app import connection_pool as cp

        configs = {
            1: SimpleNamespace(host='10.0.0.1', port=1521, service_name='SLOW',
                               username='u', password='pw'),
            2: SimpleNamespace(host='10.0.0.2', port=1521, service_name='FAST',
                               username='u', password='pw'),
        }
        self.addCleanup(cp._oracle_pools.clear)
        SLEEP = 0.6

        def fake_create_pool(**kwargs):
            if '10.0.0.1' in kwargs['dsn']:
                time.sleep(SLEEP)
            pool = MagicMock()
            pool.acquire.return_value = self._FakeConn()
            return pool

        errors = []

        def open_connection(conn_id):
            try:
                cp.get_oracle_pooled_connection(conn_id)
            except Exception as exc:  # pragma: no cover - 仅用于诊断
                errors.append(exc)

        with patch.object(cp.oracledb, 'create_pool', side_effect=fake_create_pool), \
                patch.object(cp, 'get_object_or_404', side_effect=lambda _m, **kw: configs[kw['pk']]):
            slow_thread = threading.Thread(target=open_connection, args=(1,))
            slow_thread.start()
            time.sleep(0.05)  # 确保慢池先占住资源
            started = time.monotonic()
            open_connection(2)
            fast_elapsed = time.monotonic() - started
            slow_thread.join(timeout=SLEEP * 4)

        self.assertEqual(errors, [])
        self.assertLess(
            fast_elapsed, SLEEP / 2,
            msg=f'快池等待了 {fast_elapsed:.2f}s，说明建池仍被全局锁串行化',
        )


class _FakePgConn:
    """psycopg2 连接桩：出错后事务进入 aborted 状态，必须 rollback 才能继续查询，
    所以这里记录 rollback 次数供断言。"""

    def __init__(self, routes, fail_markers=()):
        self._cursor = _FakeCursor(routes, fail_markers)
        self.closed = False
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


_PG_SHARED_BUFFERS = 32 * 1024 ** 3
_PG_WORK_MEM = 4 * 1024 * 1024
_PG_CACHE = 12 * 1024 ** 3


def _pg_routes(shmem_col='allocated_size'):
    return {
        'o2p:ping': [(1,)],
        'o2p:pgver': [('PostgreSQL 17.9 (PolarDB 17.9.1.0 build 248cd221) on x86_64-linux-gnu',)],
        'o2p:polarver': [('17.9.1.0',)],
        'o2p:inst': [('migration_meta', '2026-09-21 16:32:04', 1930000.0)],
        'o2p:settings': [
            ('shared_buffers', '4194304', '8kB'),
            ('work_mem', '4096', 'kB'),
            ('effective_cache_size', '1572864', '8kB'),
            ('max_connections', '200', None),
            ('superuser_reserved_connections', '3', None),
        ],
        'o2p:counts': [(21, 19, 4, 3, 2)],
        'o2p:sessions': [(9, 1, 6)],
        'o2p:dbsize': [(8214195,)],
        # 故意小到大返回：若未按占用降序排序，Top 5 断言就会失败
        'o2p:dblist': [('small_db', 1000), ('appdb_2024', 6690218511), ('efmis_old', 4000)],
        'o2p:shmemcol': [(shmem_col,)],
        'o2p:shmemsum': [(18_000_000_000,)],
    }


class PgInfoCollectorTest(TestCase):
    """PolarDB-PG 指标采集：逐条降级，且出错后必须回滚，否则后续查询会全部失败。"""

    def _collect(self, fail_markers=(), routes=None):
        from migration_app.pg_info import collect_database_info
        conn = _FakePgConn(routes or _pg_routes(), fail_markers)
        return collect_database_info(conn), conn

    def test_returns_all_sections(self):
        info, _ = self._collect()
        for key in ('version', 'instance', 'memory', 'sessions', 'counts', 'storage'):
            self.assertIn(key, info, msg=f'缺少区块 {key}')
        self.assertEqual(info['errors'], {})

    def test_reads_version_and_polar_version(self):
        info, _ = self._collect()
        self.assertEqual(info['version']['server_version'], '17.9')
        self.assertEqual(info['version']['polar_version'], '17.9.1.0')

    def test_polar_version_falls_back_to_banner(self):
        """线上实测：PolarDB 17.9.1.0 没有 polar_version()，但 version() 的 banner 里带着它。"""
        routes = _pg_routes()
        routes['o2p:polarver'] = []
        info, _ = self._collect(routes=routes)
        self.assertEqual(info['version']['polar_version'], '17.9.1.0')
        self.assertEqual(info['errors'], {})

    def test_community_pg_reports_no_polar_version(self):
        """社区版既没有函数、banner 里也没有 PolarDB 字样：属预期缺失而非故障。"""
        routes = _pg_routes()
        routes['o2p:polarver'] = []
        routes['o2p:pgver'] = [('PostgreSQL 17.9 on x86_64-linux-gnu',)]
        info, _ = self._collect(routes=routes)
        self.assertIsNone(info['version']['polar_version'])
        self.assertEqual(info['version']['server_version'], '17.9')
        self.assertEqual(info['errors'], {})

    def test_counts_are_scoped_to_current_database(self):
        info, _ = self._collect()
        self.assertEqual(info['counts']['databases'], 21)
        self.assertEqual(info['counts']['roles'], 19)
        self.assertEqual(info['counts']['non_system_roles'], 4)
        self.assertEqual(info['counts']['tables'], 2)
        self.assertEqual(info['counts']['database_name'], 'migration_meta')

    def test_memory_uses_setting_units(self):
        info, _ = self._collect()
        self.assertEqual(info['memory']['shared_buffers_bytes'], _PG_SHARED_BUFFERS)
        self.assertEqual(info['memory']['work_mem_bytes'], _PG_WORK_MEM)
        self.assertEqual(info['memory']['effective_cache_size_bytes'], _PG_CACHE)
        self.assertEqual(info['memory']['shmem_allocated_bytes'], 18_000_000_000)

    def test_shmem_column_name_follows_the_server(self):
        """PolarDB 的 pg_shmem_allocations 列名是 allocated_size，社区版是 allocated_bytes。"""
        routes = _pg_routes(shmem_col='allocated_bytes')
        info, conn = self._collect(routes=routes)
        self.assertEqual(info['memory']['shmem_allocated_bytes'], 18_000_000_000)
        sum_sql = [sql for sql in conn._cursor.executed if 'o2p:shmemsum' in sql]
        self.assertTrue(sum_sql, msg='未发起共享内存求和查询')
        self.assertIn('allocated_bytes', sum_sql[0])
        self.assertNotIn('allocated_size', sum_sql[0])

    def test_sessions_and_limits(self):
        info, _ = self._collect()
        self.assertEqual(info['sessions'], {'total': 9, 'active': 1, 'idle': 6,
                                            'max': 200, 'superuser_reserved': 3})

    def test_top_databases_sorted_by_size_desc(self):
        info, _ = self._collect()
        names = [db['name'] for db in info['storage']['top_databases']]
        self.assertEqual(names, ['appdb_2024', 'efmis_old', 'small_db'])
        self.assertEqual(info['storage']['instance_total_bytes'], 6690223511)
        self.assertEqual(info['storage']['current_database_bytes'], 8214195)

    def test_single_failure_degrades_only_that_metric(self):
        info, conn = self._collect(fail_markers=('o2p:dblist',))
        self.assertIn('storage.top_databases', info['errors'])
        self.assertEqual(info['storage']['top_databases'], [])
        self.assertEqual(info['counts']['databases'], 21, msg='其他区块不应被牵连')
        self.assertGreaterEqual(conn.rollbacks, 1, msg='查询失败后必须回滚，否则后续全部报错')

    def test_collector_does_not_close_connection(self):
        _, conn = self._collect()
        self.assertFalse(conn.closed)


class PgDatabaseInfoAPIViewTest(TestCase):
    """GET /api/polardb/info/ —— 与 Oracle 侧同形状，并带语句超时守卫。"""

    def setUp(self):
        from rest_framework.test import APIClient
        from migration_app.models import PostgresConnection
        self.client = APIClient()
        self.user = User.objects.create_user(username='pginfo', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.conn = PostgresConnection.objects.create(
            name='meta', host='192.0.2.20', port=5432,
            database='migration_meta', username='appuser', password='pw',
        )

    def _patch(self, conn=None, side_effect=None):
        from unittest.mock import patch
        target = conn if conn is not None else _FakePgConn(_pg_routes())
        return patch('migration_app.views.get_postgres_connection',
                     return_value=target, side_effect=side_effect), target

    def test_requires_connection_id(self):
        resp = self.client.get('/api/polardb/info/')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')

    def test_unknown_connection_returns_404(self):
        resp = self.client.get('/api/polardb/info/?connection_id=999999')
        self.assertEqual(resp.status_code, 404)

    def test_returns_metrics_and_both_latencies(self):
        ctx, fake = self._patch()
        with ctx:
            resp = self.client.get(f'/api/polardb/info/?connection_id={self.conn.pk}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'success')
        self.assertEqual(resp.data['connection_name'], 'meta')
        self.assertEqual(resp.data['target'], '192.0.2.20:5432/migration_meta')
        self.assertIn('ping_ms', resp.data)
        self.assertIn('acquire_ms', resp.data)
        self.assertEqual(resp.data['counts']['databases'], 21)
        # get_postgres_connection 返回池代理，close() 即归还；不调用会漏连接、耗尽池
        self.assertTrue(fake.closed, msg='请求结束必须归还/关闭连接')

    def test_statement_timeout_is_bounded_and_reset(self):
        """只读探测不得留下会话级超时：池连接会被其他迁移任务复用。"""
        ctx, fake = self._patch()
        with ctx:
            self.client.get(f'/api/polardb/info/?connection_id={self.conn.pk}')
        executed = ' || '.join(fake._cursor.executed)
        self.assertIn('set statement_timeout', executed)
        timeout_sql = [s for s in fake._cursor.executed if 'set statement_timeout' in s][0]
        limit = int([tok for tok in timeout_sql.split() if tok.isdigit()][0])
        self.assertGreater(limit, 0)
        self.assertLessEqual(limit, 15_000, msg='语句超时上限过大，会拖住 worker')
        self.assertIn('reset statement_timeout', executed)

    def test_reset_runs_even_when_collection_fails(self):
        import psycopg2
        from unittest.mock import patch
        ctx, fake = self._patch()
        with ctx:
            with patch('migration_app.pg_info.collect_database_info',
                       side_effect=psycopg2.OperationalError('server closed the connection')):
                resp = self.client.get(f'/api/polardb/info/?connection_id={self.conn.pk}')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['status'], 'error')
        self.assertIn('reset statement_timeout', ' || '.join(fake._cursor.executed))


class SpaFallbackAndStaticTest(TestCase):
    """合并镜像后由 Django 单进程托管 Vue SPA：深层路由回退 index.html，
    且不能把 /api、/admin 等真实前缀的 404 吞成页面；静态资源交给 WhiteNoise。"""

    def setUp(self):
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        (root / 'assets').mkdir()
        (root / 'index.html').write_text('<html>SPA-INDEX-MARKER</html>', encoding='utf-8')
        (root / 'assets' / 'app-hash.js').write_text('console.log("ASSET-MARKER")', encoding='utf-8')
        self.dist = root

    def _get(self, url, **overrides):
        from django.test import override_settings
        base = dict(VITE_BUILD_DIR=str(self.dist),
                    WHITENOISE_ROOT=str(self.dist),
                    DEBUG=False,
                    ROOT_URLCONF='oracle2polardb_pg.urls')
        base.update(overrides)
        with override_settings(**base):
            return self.client.get(url)

    def test_deep_link_falls_back_to_index(self):
        resp = self._get('/postgres')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('SPA-INDEX-MARKER', resp.content.decode())

    def test_api_paths_are_not_swallowed_by_fallback(self):
        # /api/ 前缀命中但内部无匹配时 Django 会继续向下匹配，回退路由必须显式让行
        resp = self._get('/api/definitely-not-an-endpoint/')
        self.assertEqual(resp.status_code, 404)

    def test_healthz_probe_still_served(self):
        resp = self._get('/healthz')
        self.assertEqual(resp.status_code, 200)

    def test_admin_prefix_not_shadowed(self):
        resp = self._get('/admin/')
        self.assertIn(resp.status_code, (302, 200))
        if resp.status_code == 200:
            self.assertNotIn('SPA-INDEX-MARKER', resp.content.decode())

    def test_non_get_is_rejected_not_served_index(self):
        from django.test import override_settings
        with override_settings(VITE_BUILD_DIR=str(self.dist), DEBUG=False):
            resp = self.client.post('/postgres')
        self.assertEqual(resp.status_code, 405)

    def test_fallback_404s_without_build_artifacts(self):
        import os
        empty = self._tmp.name + '-empty'
        os.makedirs(empty, exist_ok=True)
        resp = self._get('/postgres', VITE_BUILD_DIR=empty, WHITENOISE_ROOT=empty)
        self.assertEqual(resp.status_code, 404)

    def test_asset_served_from_build_dir(self):
        resp = self._get('/assets/app-hash.js')
        self.assertEqual(resp.status_code, 200, msg='静态资源应由 WhiteNoise 从 WHITENOISE_ROOT 直出')
        # WhiteNoise 用流式响应，没有 .content；断言必须读 streaming_content
        body = b''.join(resp.streaming_content) if getattr(resp, 'streaming', False) else resp.content
        self.assertIn('ASSET-MARKER', body.decode())


class WhiteNoiseConfigTest(TestCase):
    """WhiteNoise 必须排在 SecurityMiddleware 之后、CommonMiddleware 之前，
    否则 GZip/压缩中间件会先接管响应，命中不了缓存的静态文件。"""

    def test_middleware_installed(self):
        from django.conf import settings
        mw = list(settings.MIDDLEWARE)
        self.assertIn('whitenoise.middleware.WhiteNoiseMiddleware', mw)
        self.assertLess(mw.index('django.middleware.security.SecurityMiddleware'),
                        mw.index('whitenoise.middleware.WhiteNoiseMiddleware'))
        self.assertLess(mw.index('whitenoise.middleware.WhiteNoiseMiddleware'),
                        mw.index('django.middleware.common.CommonMiddleware'))

    def test_static_root_uses_compressed_manifest_storage(self):
        from django.conf import settings
        storages = getattr(settings, 'STORAGES', {})
        backend = storages.get('staticfiles', {}).get('BACKEND', '')
        self.assertIn('CompressedManifestStaticFilesStorage', backend)


class ProbeHostExemptionTest(TestCase):
    """镜像/compose 的健康检查从 localhost 打 /healthz，而生产 ALLOWED_HOSTS 只配真实域名时
    Django 的 Host 校验会把探针变成 400 → 容器永远 unhealthy。豁免只能覆盖探针本身。"""

    def _get(self, url, allowed=('migration.example.com',), host='localhost'):
        from django.test import override_settings
        with override_settings(ALLOWED_HOSTS=list(allowed), DEBUG=False, SECURE_SSL_REDIRECT=False):
            return self.client.get(url, headers={'host': host})

    def test_healthz_served_when_host_is_localhost(self):
        resp = self._get('/healthz')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')

    def test_readyz_served_when_host_is_localhost(self):
        # 200(连得上)或 503(连不上)都算探针真正执行过；400 才是被 Host 校验半路拦下
        self.assertIn(self._get('/readyz').status_code, (200, 503))

    def test_subdomain_wildcard_allowlist_still_probeable(self):
        # Django 的写法是 .example.com（不是 *.example.com）；改写目标必须落在它真正接受的 Host 上
        self.assertEqual(self._get('/healthz', allowed=('.example.com',)).status_code, 200)

    def test_unsupportable_allowlist_yields_no_rewrite_target(self):
        """'mg.*' 这类写法 Django 对任何 Host 都拒绝，属于整站配错。

        不在 HTTP 层断言：get_host() 的 is_valid_host 先就把带 '*' 的 Host 拒了，
        无论改写逻辑怎么写结果都是 400，那样的断言没有牙。直接验选择函数的契约。
        """
        from django.http.request import validate_host
        from oracle2polardb_pg.probe_host import _stand_in_host
        self.assertIsNone(_stand_in_host(['mg.*']))
        self.assertEqual(_stand_in_host(['migration.example.com']), 'migration.example.com')
        self.assertTrue(validate_host(_stand_in_host(['.example.com']), ['.example.com']))

    def test_real_host_is_untouched(self):
        self.assertEqual(self._get('/healthz', host='migration.example.com').status_code, 200)

    def test_non_probe_paths_keep_strict_validation(self):
        self.assertEqual(self._get('/admin/').status_code, 400)
        self.assertEqual(self._get('/api/oracle/connections/').status_code, 400)

    def test_probe_lookalike_is_not_exempt(self):
        self.assertEqual(self._get('/healthzz').status_code, 400)

    def test_middleware_runs_before_security_middleware(self):
        from django.conf import settings
        mw = list(settings.MIDDLEWARE)
        self.assertIn('oracle2polardb_pg.probe_host.ProbeHostExemptionMiddleware', mw)
        self.assertLess(mw.index('oracle2polardb_pg.probe_host.ProbeHostExemptionMiddleware'),
                        mw.index('django.middleware.security.SecurityMiddleware'))


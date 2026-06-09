from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from .models import OracleConnection, PostgresConnection, MigrationTask
from .serializers import (
    OracleConnectionSerializer,
    PostgresConnectionSerializer,
    MigrationTaskSerializer,
    MigrationTaskListSerializer,
    MigrationTaskLogSerializer,
)
from . import dashboard
from . import create_task
import json
import psycopg2


class OracleConnectionViewSet(viewsets.ModelViewSet):
    queryset = OracleConnection.objects.all().order_by('id')
    serializer_class = OracleConnectionSerializer


class PostgresConnectionViewSet(viewsets.ModelViewSet):
    queryset = PostgresConnection.objects.all().order_by('id')
    serializer_class = PostgresConnectionSerializer
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        connection = self.get_object()
        try:
            from .views import test_pg_connection as test_conn
            result = test_conn(request, connection_id=pk)
            return Response(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            
            if not username or not password:
                return Response({
                    'status': 'error',
                    'message': '用户名和密码不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'status': 'success',
                    'message': '登录成功',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'username': user.username,
                        'email': user.email if hasattr(user, 'email') else ''
                    }
                })
            else:
                return Response({
                    'status': 'error',
                    'message': '用户名或密码错误'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'登录失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    print(f'Blacklist token error: {e}')
            
            logout(request)
            return Response({
                'status': 'success',
                'message': '登出成功'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'登出失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class CheckAuthAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        try:
            if request.user.is_authenticated:
                return Response({
                    'status': 'success',
                    'authenticated': True,
                    'user': {
                        'username': request.user.username,
                        'email': request.user.email if hasattr(request.user, 'email') else ''
                    }
                })
            else:
                return Response({
                    'status': 'success',
                    'authenticated': False
                })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'检查认证状态失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MigrationTaskViewSet(viewsets.ModelViewSet):
    # 按创建时间倒序，避免分页时 UnorderedObjectListWarning
    queryset = MigrationTask.objects.all().order_by('-created_at')
    serializer_class = MigrationTaskSerializer

    def retrieve(self, request, *args, **kwargs):
        """任务详情；仅当 ?reconcile=1 时修正孤儿 running（避免频繁 GET 误杀仍在其它进程执行的任务）。"""
        instance = self.get_object()
        if request.query_params.get('reconcile') == '1':
            from .task_lifecycle import reconcile_orphan_running_task
            if reconcile_orphan_running_task(instance):
                instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MigrationTaskListSerializer
        return MigrationTaskSerializer
    
    def _response_from_dashboard(self, result):
        """将 dashboard 返回的 JsonResponse 转为 DRF Response 可用的 dict 和状态码"""
        if isinstance(result, JsonResponse):
            data = json.loads(result.content.decode('utf-8'))
            return Response(data, status=result.status_code)
        if isinstance(result, dict):
            return Response(result)
        return Response(result)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        try:
            result = dashboard.start_task(request, task_id=pk)
            return self._response_from_dashboard(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        task = self.get_object()
        try:
            result = dashboard.cancel_task(request, task_id=pk)
            return self._response_from_dashboard(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        task = self.get_object()
        try:
            result = dashboard.delete_task(request, task_id=pk)
            return self._response_from_dashboard(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        task = self.get_object()
        try:
            result = dashboard.task_status(request, task_id=pk)
            return self._response_from_dashboard(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """分页返回结构化任务日志（MigrationTaskLog），cursor 为上一页最后一条 id。"""
        from .models import MigrationTaskLog

        task = self.get_object()
        try:
            page_size = min(int(request.query_params.get('page_size', 50)), 200)
        except (TypeError, ValueError):
            page_size = 50
        cursor_id = request.query_params.get('cursor')
        qs = MigrationTaskLog.objects.filter(task=task).order_by('-id')
        if cursor_id:
            try:
                qs = qs.filter(id__lt=int(cursor_id))
            except ValueError:
                pass
        rows = list(qs[: page_size + 1])
        has_more = len(rows) > page_size
        rows = rows[:page_size]
        next_cursor = str(rows[-1].id) if has_more and rows else None
        ser = MigrationTaskLogSerializer(rows, many=True)
        return Response({
            'status': 'success',
            'results': ser.data,
            'next_cursor': next_cursor,
            'task_id': task.id,
        })

    @action(detail=True, methods=['get'])
    def info(self, request, pk=None):
        task = self.get_object()
        try:
            result = dashboard.task_detailed_info(request, task_id=pk)
            return self._response_from_dashboard(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='monitor')
    def monitor(self, request):
        """实时任务监控聚合：状态汇总、运行中任务、对比快照、日志与最近操作。"""
        from .monitor import build_monitor_payload

        try:
            task_limit = int(request.query_params.get('task_limit', 40))
        except (TypeError, ValueError):
            task_limit = 40
        try:
            log_limit = int(request.query_params.get('log_limit', 60))
        except (TypeError, ValueError):
            log_limit = 60
        try:
            compare_limit = int(request.query_params.get('compare_limit', 25))
        except (TypeError, ValueError):
            compare_limit = 25
        return Response(
            build_monitor_payload(
                task_limit=task_limit,
                log_limit=log_limit,
                compare_limit=compare_limit,
            )
        )

    @action(detail=True, methods=['post'])
    def switch_database(self, request, pk=None):
        task = self.get_object()
        try:
            result = dashboard.switch_postgres_database(request, task_id=pk)
            return self._response_from_dashboard(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SchemasAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            conn_type = request.query_params.get('type', 'oracle')
            limit = request.query_params.get('limit', 1000)
            database = request.query_params.get('database')
            
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            schemas = []
            
            if conn_type == 'oracle':
                from . import views
                connection = views.get_oracle_connection(connection_id)
                cursor = connection.cursor()
                
                query = """
                SELECT USERNAME 
                FROM ALL_USERS 
                WHERE USERNAME NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 'OJVMSYS', 'OLAPSYS', 'ORDDATA', 'ORDSYS', 'REMOTE_SCHEDULER_AGENT', 'WMSYS', 'XDB')
                ORDER BY USERNAME
                """
                cursor.execute(query)
                schemas = [row[0] for row in cursor.fetchall()]
                cursor.close()
                connection.close()
            elif conn_type == 'postgres':
                from .models import PostgresConnection
                from .views import _pg_connect_kwargs
                pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
                conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, database or pg_conn.database))
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schema_name
                LIMIT %s
                """, [limit])
                
                schemas = [row[0] for row in cursor.fetchall()]
                cursor.close()
                conn.close()
            
            return Response({
                'status': 'success',
                'schemas': schemas
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DatabaseObjectsAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            schema = request.query_params.get('schema')
            object_type = request.query_params.get('object_type')
            search_term = request.query_params.get('search_term', '').strip()
            
            if not connection_id or not schema or not object_type:
                return Response({
                    'status': 'error',
                    'message': '缺少必要参数：connection_id, schema, object_type'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from . import views
            connection = views.get_oracle_connection(connection_id)
            cursor = connection.cursor()
            
            objects = []
            
            if object_type == 'view_to_sqlite':
                cursor.execute("""
                SELECT TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER = :schema 
                ORDER BY TABLE_NAME
                """, {'schema': schema})
                table_rows = cursor.fetchall()
                
                cursor.execute("""
                SELECT VIEW_NAME 
                FROM ALL_VIEWS 
                WHERE OWNER = :schema 
                ORDER BY VIEW_NAME
                """, {'schema': schema})
                view_rows = cursor.fetchall()
                
                table_objects = [{'name': row[0], 'object_type': 'TABLE'} for row in table_rows]
                view_objects = [{'name': row[0], 'object_type': 'VIEW'} for row in view_rows]
                objects = table_objects + view_objects
                
                if search_term:
                    objects = [
                        obj for obj in objects 
                        if search_term.lower() in (obj['name'] or '').lower()
                    ]
                
                objects.sort(key=lambda obj: (obj['object_type'], obj['name']))
                
                cursor.close()
                connection.close()
                
                return Response({
                    'status': 'success',
                    'objects': objects,
                    'total': len(objects),
                    'has_more': False
                })
            elif object_type.upper() == 'TABLE':
                query = """
                SELECT TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER = :schema 
                ORDER BY TABLE_NAME
                """
                cursor.execute(query, {'schema': schema})
                objects = [row[0] for row in cursor.fetchall()]
                
            elif object_type.upper() in ('VIEW', 'VIEW_TO_TABLE'):
                query = """
                SELECT VIEW_NAME 
                FROM ALL_VIEWS 
                WHERE OWNER = :schema 
                ORDER BY VIEW_NAME
                """
                cursor.execute(query, {'schema': schema})
                objects = [row[0] for row in cursor.fetchall()]
                
            elif object_type.upper() == 'MATERIALIZED_VIEW':
                query = """
                SELECT MVIEW_NAME 
                FROM ALL_MVIEWS 
                WHERE OWNER = :schema 
                ORDER BY MVIEW_NAME
                """
                cursor.execute(query, {'schema': schema})
                objects = [row[0] for row in cursor.fetchall()]
                
            elif object_type.upper() == 'ROUTINE':
                query = """
                SELECT DISTINCT OBJECT_NAME 
                FROM ALL_OBJECTS 
                WHERE OWNER = :schema 
                  AND OBJECT_TYPE IN ('PROCEDURE', 'FUNCTION') 
                ORDER BY OBJECT_NAME
                """
                cursor.execute(query, {'schema': schema})
                objects = [row[0] for row in cursor.fetchall()]

            elif object_type.upper() == 'SEQUENCE':
                query = """
                SELECT SEQUENCE_NAME FROM ALL_SEQUENCES
                WHERE SEQUENCE_OWNER = :schema ORDER BY SEQUENCE_NAME
                """
                cursor.execute(query, {'schema': schema})
                objects = [row[0] for row in cursor.fetchall()]

            elif object_type.upper() == 'TRIGGER':
                query = """
                SELECT TRIGGER_NAME FROM ALL_TRIGGERS
                WHERE OWNER = :schema AND BASE_OBJECT_TYPE IN ('TABLE', 'VIEW')
                ORDER BY TRIGGER_NAME
                """
                cursor.execute(query, {'schema': schema})
                objects = [row[0] for row in cursor.fetchall()]

            else:
                cursor.close()
                connection.close()
                return Response({
                    'status': 'error',
                    'message': f'不支持的object_type: {object_type}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if search_term:
                objects = [obj for obj in objects if search_term.lower() in obj.lower()]
            
            cursor.close()
            connection.close()
            
            return Response({
                'status': 'success',
                'objects': objects
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PostgresDatabasesAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取PostgreSQL连接信息
            from .models import PostgresConnection
            from .views import _pg_connect_kwargs
            pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
            conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, 'postgres'))
            cursor = conn.cursor()
            
            # 查询所有非系统数据库
            cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datistemplate = false AND datname != 'postgres' 
            ORDER BY datname
            """)
            
            databases = [row[0] for row in cursor.fetchall()]
            
            # 添加默认连接的数据库到列表首位
            if pg_conn.database not in databases:
                databases.insert(0, pg_conn.database)
            else:
                databases.remove(pg_conn.database)
                databases.insert(0, pg_conn.database)
            
            # 关闭游标和连接
            cursor.close()
            conn.close()
            
            return Response({
                'status': 'success',
                'databases': databases
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BrowseDirectoriesAPIView(APIView):
    def get(self, request):
        try:
            from pathlib import Path
            raw_path = request.query_params.get('path', '').strip()
            explicit_request = bool(raw_path)
            base_path = Path.home().resolve()
            
            if not raw_path:
                raw_path = str(base_path)
            
            try:
                target = Path(raw_path).expanduser().resolve()
            except Exception as resolve_err:
                return Response({'status': 'error', 'message': f'路径解析失败: {resolve_err}'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                if explicit_request and (not target.exists() or not target.is_dir()):
                    return Response({'status': 'error', 'message': '目标路径不存在或不是目录'}, status=status.HTTP_400_BAD_REQUEST)
                if not target.exists() or not target.is_dir():
                    return Response({'status': 'error', 'message': '目标路径不存在或不是目录'}, status=status.HTTP_400_BAD_REQUEST)
                
                directories = []
                for item in target.iterdir():
                    if item.is_dir():
                        directories.append({
                            'name': item.name,
                            'path': str(item),
                            'is_parent': False
                        })
                
                if target != base_path and target.parent.exists():
                    directories.insert(0, {
                        'name': '..',
                        'path': str(target.parent),
                        'is_parent': True
                    })
                
                directories.sort(key=lambda x: (not x['is_parent'], x['name'].lower()))
                
                return Response({
                    'status': 'success',
                    'current_path': str(target),
                    'directories': directories
                })
            except Exception as e:
                return Response({'status': 'error', 'message': f'读取目录失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DatabaseInfoAPIView(APIView):
    def get(self, request):
        return Response({'status': 'success', 'message': 'Database info endpoint'})


class OracleSchemasAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            from . import views
            connection = views.get_oracle_connection(connection_id)
            cursor = connection.cursor()
            
            query = """
            SELECT USERNAME 
            FROM ALL_USERS 
            WHERE USERNAME NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 'OJVMSYS', 'OLAPSYS', 'ORDDATA', 'ORDSYS', 'REMOTE_SCHEDULER_AGENT', 'WMSYS', 'XDB')
            ORDER BY USERNAME
            """
            cursor.execute(query)
            schemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            connection.close()
            
            return Response({
                'status': 'success',
                'schemas': schemas
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OracleTablesAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            schema = request.query_params.get('schema')
            
            if not connection_id or not schema:
                return Response({'status': 'error', 'message': '缺少必要参数：connection_id, schema'}, status=status.HTTP_400_BAD_REQUEST)
            
            from . import views
            connection = views.get_oracle_connection(connection_id)
            cursor = connection.cursor()
            
            query = """
            SELECT TABLE_NAME 
            FROM ALL_TABLES 
            WHERE OWNER = :schema 
            ORDER BY TABLE_NAME
            """
            cursor.execute(query, schema=schema)
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            connection.close()
            
            return Response({
                'status': 'success',
                'tables': tables
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OracleUsersAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            from . import views
            connection = views.get_oracle_connection(connection_id)
            cursor = connection.cursor()
            
            query = """
            SELECT USERNAME 
            FROM ALL_USERS 
            WHERE USERNAME NOT IN ('SYS', 'SYSTEM', 'OUTLN', 'DBSNMP', 'APPQOSSYS', 'AUDSYS', 'CTXSYS', 'DVSYS', 'GSMADMIN_INTERNAL', 'LBACSYS', 'MDSYS', 'OJVMSYS', 'OLAPSYS', 'ORDDATA', 'ORDSYS', 'REMOTE_SCHEDULER_AGENT', 'WMSYS', 'XDB')
            ORDER BY USERNAME
            """
            cursor.execute(query)
            users = [row[0] for row in cursor.fetchall()]
            cursor.close()
            connection.close()
            
            return Response({
                'status': 'success',
                'users': users
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgSchemasAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            database = request.query_params.get('database')
            limit = request.query_params.get('limit', 1000)
            
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .models import PostgresConnection
            from .views import _pg_connect_kwargs
            pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
            target_database = database or pg_conn.database
            try:
                conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, 'postgres'))
                cursor = conn.cursor()
                
                # 检查目标数据库是否存在
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [target_database])
                db_exists = cursor.fetchone()
                
                cursor.close()
                conn.close()
                
                if not db_exists:
                    # 如果目标数据库不存在，返回空列表
                    return Response({
                        'status': 'success',
                        'schemas': [],
                        'message': f'数据库 "{target_database}" 不存在'
                    })
            except Exception as check_error:
                pass
            conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, target_database))
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            ORDER BY schema_name
            LIMIT %s
            """, [limit])
            
            schemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return Response({
                'status': 'success',
                'schemas': schemas
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgTablesAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            schema = request.query_params.get('schema')
            database = request.query_params.get('database')
            
            if not connection_id or not schema:
                return Response({'status': 'error', 'message': '缺少必要参数：connection_id, schema'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .models import PostgresConnection
            from .views import _pg_connect_kwargs
            pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
            conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, database or pg_conn.database))
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """, [schema])
            
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return Response({
                'status': 'success',
                'tables': tables
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgUsersAPIView(APIView):
    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            database = request.query_params.get('database')
            
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .models import PostgresConnection
            from .views import _pg_connect_kwargs
            pg_conn = get_object_or_404(PostgresConnection, pk=connection_id)
            conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, database or pg_conn.database))
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT usename 
            FROM pg_user 
            WHERE usename NOT IN ('postgres')
            ORDER BY usename
            """)
            
            users = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            
            return Response({
                'status': 'success',
                'users': users
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MigrationSettingsAPIView(APIView):
    """迁移配置读写接口"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _default_migration_settings():
        return {
            'default_identifier_case': 'lower',
            'default_conflict_strategy': 'error',
            'enable_batch_migration': False,
            'batch_size': 100,
        }

    def get(self, request):
        try:
            # 直接返回扁平结构，与前端 v-model 字段一致
            return Response(self._default_migration_settings())
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            data = request.data or {}
            # 校验并归一化配置项
            settings = self._default_migration_settings()
            if 'default_identifier_case' in data:
                settings['default_identifier_case'] = data['default_identifier_case']
            if 'default_conflict_strategy' in data:
                settings['default_conflict_strategy'] = data['default_conflict_strategy']
            if 'enable_batch_migration' in data:
                settings['enable_batch_migration'] = bool(data['enable_batch_migration'])
            if 'batch_size' in data:
                settings['batch_size'] = max(1, int(data['batch_size']))
            return Response({'status': 'success', 'message': '保存成功', 'data': settings})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SystemSettingsAPIView(APIView):
    """系统设置读写接口"""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _default_system_settings():
        return {
            'log_level': 'INFO',
            'max_concurrent_tasks': 5,
            'task_timeout': 3600,
            'enable_auto_retry': False,
            'max_retry_count': 3,
        }

    def get(self, request):
        try:
            return Response(self._default_system_settings())
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            data = request.data or {}
            settings = self._default_system_settings()
            if 'log_level' in data:
                settings['log_level'] = data['log_level']
            if 'max_concurrent_tasks' in data:
                settings['max_concurrent_tasks'] = max(1, int(data['max_concurrent_tasks']))
            if 'task_timeout' in data:
                settings['task_timeout'] = max(1, int(data['task_timeout']))
            if 'enable_auto_retry' in data:
                settings['enable_auto_retry'] = bool(data['enable_auto_retry'])
            if 'max_retry_count' in data:
                settings['max_retry_count'] = max(0, int(data['max_retry_count']))
            return Response({'status': 'success', 'message': '保存成功', 'data': settings})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MigrationLogsAPIView(APIView):
    """迁移日志查询（限制条数与体积，避免前端卡顿）"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            from .models import MigrationTask, MigrationTaskLog

            max_lines = min(int(request.query_params.get('limit', 200)), 500)
            log_text_parts = []

            # 优先读取结构化日志表
            structured = (
                MigrationTaskLog.objects.select_related('task')
                .order_by('-created_at')[:max_lines]
            )
            if structured.exists():
                for entry in structured:
                    ts = entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else '-'
                    task_name = entry.task.name if entry.task_id else '未知任务'
                    log_text_parts.append(f"[{ts}] [{entry.level}] {task_name}: {entry.message}")
            else:
                # 回退：仅取最近任务的日志尾部，避免一次性加载超大文本
                tasks = (
                    MigrationTask.objects.order_by('-created_at')
                    .only('name', 'status', 'log', 'created_at')[:20]
                )
                for task in tasks:
                    raw_log = (task.log or '').strip()
                    if not raw_log:
                        continue
                    tail = raw_log[-3000:] if len(raw_log) > 3000 else raw_log
                    log_text_parts.append(f"=== {task.name} ({task.status}) ===\n{tail}")

            log_text = '\n'.join(log_text_parts) if log_text_parts else '暂无日志'

            return Response({
                'status': 'success',
                'logs': log_text,
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HelpDocsAPIView(APIView):
    def get(self, request):
        return Response({
            'status': 'success',
            'message': 'Help documentation available'
        })


class CreateTaskAPIView(APIView):
    def post(self, request):
        try:
            result = create_task.create_task_validated(request)
            
            # 检查返回结果的类型
            if isinstance(result, dict):
                # 检查是否是错误状态
                if result.get('status') == 'error':
                    # 提取状态码，如果有的话
                    error_code = result.get('code', 400)
                    return Response(result, status=error_code)
                else:
                    return Response(result)
            else:
                return Response({'status': 'error', 'message': 'Invalid response from create_task_validated'})
                
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgTablespacesAPIView(APIView):
    """列出 PolarDB-PG 表空间"""

    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            database = request.query_params.get('database')
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            from .target_provisioning import list_tablespaces
            names = list_tablespaces(int(connection_id), database)
            return Response({'status': 'success', 'tablespaces': names})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgCreateDatabaseAPIView(APIView):
    """创建 PolarDB-PG 数据库"""

    def post(self, request):
        try:
            from .target_provisioning import create_database
            data = request.data or {}
            connection_id = data.get('connection_id')
            name = data.get('name')
            if not connection_id or not name:
                return Response({'status': 'error', 'message': '缺少 connection_id 或 name'}, status=status.HTTP_400_BAD_REQUEST)
            result = create_database(
                int(connection_id), name,
                owner=data.get('owner'),
                encoding=data.get('encoding') or 'UTF8',
            )
            return Response({'status': 'success', **result})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgCreateTablespaceAPIView(APIView):
    """创建 PolarDB-PG 表空间"""

    def post(self, request):
        try:
            from .target_provisioning import create_tablespace
            data = request.data or {}
            connection_id = data.get('connection_id')
            name = data.get('name')
            location = data.get('location')
            if not connection_id or not name:
                return Response({'status': 'error', 'message': '缺少 connection_id 或 name'}, status=status.HTTP_400_BAD_REQUEST)
            result = create_tablespace(int(connection_id), name, location or '')
            return Response({'status': 'success', **result})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgCreateUserAPIView(APIView):
    """创建 PolarDB-PG 用户/角色"""

    def post(self, request):
        try:
            from .target_provisioning import create_role, grant_connect_on_database
            data = request.data or {}
            connection_id = data.get('connection_id')
            username = data.get('username')
            password = data.get('password')
            if not connection_id or not username:
                return Response({'status': 'error', 'message': '缺少 connection_id 或 username'}, status=status.HTTP_400_BAD_REQUEST)
            result = create_role(
                int(connection_id), username, password or '',
                createdb=bool(data.get('createdb')),
                database=data.get('database'),
            )
            if data.get('database') and result.get('status') == 'created':
                grant_connect_on_database(int(connection_id), username, data['database'])
            return Response({'status': 'success', **result})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PgCreateSchemaAPIView(APIView):
    """创建 PolarDB-PG Schema"""

    def post(self, request):
        try:
            from .target_provisioning import create_schema
            data = request.data or {}
            connection_id = data.get('connection_id')
            database = data.get('database')
            schema = data.get('schema') or data.get('name')
            if not connection_id or not database or not schema:
                return Response({'status': 'error', 'message': '缺少 connection_id、database 或 schema'}, status=status.HTTP_400_BAD_REQUEST)
            result = create_schema(int(connection_id), database, schema, owner=data.get('owner'))
            return Response({'status': 'success', **result})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TargetEnvPrepareAPIView(APIView):
    """一次性准备目标环境（库/表空间/用户/Schema）"""

    def post(self, request):
        try:
            from .target_provisioning import prepare_target_env
            data = request.data or {}
            if not data.get('connection_id'):
                return Response({'status': 'error', 'message': '缺少 connection_id'}, status=status.HTTP_400_BAD_REQUEST)
            result = prepare_target_env(data)
            code = status.HTTP_400_BAD_REQUEST if result.get('status') == 'error' else status.HTTP_200_OK
            return Response(result, status=code)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OracleDiscoveryAPIView(APIView):
    """发现 Oracle 实例下所有 Schema 及对象统计"""

    def get(self, request):
        try:
            connection_id = request.query_params.get('connection_id')
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
            from .full_database import discover_oracle_instance
            result = discover_oracle_instance(int(connection_id))
            return Response({'status': 'success', **result})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateTableMigrationAPIView(APIView):
    """表级迁移向导创建任务"""

    def post(self, request):
        try:
            result = create_task.create_table_migration_plan(request.data or {})
            if result.get('status') == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateFullDatabaseMigrationAPIView(APIView):
    """整库一键迁移创建任务"""

    def post(self, request):
        try:
            result = create_task.create_full_database_migration_plan(request.data or {})
            if result.get('status') == 'error':
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result)
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
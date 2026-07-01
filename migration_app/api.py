from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.conf import settings
from .models import OracleConnection, PostgresConnection, MigrationTask, AuditLog
from .permissions import IsAdmin, IsOperatorOrAdmin, IsViewerOrAbove
from .serializers import (
    OracleConnectionSerializer,
    PostgresConnectionSerializer,
    MigrationTaskSerializer,
    MigrationTaskListSerializer,
    MigrationTaskLogSerializer,
)
from . import dashboard
from . import create_task
from .migration_errors import format_db_error, safe_close_db_resources
import json
import logging
import traceback
import psycopg2

logger = logging.getLogger(__name__)


def _safe_error(e: Exception, prefix: str = '操作失败') -> Response:
    """统一错误响应，避免直接返回 str(e) 泄露内部异常堆栈。

    开发环境返回完整错误信息便于调试，生产环境仅返回通用提示。
    异常详情始终写入后端日志。
    """
    logger.error('%s: %s', prefix, e, exc_info=True)
    if getattr(settings, 'DEBUG', False):
        msg = f'{prefix}: {e}'
    else:
        # 生产环境只返回通用提示，不泄露内部细节
        msg = prefix
    return Response({'status': 'error', 'message': msg}, status=status.HTTP_400_BAD_REQUEST)


class OracleConnectionViewSet(viewsets.ModelViewSet):
    queryset = OracleConnection.objects.all().order_by('id')
    serializer_class = OracleConnectionSerializer
    
    def get_permissions(self):
        """根据操作类型返回不同的权限类"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # 创建/修改/删除需要操作员或管理员权限
            return [IsOperatorOrAdmin()]
        # 只读操作只需登录即可
        return [permissions.IsAuthenticated()]


class PostgresConnectionViewSet(viewsets.ModelViewSet):
    queryset = PostgresConnection.objects.all().order_by('id')
    serializer_class = PostgresConnectionSerializer
    
    def get_permissions(self):
        """根据操作类型返回不同的权限类"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # 创建/修改/删除需要操作员或管理员权限
            return [IsOperatorOrAdmin()]
        # 只读操作只需登录即可
        return [permissions.IsAuthenticated()]
    
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
    # 登录接口限流：每分钟最多 5 次尝试（防暴力破解）
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

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
            logger.error('登录异常: %s', e, exc_info=True)
            return Response({
                'status': 'error',
                'message': f'登录失败: {str(e)}' if getattr(settings, 'DEBUG', False) else '登录失败，请稍后重试'
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
    
    def get_permissions(self):
        """根据操作类型返回不同的权限类"""
        if self.action == 'delete':
            # 删除任务需要操作员或管理员权限
            return [IsOperatorOrAdmin()]
        # 其他操作只需登录即可
        return [permissions.IsAuthenticated()]

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
    def report(self, request, pk=None):
        """获取或生成结构化迁移报告。"""
        from django.http import HttpResponse

        from .migration_report import build_migration_report, persist_migration_report, report_to_json_text

        task = self.get_object()
        refresh = request.query_params.get('refresh') == '1'
        if refresh or not task.migration_report:
            report = persist_migration_report(task)
        else:
            report = task.migration_report
        if request.query_params.get('format') == 'download':
            filename = f'migration_report_task_{task.id}.json'
            resp = HttpResponse(report_to_json_text(report), content_type='application/json; charset=utf-8')
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp
        return Response({'status': 'success', 'report': report})

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
        connection = cursor = conn = None
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
            elif conn_type == 'postgres':
                from .models import PostgresConnection
                from .views import _pg_connect_kwargs
                pg_conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)
                conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn_obj, database or pg_conn_obj.database))
                cursor = conn.cursor()
                cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schema_name
                LIMIT %s
                """, [limit])
                schemas = [row[0] for row in cursor.fetchall()]
            else:
                return Response({'status': 'error', 'message': f'不支持的 type: {conn_type}'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'status': 'success', 'schemas': schemas})
        except Exception as e:
            return Response({'status': 'error', 'message': format_db_error(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, connection, conn)


class DatabaseObjectsAPIView(APIView):
    def get(self, request):
        connection = cursor = None
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
                return Response({
                    'status': 'success',
                    'objects': objects,
                    'total': len(objects),
                    'has_more': False,
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
                return Response({
                    'status': 'error',
                    'message': f'不支持的object_type: {object_type}',
                }, status=status.HTTP_400_BAD_REQUEST)

            if search_term:
                objects = [obj for obj in objects if search_term.lower() in obj.lower()]

            return Response({'status': 'success', 'objects': objects})
        except Exception as e:
            return Response({'status': 'error', 'message': format_db_error(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, connection)


class PostgresDatabasesAPIView(APIView):
    def get(self, request):
        conn = cursor = None
        try:
            connection_id = request.query_params.get('connection_id')
            if not connection_id:
                return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)

            from .models import PostgresConnection
            from .views import _pg_connect_kwargs
            pg_conn_obj = get_object_or_404(PostgresConnection, pk=connection_id)
            conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn_obj, 'postgres'))
            cursor = conn.cursor()
            cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datistemplate = false AND datname != 'postgres' 
            ORDER BY datname
            """)
            databases = [row[0] for row in cursor.fetchall()]
            if pg_conn_obj.database not in databases:
                databases.insert(0, pg_conn_obj.database)
            else:
                databases.remove(pg_conn_obj.database)
                databases.insert(0, pg_conn_obj.database)
            return Response({'status': 'success', 'databases': databases})
        except Exception as e:
            return Response({'status': 'error', 'message': format_db_error(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, conn)


class BrowseDirectoriesAPIView(APIView):
    def get(self, request):
        from pathlib import Path
        # 安全沙箱：只允许访问白名单内的根目录及其子目录
        whitelist = getattr(settings, 'BROWSE_DIRECTORIES_WHITELIST', [])
        if not whitelist:
            return Response({'status': 'error', 'message': '文件浏览功能未配置白名单，已禁用'},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            raw_path = request.query_params.get('path', '').strip()
            explicit_request = bool(raw_path)

            # 默认返回白名单第一个根目录
            if not raw_path:
                raw_path = whitelist[0]

            try:
                target = Path(raw_path).expanduser().resolve()
            except Exception as resolve_err:
                return Response({'status': 'error', 'message': f'路径解析失败: {resolve_err}'}, status=status.HTTP_400_BAD_REQUEST)

            # 关键：校验 target 是否在白名单某个根目录之下（防止目录穿越）
            allowed_roots = [Path(p).resolve() for p in whitelist]
            if not any(target == r or target.is_relative_to(r) for r in allowed_roots):
                logger.warning('目录浏览越权访问被拒绝: %s (白名单: %s)', target, whitelist)
                return Response({'status': 'error', 'message': '访问被拒绝：目标路径不在允许的目录范围内'},
                                status=status.HTTP_403_FORBIDDEN)

            try:
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

                # 仅在白名单根目录的子目录内允许返回「..」
                parent = target.parent
                if any(parent == r or parent.is_relative_to(r) for r in allowed_roots) and parent != target:
                    directories.insert(0, {
                        'name': '..',
                        'path': str(parent),
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
        connection = cursor = None
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

            return Response({
                'status': 'success',
                'schemas': schemas
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, connection)


class OracleTablesAPIView(APIView):
    def get(self, request):
        connection = cursor = None
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

            return Response({
                'status': 'success',
                'tables': tables
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, connection)


class OracleUsersAPIView(APIView):
    def get(self, request):
        connection = cursor = None
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

            return Response({
                'status': 'success',
                'users': users
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, connection)


class PgSchemasAPIView(APIView):
    def get(self, request):
        conn = cursor = None
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

            # 检查目标数据库是否存在
            check_conn = check_cursor = None
            try:
                check_conn = psycopg2.connect(**_pg_connect_kwargs(pg_conn, 'postgres'))
                check_cursor = check_conn.cursor()
                check_cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [target_database])
                db_exists = check_cursor.fetchone()

                if not db_exists:
                    # 如果目标数据库不存在，返回空列表
                    return Response({
                        'status': 'success',
                        'schemas': [],
                        'message': f'数据库 "{target_database}" 不存在'
                    })
            except Exception as check_error:
                pass
            finally:
                safe_close_db_resources(check_cursor, check_conn)

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

            return Response({
                'status': 'success',
                'schemas': schemas
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, conn)


class PgTablesAPIView(APIView):
    def get(self, request):
        conn = cursor = None
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

            return Response({
                'status': 'success',
                'tables': tables
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, conn)


class PgUsersAPIView(APIView):
    def get(self, request):
        conn = cursor = None
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

            return Response({
                'status': 'success',
                'users': users
            })
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            safe_close_db_resources(cursor, conn)


class MigrationSettingsAPIView(APIView):
    """迁移配置读写接口（持久化至 PlatformConfig）"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            from .platform_config import get_migration_settings
            return Response(get_migration_settings())
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            from .platform_config import save_migration_settings
            data = request.data or {}
            settings = save_migration_settings(data)
            return Response({'status': 'success', 'message': '保存成功', 'data': settings})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SystemSettingsAPIView(APIView):
    """系统设置读写接口（持久化至 PlatformConfig）"""
    
    def get_permissions(self):
        """GET 操作只需登录，POST 操作需要管理员权限"""
        if self.request.method == 'POST':
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        try:
            from .platform_config import get_system_settings
            return Response(get_system_settings())
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            from .platform_config import save_system_settings
            data = request.data or {}
            settings = save_system_settings(data)
            
            # 记录审计日志
            try:
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='update_system_settings',
                    target_type='settings',
                    target_id=None,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    payload=data,
                    result='success',
                )
            except Exception as audit_err:
                logger.error(f'记录审计日志失败: {audit_err}', exc_info=True)
            
            return Response({'status': 'success', 'message': '保存成功', 'data': settings})
        except Exception as e:
            # 记录失败的审计日志
            try:
                AuditLog.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    action='update_system_settings',
                    target_type='settings',
                    target_id=None,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    payload=request.data,
                    result='failed',
                )
            except Exception as audit_err:
                logger.error(f'记录审计日志失败: {audit_err}', exc_info=True)
            
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


class CeleryStatusAPIView(APIView):
    """Celery / Beat 配置状态（供前端提示定时增量依赖）"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            from .platform_config import get_celery_status
            return Response({'status': 'success', **get_celery_status()})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class HelpDocsAPIView(APIView):
    """帮助文档索引（供前端 Help 页渲染）"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sections = [
            {
                'title': '快速开始',
                'items': [
                    {'label': '产品概述与 v2 亮点', 'path': 'README.md', 'anchor': '亮点功能--v2'},
                    {'label': '环境要求与一键启动', 'path': 'README.md', 'anchor': '快速开始'},
                    {'label': '表级迁移向导', 'path': 'README.md', 'anchor': '表级迁移向导'},
                    {'label': '整库一键迁移', 'path': 'README.md', 'anchor': '整库一键迁移'},
                ],
            },
            {
                'title': '子文档',
                'items': [
                    {'label': '文档索引', 'path': 'docs/文档索引.md'},
                    {'label': '迁移进度与监控', 'path': 'docs/迁移进度与监控.md'},
                    {'label': '路由与前后端配置', 'path': 'docs/路由与前后端配置.md'},
                    {'label': '需求与版本说明', 'path': 'docs/需求与版本说明.md'},
                ],
            },
            {
                'title': '运维提示',
                'items': [
                    {'label': 'Celery Worker + Beat + Redis 三件套（定时增量必需）', 'hint': True},
                    {'label': '触发器/复杂 PL/SQL 需人工改写后在目标库执行', 'hint': True},
                    {'label': '外键约束在表数据导入完成后回放（可在系统配置关闭）', 'hint': True},
                ],
            },
        ]
        return Response({
            'status': 'success',
            'title': 'Oracle → PolarDB 迁移平台帮助',
            'version': 'v2.0',
            'sections': sections,
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
    permission_classes = [IsAdmin]

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
    permission_classes = [IsAdmin]

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
    permission_classes = [IsAdmin]

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
        connection_id = request.query_params.get('connection_id')
        if not connection_id:
            return Response({'status': 'error', 'message': '未提供连接ID'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from .full_database import discover_oracle_instance
            result = discover_oracle_instance(int(connection_id), timeout_seconds=90)
            return Response({'status': 'success', **result})
        except TimeoutError as e:
            logger.error("Oracle discovery 超时, connection_id=%s", connection_id)
            return Response(
                {'status': 'error', 'message': f'{e}。请检查：1) Oracle 主机/端口是否可达 2) 服务名是否正确 3) 网络是否畅通'},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as e:
            logger.exception("Oracle discovery 失败, connection_id=%s", connection_id)
            return Response(
                {'status': 'error', 'message': self._format_oracle_error(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def _format_oracle_error(e: Exception) -> str:
        """把 cx_Oracle 异常转为用户可读的提示。"""
        msg = str(e)
        if 'ORA-12154' in msg:
            return f'ORA-12154: 无法解析连接标识符。请检查 service_name 配置。({msg})'
        if 'ORA-12541' in msg:
            return f'ORA-12541: 监听器未运行。请检查 Oracle 主机端口和监听状态。({msg})'
        if 'ORA-01017' in msg:
            return f'ORA-01017: 用户名/密码错误。({msg})'
        if 'ORA-12514' in msg:
            return f'ORA-12514: 监听器未识别 service_name。请检查 service_name 拼写。({msg})'
        if 'DPI-1040' in msg or 'cannot locate' in msg.lower():
            return f'Oracle Client 未安装或路径未配置。请安装 Oracle Instant Client 并设置 LD_LIBRARY_PATH。({msg})'
        if 'DPI-1067' in msg or 'ORA-01013' in msg:
            return f'查询超时被中断。Oracle 数据量过大或查询过慢。({msg})'
        return msg


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
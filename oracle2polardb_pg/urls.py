"""
URL configuration for oracle2polardb_pg project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.views.generic import RedirectView
import os
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


def healthz(request):
    """存活探针：只要进程能响应即返回 200"""
    return JsonResponse({'status': 'ok'})


def readyz(request):
    """就绪探针：检查数据库连接是否正常"""
    try:
        from django.db import connections
        conn = connections['default']
        conn.ensure_connection()
        return JsonResponse({'status': 'ready', 'database': 'connected'})
    except Exception as e:
        return JsonResponse({'status': 'not_ready', 'error': str(e)}, status=503)


# Vue history 路由的前缀白名单：这些前缀下的未知路径必须保持 404，
# 否则 /api/xxx 打错会被回退视图伪装成首页，前端只能看到"200 但 JSON 解析失败"
_SPA_RESERVED_PREFIXES = ('api', 'admin', 'static', 'media', 'healthz', 'readyz')


def spa_fallback(request, path=''):
    """生产环境下的 SPA 深层链接回退：非真实前缀的 GET/HEAD 一律返回 index.html。"""
    if path.split('/')[0] in _SPA_RESERVED_PREFIXES:
        raise Http404
    if request.method not in ('GET', 'HEAD'):
        return HttpResponseNotAllowed(['GET', 'HEAD'])
    # 存在性检查放在请求期：CI 与未构建的仓库里没有 dist，
    # 若依赖 import 期的 os.path.exists 注册路由，这条分支在测试里永远进不来
    index = os.path.join(settings.VITE_BUILD_DIR, 'index.html')
    if settings.DEBUG or not os.path.isfile(index):
        raise Http404
    with open(index, 'rb') as handle:
        return HttpResponse(handle.read(), content_type='text/html; charset=utf-8')


urlpatterns = [
    path('admin/', admin.site.urls),
    # API 版本化 v1
    path('api/v1/', include('migration_app.urls')),
    # 兼容现有前端：保留 api/ 作为别名
    path('api/', include('migration_app.urls')),
    # OpenAPI/Swagger 文档端点
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # 健康检查端点（供 k8s / 负载均衡探针使用，无需认证）
    path('healthz', healthz),
    path('readyz', readyz),
]

# 开发环境配置
if settings.DEBUG:
    # 开发环境：重定向到Vue开发服务器
    urlpatterns += [
        path('', RedirectView.as_view(url='http://localhost:5173', permanent=False)),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# 生产环境配置
else:
    # /static/ 与 Vue 的 /assets/ 由 WhiteNoise 中间件按文件直出，这里只剩路由回退。
    # 原先这两行 static() 在 DEBUG=False 下恒返回空列表（django/conf/urls/static.py:23），
    # 属于死代码：删掉后由 WhiteNoise 承担，index.html 引用 /assets/ 不再 404。
    urlpatterns += [
        re_path(r'^(?P<path>.*?)/?$', spa_fallback, name='spa_fallback'),
    ]

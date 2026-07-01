"""
URL configuration for oracle2polardb_pg project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.http import JsonResponse
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
    # 生产环境：提供Vue构建后的静态文件
    if os.path.exists(settings.VITE_BUILD_DIR):
        urlpatterns += [
            path('', TemplateView.as_view(template_name='index.html'), name='frontend'),
        ]
        # 添加静态文件服务
        from django.contrib.staticfiles.views import serve
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
        urlpatterns += static('/assets/', document_root=os.path.join(settings.VITE_BUILD_DIR, 'assets'))

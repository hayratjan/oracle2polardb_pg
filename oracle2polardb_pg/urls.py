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
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('migration_app.urls')),
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

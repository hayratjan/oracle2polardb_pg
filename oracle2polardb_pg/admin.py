from django.contrib import admin
from django.utils.safestring import mark_safe
import markdown
import os
from django.conf import settings
from migration_app.models import OracleConnection, PostgresConnection, MigrationTask
from migration_app.admin import OracleConnectionAdmin, PostgresConnectionAdmin, MigrationTaskAdmin

class CustomAdminSite(admin.AdminSite):
    """
    自定义admin站点
    """
    site_title = 'Oracle到PolarDB迁移工具'
    site_header = 'Oracle到PolarDB迁移工具'
    index_title = '管理中心'
    
    def index(self, request, extra_context=None):
        """
        自定义首页视图
        """
        # 读取README.md
        readme_path = getattr(settings, 'SIMPLEUI_HOME_INFO_PATH', os.path.join(settings.BASE_DIR, 'README.md'))
        readme_content = ""
        
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                # 将Markdown转换为HTML
                readme_content = markdown.markdown(
                    readme_content, 
                    extensions=[
                        'markdown.extensions.extra',
                        'markdown.extensions.codehilite',
                        'markdown.extensions.toc',
                    ]
                )
        
        context = {
            'readme_content': mark_safe(readme_content)
        }
        
        if extra_context:
            context.update(extra_context)
        
        return super().index(request, context)

# 替换默认的admin站点
admin_site = CustomAdminSite(name='admin')

# 注册模型到自定义admin站点
admin_site.register(OracleConnection, OracleConnectionAdmin)
admin_site.register(PostgresConnection, PostgresConnectionAdmin)
admin_site.register(MigrationTask, MigrationTaskAdmin)

# 导入并注册Django内置的模型
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin) 
from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    仅管理员可访问的权限类。
    用于高危操作：系统设置、创建数据库/用户等。
    """
    message = '需要管理员权限'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Django 的 is_staff 字段代表管理员
        return request.user.is_staff


class IsOperatorOrAdmin(permissions.BasePermission):
    """
    操作员或管理员可访问的权限类。
    用于中等风险操作：创建/修改连接、删除任务等。
    """
    message = '需要操作员或管理员权限'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 管理员直接放行
        if request.user.is_staff:
            return True
        # 检查用户角色配置
        profile = getattr(request.user, 'profile', None)
        if not profile:
            # 无 profile 时，用 is_staff 兜底（已上面检查，此时为 False）
            return False
        # 角色为 admin 或 operator 时放行
        return profile.role in ['admin', 'operator']


class IsViewerOrAbove(permissions.BasePermission):
    """
    所有角色都可访问的权限类（viewer 及以上）。
    用于只读操作：查看任务列表、连接列表等。
    """
    message = '需要登录'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 所有已登录用户都有 viewer 权限
        return True


def get_user_role(request):
    """获取用户角色，返回 'admin'、'operator'、'viewer' 或 'unknown'"""
    if not request.user or not request.user.is_authenticated:
        return 'unknown'
    if request.user.is_staff:
        return 'admin'
    profile = getattr(request.user, 'profile', None)
    if not profile:
        return 'viewer'  # 无 profile 默认为 viewer
    return profile.role
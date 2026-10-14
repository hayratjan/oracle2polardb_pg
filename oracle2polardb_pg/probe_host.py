"""容器探针的 Host 豁免。

生产里 ALLOWED_HOSTS 只配真实域名，而镜像 HEALTHCHECK / compose healthcheck 是从容器内部
用 localhost 打 /healthz 的；Django 的 Host 校验会先把这种请求拒成 400，于是应用明明健康，
容器却永远 unhealthy。

这里只把两个探针路径的 Host 改写为 ALLOWED_HOSTS 真正接受的主机名，其余路径一律保持严格校验。
这两个端点返回固定 JSON：不带 Cookie、不生成绝对 URL、不该进共享缓存，
所以豁免它们不扩大 Host 头的攻击面。

前置假设：本项目未启用 USE_X_FORWARDED_HOST，因此 get_host() 读的就是 HTTP_HOST。
"""
from django.conf import settings
from django.http.request import validate_host

PROBE_PATHS = frozenset({'/healthz', '/readyz'})


def _stand_in_host(allowed_hosts):
    """挑一个 Django 自己认可的主机名当改写目标。

    ALLOWED_HOSTS 只认三种写法：字面域名、以 '.' 开头（.example.com 匹配 example.com 及其
    子域）、单独的 '*'；'*.example.com' 这种写法 validate_host 一概拒绝，所以候选要按前两种
    生成，并且仍用 Django 的 validate_host 复核，而不是猜它的支持范围。
    """
    candidates = []
    for pattern in allowed_hosts:
        if pattern.startswith('*.'):
            candidates.extend(('probe.' + pattern[2:], pattern[2:]))
        elif pattern.startswith('.'):
            candidates.extend(('probe.' + pattern[1:], pattern[1:]))
        elif pattern == '*' or pattern.endswith('*'):
            continue  # '*' 由调用方提前返回；'mg.*' 这类 Django 本身不接受
        else:
            candidates.append(pattern)
    for host in candidates:
        if validate_host(host, allowed_hosts):
            return host
    return None


class ProbeHostExemptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed = list(settings.ALLOWED_HOSTS)
        # '*' 本来就不拒绝任何 Host，无需改写；DEBUG 下 ALLOWED_HOSTS 也是 ['*']
        if allowed and '*' not in allowed and request.META.get('PATH_INFO') in PROBE_PATHS:
            host = request.META.get('HTTP_HOST', '')
            # 与 get_host() 一致：Host 头可能带端口，校验的是去掉端口的主机名
            if not validate_host(host.rpartition(':')[0], allowed):
                target = _stand_in_host(allowed)
                if target:
                    request.META['HTTP_HOST'] = target
        return self.get_response(request)

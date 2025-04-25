from django import template
from django.conf import settings

register = template.Library()

@register.filter(is_safe=False)
def length_is(value, arg):
    """返回值的长度是否等于参数。"""
    try:
        return len(value) == int(arg)
    except (ValueError, TypeError):
        return False

@register.filter
def get_config(name):
    """
    获取settings中的配置项
    用法: {{ 'SIMPLEUI_LOGO'|get_config }}
    """
    value = getattr(settings, name, '')
    return value 
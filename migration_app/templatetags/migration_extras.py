from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """
    将字符串按指定的分隔符拆分为列表
    用法: {{ value|split:"," }}
    """
    return value.split(arg)

@register.filter
def get_item(value, key):
    """安全地获取字典中的值"""
    if isinstance(value, dict):
        return value.get(key)
    return None

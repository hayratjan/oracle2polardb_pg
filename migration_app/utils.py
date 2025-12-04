"""
工具函数模块：包含在应用程序中使用的通用功能函数
"""

def format_string(value, max_length=50):
    """
    格式化字符串，如果超过最大长度则截断并添加省略号
    
    Args:
        value: 需要格式化的字符串
        max_length: 最大长度，默认为50
        
    Returns:
        格式化后的字符串
    """
    if not value:
        return ""
    
    value = str(value)
    if len(value) <= max_length:
        return value
    
    return value[:max_length-3] + "..."


def get_file_extension(filename):
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        文件扩展名（小写）
    """
    if not filename:
        return ""
    
    parts = filename.split(".")
    if len(parts) > 1:
        return parts[-1].lower()
    
    return "" 
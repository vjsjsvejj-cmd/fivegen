
import os
import secrets
from datetime import datetime


def generate_short_id(length=6):
    """生成随机短 ID"""
    return secrets.token_urlsafe(length)[:length]


def get_category_from_mime(mime_type):
    """从 MIME 类型获取分类"""
    if mime_type.startswith('image/'):
        return 'image'
    elif mime_type.startswith('video/'):
        return 'video'
    elif mime_type.startswith('audio/'):
        return 'audio'
    return 'other'


def get_display_name(category, index, original_name):
    """
    获取显示用的文件名
    格式: {类别}{序号}.{扩展名}
    
    例如: 图片1.jpg, 视频1.mp4
    """
    ext = os.path.splitext(original_name)[1]
    if category == 'image':
        return f"图片{index}{ext}"
    elif category == 'video':
        return f"视频{index}{ext}"
    elif category == 'audio':
        return f"音频{index}{ext}"
    return f"文件{index}{ext}"


def get_short_code(category, index):
    """
    获取 @功能用的短代码
    格式: {类别}{序号}
    
    例如: 图片1, 视频1
    """
    if category == 'image':
        return f"图片{index}"
    elif category == 'video':
        return f"视频{index}"
    elif category == 'audio':
        return f"音频{index}"
    return f"文件{index}"


def format_upload_filename(original_name, index=1):
    """
    格式化上传文件名（存储用）
    格式: {序号}_{日期时间}.{扩展名}
    日期格式: MMDDHHmm
    例如: 1_04290347.jpg
    """
    ext = os.path.splitext(original_name)[1]
    timestamp = datetime.now().strftime('%m%d%H%M')
    return f"{index}_{timestamp}{ext}"


def format_result_filename(file_type, index=1):
    """
    格式化结果文件名（存储用）
    格式: {类型}_{序号}_{日期时间}.{扩展名}
    类型: img/vid
    日期格式: MMDDHHmm
    例如: img_1_04290347.jpg, vid_1_04290347.mp4
    """
    timestamp = datetime.now().strftime('%m%d%H%M')
    if file_type == 'image':
        return f"img_{index}_{timestamp}.jpg"
    elif file_type == 'video':
        return f"vid_{index}_{timestamp}.mp4"
    return f"file_{index}_{timestamp}.bin"


def get_result_display_name(file_type, index):
    """
    获取结果文件的显示名称
    例如: 图生1.jpg, 视频1.mp4
    """
    if file_type == 'image':
        return f"图生{index}.jpg"
    elif file_type == 'video':
        return f"视频{index}.mp4"
    return f"生成{index}"


def parse_file_info(filename):
    """
    从文件名解析信息
    返回: {index, timestamp, extension}
    """
    base = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    parts = base.split('_')
    
    result = {
        'index': None,
        'timestamp': None,
        'extension': ext
    }
    
    if len(parts) >= 2:
        try:
            result['index'] = int(parts[0])
            result['timestamp'] = parts[1]
        except (ValueError, IndexError):
            pass
    
    return result


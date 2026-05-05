# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import requests
import uuid
import threading
import tempfile
from datetime import datetime
import logging
from tos_service import get_tos_service
from utils.file_naming import format_result_filename, get_result_display_name
from config import Config

logger = logging.getLogger(__name__)

_history_lock = threading.Lock()
_chat_lock = threading.Lock()
_templates_lock = threading.Lock()

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LocalStorage')
HISTORY_FILE = os.path.join(STORAGE_DIR, 'history.json')
CHAT_FILE = os.path.join(STORAGE_DIR, 'chat.json')
TEMPLATES_FILE = os.path.join(STORAGE_DIR, 'templates.json')
MEDIA_DIR = os.path.join(STORAGE_DIR, 'media')
IMAGES_DIR = os.path.join(MEDIA_DIR, 'images')
VIDEOS_DIR = os.path.join(MEDIA_DIR, 'videos')


def ensure_storage_dir():
    """确保所有存储目录存在"""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)


def load_history():
    ensure_storage_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _atomic_write_json(filepath, data):
    """原子写入 JSON 文件，防止写入中途崩溃导致文件损坏"""
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def save_history(history):
    ensure_storage_dir()
    _atomic_write_json(HISTORY_FILE, history)


MAX_HISTORY_ITEMS = 500
MAX_CHAT_ITEMS = 1000

def add_to_history(item):
    with _history_lock:
        history = load_history()
        item['id'] = len(history) + 1
        if 'created_at' not in item:
            item['created_at'] = datetime.now().isoformat()
        history.append(item)
        if len(history) > MAX_HISTORY_ITEMS:
            history = history[-MAX_HISTORY_ITEMS:]
        save_history(history)
    return item


def get_history_by_room(room_id):
    history = load_history()
    room_history = [item for item in history if item.get('room_id') == room_id]
    room_history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return room_history


def load_chat():
    ensure_storage_dir()
    if not os.path.exists(CHAT_FILE):
        return []
    try:
        with open(CHAT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_chat(chat):
    ensure_storage_dir()
    _atomic_write_json(CHAT_FILE, chat)


def add_chat_message(message):
    with _chat_lock:
        chat = load_chat()
        message['id'] = len(chat) + 1
        message['created_at'] = datetime.now().isoformat()
        chat.append(message)
        if len(chat) > MAX_CHAT_ITEMS:
            chat = chat[-MAX_CHAT_ITEMS:]
        save_chat(chat)
    return message


def get_chat_by_room(room_id):
    chat = load_chat()
    room_chat = [msg for msg in chat if msg.get('room_id') == room_id]
    room_chat.sort(key=lambda x: x.get('created_at', ''))
    return room_chat


def get_default_templates():
    """获取默认模版列表
    
    ⚠️ 同步说明：此列表需与前端 useTemplates.js 中的 defaultTemplates 保持一致。
    修改此处时，务必同步修改前端 src/composables/useTemplates.js 中的对应定义。
    """
    return [
        {"id": "template_1", "name": "Slogan", "content": "「文字内容」+「出现时机」+「出现位置」+「出现方式」，「文字特征（颜色、风格）」", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_2", "name": "字幕", "content": "画面底部出现字幕，字幕内容为\"……\"，字幕需与音频节奏完全同步。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_3", "name": "气泡台词", "content": "「角色」说：\"……\"，角色话说时周围出现气泡，气泡里写着台词。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_4", "name": "主体多视角图参考", "content": "参考/提取/结合+「图片 n」中的「主体」，生成「画面描述」，保持「主体」特征一致。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_5", "name": "多图参考", "content": "参考/提取/结合/按照/生成+「图片n」中的「被参考元素描述」，生成「画面描述」，保持「被参考元素」特征一致。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_6", "name": "视频参考", "content": "参考「视频n」的「动作描述」，生成「画面描述」，保持动作细节一致。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_7", "name": "运镜参考", "content": "参考「视频n」的「运镜描述」，生成「画面描述」，保持运镜一致。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_8", "name": "特效参考", "content": "参考「视频n」的「特效描述」，生成「画面描述」，保持特效一致。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_9", "name": "增加元素", "content": "在「视频n」的「时间位置」+「空间位置」，增加「理想元素描述」。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_10", "name": "删除元素", "content": "删除「视频n」中的「被删除元素」，视频其他内容保持不变。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_11", "name": "修改元素", "content": "将「视频n」中的「被更换元素描述」，替换为「理想元素描述」。", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_12", "name": "视频延长", "content": "向前/向后延长「视频n」+「需延长的视频描述」\n生成「视频n」之前/之后的内容+「需延长的视频描述」", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
        {"id": "template_13", "name": "轨道补齐", "content": "「视频1」+「过渡画面描述」+接「视频2」+「过渡画面描述」+接「视频3」", "fullWidth": False, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()},
    ]


def load_templates():
    """加载模版列表"""
    ensure_storage_dir()
    if not os.path.exists(TEMPLATES_FILE):
        default_templates = get_default_templates()
        save_templates(default_templates)
        return default_templates
    try:
        with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        if not templates:
            default_templates = get_default_templates()
            save_templates(default_templates)
            return default_templates
        return templates
    except Exception:
        default_templates = get_default_templates()
        save_templates(default_templates)
        return default_templates


def save_templates(templates):
    """保存模版列表"""
    ensure_storage_dir()
    _atomic_write_json(TEMPLATES_FILE, templates)


def add_template(template_data):
    with _templates_lock:
        templates = load_templates()
        template_id = f"template_{uuid.uuid4().hex[:8]}"
        new_template = {
            "id": template_id,
            "name": template_data.get("name", ""),
            "content": template_data.get("content", ""),
            "fullWidth": template_data.get("fullWidth", False),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        templates.append(new_template)
        save_templates(templates)
    return new_template


def update_template(template_id, template_data):
    with _templates_lock:
        templates = load_templates()
        index = next((i for i, t in enumerate(templates) if t["id"] == template_id), None)
        if index is not None:
            templates[index]["name"] = template_data.get("name", templates[index]["name"])
            templates[index]["content"] = template_data.get("content", templates[index]["content"])
            templates[index]["fullWidth"] = template_data.get("fullWidth", templates[index]["fullWidth"])
            templates[index]["updated_at"] = datetime.now().isoformat()
            save_templates(templates)
            return templates[index]
    return None


def delete_template(template_id):
    with _templates_lock:
        templates = load_templates()
        index = next((i for i, t in enumerate(templates) if t["id"] == template_id), None)
        if index is not None:
            deleted = templates.pop(index)
            save_templates(templates)
            return deleted
    return None


def get_next_file_index(media_type):
    """
    获取下一个可用的文件序号
    
    扫描当前目录的文件，找到最大的序号 + 1
    """
    ensure_storage_dir()
    save_dir = IMAGES_DIR if media_type == 'image' else VIDEOS_DIR
    
    max_index = 0
    
    if os.path.exists(save_dir):
        for filename in os.listdir(save_dir):
            # 解析文件名格式: img_1_04290347.jpg, vid_1_04290347.mp4
            if filename.startswith('img_') or filename.startswith('vid_'):
                try:
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        index = int(parts[1])
                        if index > max_index:
                            max_index = index
                except (ValueError, IndexError):
                    continue
    
    return max_index + 1


def download_and_save_media(url, media_type='image', index=None, upload_to_tos=True):
    """
    从 URL 下载媒体文件并保存到本地，可选上传到 TOS
    
    Args:
        url: 媒体文件的 URL
        media_type: 'image' 或 'video'
        index: 文件序号（1-based），如果不指定则自动获取下一个
        upload_to_tos: 是否上传到 TOS，图片默认上传，视频默认不上传
    
    Returns:
        包含 local_path, tos_url, filename, display_name 的字典，失败返回 None
    """
    ensure_storage_dir()
    
    try:
        # 确定文件扩展名和目录
        if media_type == 'image':
            ext = '.jpg'
            save_dir = IMAGES_DIR
        elif media_type == 'video':
            ext = '.mp4'
            save_dir = VIDEOS_DIR
        else:
            ext = '.bin'
            save_dir = MEDIA_DIR
        
        # 获取或生成序号
        if index is None:
            index = get_next_file_index(media_type)
        
        # 使用规范的命名格式
        filename = format_result_filename(media_type, index)
        display_name = get_result_display_name(media_type, index)
        filepath = os.path.join(save_dir, filename)
        
        # 🟡 修改：使用 Config 中的配置，区分图片和视频的超时时间
        timeout = Config.IMAGE_DOWNLOAD_TIMEOUT if media_type == 'image' else Config.VIDEO_DOWNLOAD_TIMEOUT
        logger.debug(f"📥 正在下载 {media_type}，超时时间: {timeout} 秒")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info("媒体文件已保存到本地: %s", filepath)
        
        # 保存到 TOS（可选）
        tos_url = url  # 默认使用原始 URL
        if upload_to_tos:
            try:
                tos_service = get_tos_service()
                if tos_service:
                    tos_url = tos_service.upload_file(filepath, filename)
                    logger.info("媒体文件已上传到 TOS: %s", tos_url)
            except Exception as e:
                logger.warning("上传到 TOS 失败: %s", e)
                tos_url = url  # 如果 TOS 上传失败，使用原始 URL
        
        # 返回相对路径（相对于项目根目录）
        rel_path = os.path.relpath(filepath, os.path.dirname(os.path.dirname(__file__)))
        
        return {
            "local_path": rel_path,
            "tos_url": tos_url,
            "filename": filename,
            "display_name": display_name
        }
    
    except Exception as e:
        logger.error("下载媒体文件失败: %s", e)
        return None


def download_media_local_only(url, media_type='image', index=None):
    """
    从 URL 下载媒体文件仅保存到本地，不上传 TOS
    
    Args:
        url: 媒体文件的 URL
        media_type: 'image' 或 'video'
        index: 文件序号（1-based），如果不指定则自动获取下一个
    
    Returns:
        包含 local_path, filename, display_name 的字典，失败返回 None
    """
    ensure_storage_dir()
    
    try:
        # 确定文件扩展名和目录
        if media_type == 'image':
            ext = '.jpg'
            save_dir = IMAGES_DIR
        elif media_type == 'video':
            ext = '.mp4'
            save_dir = VIDEOS_DIR
        else:
            ext = '.bin'
            save_dir = MEDIA_DIR
        
        # 获取或生成序号
        if index is None:
            index = get_next_file_index(media_type)
        
        # 使用规范的命名格式
        filename = format_result_filename(media_type, index)
        display_name = get_result_display_name(media_type, index)
        filepath = os.path.join(save_dir, filename)
        
        # 下载文件
        timeout = Config.IMAGE_DOWNLOAD_TIMEOUT if media_type == 'image' else Config.VIDEO_DOWNLOAD_TIMEOUT
        logger.debug(f"📥 正在下载 {media_type}（仅本地），超时时间: {timeout} 秒")
        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info("媒体文件已保存到本地: %s", filepath)
        
        # 返回相对路径（相对于项目根目录）
        rel_path = os.path.relpath(filepath, os.path.dirname(os.path.dirname(__file__)))
        
        return {
            "local_path": rel_path,
            "tos_url": url,  # tos_url 直接使用原始公网 URL
            "filename": filename,
            "display_name": display_name
        }
    
    except Exception as e:
        logger.error("下载媒体文件失败: %s", e)
        return None


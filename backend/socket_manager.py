# -*- coding: utf-8 -*-

import uuid
import asyncio
import random
import os
import time
import json
from typing import Dict, Set, Any
import logging
from storage import add_to_history, get_history_by_room, download_and_save_media, download_media_local_only, add_chat_message, get_chat_by_room, load_templates, add_template, update_template, delete_template
from image_api_service import ImageAPIService

logger = logging.getLogger(__name__)

# 模型配置
IMAGE_MODELS = {
    "gpt-image-2": {
        "name": "GPT Image 2",
        "resolutions": ["1K"],
        "default_resolution": "1K"
    },
    "gpt-image-2-vip": {
        "name": "GPT Image 2 VIP",
        "resolutions": ["1K", "2K", "4K"],
        "default_resolution": "1K"
    },
    "nano-banana-2": {
        "name": "Nano Banana 2",
        "resolutions": ["1K", "2K", "4K"],
        "default_resolution": "1K"
    },
    "nano-banana-2-cl": {
        "name": "Nano Banana 2 CL",
        "resolutions": ["1K", "2K"],
        "default_resolution": "1K"
    },
    "nano-banana-2-4k-cl": {
        "name": "Nano Banana 2 4K CL",
        "resolutions": ["4K"],
        "default_resolution": "4K"
    },
    "nano-banana-pro": {
        "name": "Nano Banana Pro",
        "resolutions": ["1K", "2K", "4K"],
        "default_resolution": "1K"
    },
    "nano-banana-pro-cl": {
        "name": "Nano Banana Pro CL",
        "resolutions": ["1K", "2K", "4K"],
        "default_resolution": "1K"
    },
    "nano-banana-pro-4k-vip": {
        "name": "Nano Banana Pro 4K VIP",
        "resolutions": ["4K"],
        "default_resolution": "4K"
    },
    "seedream-5-0-lite": {
        "name": "Seedream 5.0 Lite",
        "resolutions": ["2K", "3K"],
        "default_resolution": "2K"
    }
}

VIDEO_MODELS = {
    "seedance-2-0": {
        "name": "Seedance 2.0",
        "resolutions": ["480p", "720p", "1080p"],
        "durations": ["4s", "5s", "6s", "7s", "8s", "9s", "10s", "11s", "12s", "13s", "14s", "15s"]
    }
}

ASPECT_RATIOS = ["auto", "16:9", "9:16", "1:1", "3:4", "4:3"]

# 占位图片
PLACEHOLDER_IMAGES = [
    "https://picsum.photos/seed/{seed}/800/450",
    "https://picsum.photos/seed/{seed}/450/800",
    "https://picsum.photos/seed/{seed}/600/600",
    "https://picsum.photos/seed/{seed}/600/800",
    "https://picsum.photos/seed/{seed}/800/600"
]

# 生成模拟视频占位图（使用图片代替视频防止失效）
PLACEHOLDER_VIDEO_THUMB = "https://picsum.photos/seed/video/800/450"


class SocketManager:
    def __init__(self, sio):
        self.sio = sio
        self.connected_users: Dict[str, str] = {}
        self.room_users: Dict[str, Set[str]] = {}
        self.image_service = ImageAPIService()

    def register_events(self):
        self.sio.on("connect", self.handle_connect)
        self.sio.on("disconnect", self.handle_disconnect)
        self.sio.on("join_room", self.handle_join_room)
        self.sio.on("leave_room", self.handle_leave_room)
        self.sio.on("ping", self.handle_ping)
        self.sio.on("test_message", self.handle_test_message)
        self.sio.on("generate_image", self.handle_generate_image)
        self.sio.on("generate_video", self.handle_generate_video)
        self.sio.on("cancel_task", self.handle_cancel_task)
        self.sio.on("get_history", self.handle_get_history)
        self.sio.on("send_chat_message", self.handle_send_chat_message)
        self.sio.on("get_chat_history", self.handle_get_chat_history)
        self.sio.on("get_templates", self.handle_get_templates)
        self.sio.on("add_template", self.handle_add_template)
        self.sio.on("update_template", self.handle_update_template)
        self.sio.on("delete_template", self.handle_delete_template)

    async def handle_connect(self, sid, environ, auth=None):
        user_id = str(uuid.uuid4())
        self.connected_users[sid] = user_id
        logger.info(f"User connected: sid={sid}, user_id={user_id}")
        await self.sio.emit("connected", {"user_id": user_id}, room=sid)

    async def handle_disconnect(self, sid):
        user_id = self.connected_users.pop(sid, None)
        if user_id:
            for room_id, users in list(self.room_users.items()):
                if sid in users:
                    users.remove(sid)
                    await self.sio.emit(
                        "user_left",
                        {"user_id": user_id, "sid": sid, "room_id": room_id},
                        room=room_id
                    )
                    # 发送更新后的房间成员列表
                    if users:
                        room_members = [
                            self.connected_users.get(member_sid) for member_sid in users]
                        await self.sio.emit(
                            "room_members",
                            {"room_id": room_id, "members": room_members},
                            room=room_id
                        )
                    else:
                        self.room_users.pop(room_id, None)
        logger.info(f"User disconnected: sid={sid}, user_id={user_id}")

    async def handle_join_room(self, sid, data):
        room_id = data.get("room_id")
        if not room_id:
            return

        await self.sio.enter_room(sid, room_id)
        
        if room_id not in self.room_users:
            self.room_users[room_id] = set()
        self.room_users[room_id].add(sid)
        
        user_id = self.connected_users.get(sid)
        logger.info(f"User {user_id} joined room {room_id}")
        
        await self.sio.emit(
            "user_joined",
            {"user_id": user_id, "sid": sid, "room_id": room_id},
            room=room_id
        )
        
        room_members = [
            self.connected_users.get(member_sid) for member_sid in self.room_users[room_id]]
        await self.sio.emit(
            "room_members",
            {"room_id": room_id, "members": room_members},
            room=room_id
        )
        
        # 发送该房间的历史记录给刚加入的用户
        room_history = await asyncio.to_thread(get_history_by_room, room_id)
        await self.sio.emit(
            "history_data",
            {"history": room_history},
            room=sid
        )

    async def handle_leave_room(self, sid, data):
        room_id = data.get("room_id")
        if not room_id or room_id not in self.room_users:
            return

        await self.sio.leave_room(sid, room_id)
        self.room_users[room_id].discard(sid)
        
        user_id = self.connected_users.get(sid)
        logger.info(f"User {user_id} left room {room_id}")
        
        await self.sio.emit(
            "user_left",
            {"user_id": user_id, "sid": sid, "room_id": room_id},
            room=room_id
        )
        
        if room_id in self.room_users:
            room_members = [
                self.connected_users.get(member_sid) for member_sid in self.room_users[room_id]]
            await self.sio.emit(
                "room_members",
                {"room_id": room_id, "members": room_members},
                room=room_id
            )
        
        if not self.room_users[room_id]:
            self.room_users.pop(room_id, None)

    async def handle_ping(self, sid, data):
        timestamp = data.get("timestamp")
        await self.sio.emit(
            "pong",
            {"timestamp": timestamp, "server_timestamp": int(uuid.uuid4().time_low)},
            room=sid
        )

    async def handle_test_message(self, sid, data):
        room_id = data.get("room_id")
        message = data.get("message", "")
        user_id = self.connected_users.get(sid)
        
        if room_id:
            await self.sio.emit(
                "test_message",
                {"user_id": user_id, "message": message, "room_id": room_id},
                room=room_id
            )
        else:
            await self.sio.emit(
                "test_message",
                {"user_id": user_id, "message": message},
                room=sid
            )

    async def handle_get_history(self, sid, data):
        room_id = data.get("room_id")
        if not room_id:
            return
            
        history = await asyncio.to_thread(get_history_by_room, room_id)
        await self.sio.emit("history_data", {"history": history}, room=sid)

    async def handle_generate_image(self, sid, data):
        room_id = data.get("room_id")
        user_id = self.connected_users.get(sid)
        if not room_id:
            return

        task_id = data.get("task_id") or str(uuid.uuid4())
        model = data.get("model", "gpt-image-2")
        start_time = time.time()

        logger.info(f"🎨 图片生成请求 - 任务ID: {task_id}, 用户: {user_id}, 模型: {model}")

        async def progress_callback(task_id: str, progress: int):
            await self.sio.emit(
                "generation_progress",
                {
                    "task_id": task_id,
                    "progress": progress,
                    "type": "image",
                    "user_id": user_id
                },
                room=room_id
            )

        try:
            # 发送初始进度
            await progress_callback(task_id, 0)

            # 获取模型配置和默认清晰度
            model_config = IMAGE_MODELS.get(model, {})
            default_resolution = model_config.get("default_resolution", "")
            
            # 使用用户指定的清晰度，如果没有则使用默认值
            resolution = data.get("resolution") or default_resolution

            # 准备API参数
            api_params = {
                "task_id": task_id,
                "prompt": data.get("prompt"),
                "aspect_ratio": data.get("aspect_ratio"),
                "resolution": resolution,
                "reference_images": data.get("reference_images", []),
                "mode": data.get("mode", "text-to-image")
            }

            # 调用真实API生成图片
            result_data = await self.image_service.generate_image(model, api_params, progress_callback)
            remote_image_url = result_data.get("url")

            # 发送100%进度
            await progress_callback(task_id, 100)

            # 混合方案：同时保存远程URL和下载到本地
            final_url = remote_image_url
            tos_url = remote_image_url
            display_name = None
            try:
                media_data = await asyncio.to_thread(download_and_save_media, remote_image_url, 'image')
                if media_data:
                    local_path = media_data.get("local_path")
                    tos_url = media_data.get("tos_url", remote_image_url)
                    display_name = media_data.get("display_name")
                    if local_path:
                        filename = os.path.basename(local_path)
                        final_url = f"/local-media/images/{filename}"
                        logger.info(f"图片已备份到本地: {final_url}")
                        logger.info(f"图片已备份到 TOS: {tos_url}")
                        if display_name:
                            logger.info(f"图片显示名称: {display_name}")
            except Exception as e:
                logger.warning(f"下载本地备份失败，将使用远程URL: {e}")

            duration = round(time.time() - start_time, 2)

            result = {
                "task_id": task_id,
                "type": "image",
                "user_id": user_id,
                "room_id": room_id,
                "url": final_url,
                "remote_url": tos_url,
                "displayName": display_name,
                "duration": duration,
                "cost": round(random.uniform(1, 5), 2),
                "created_at": int(time.time()),
                "params": {
                    "model": model,
                    "aspect_ratio": data.get("aspect_ratio"),
                    "resolution": resolution,
                    "prompt": data.get("prompt"),
                    "displayPrompt": data.get("displayPrompt"),
                    "reference_images": data.get("reference_images", []),
                    "mode": data.get("mode", "text-to-image")
                }
            }

            await asyncio.to_thread(add_to_history, result)

            logger.info(f"✅ 图片生成成功 - 任务ID: {task_id}, 耗时: {duration}秒")

            await self.sio.emit(
                "image_completed",
                result,
                room=room_id
            )

        except Exception as e:
            logger.error(f"❌ 图片生成失败 - 任务ID: {task_id}, 错误: {str(e)}")
            
            await self.sio.emit(
                "generation_progress",
                {
                    "task_id": task_id,
                    "progress": 0,
                    "type": "image",
                    "user_id": user_id,
                    "error": str(e)
                },
                room=room_id
            )
            
            logger.info(f"🔄 启动回退机制 - 任务ID: {task_id}")
            await self._fallback_generate_image(sid, data, task_id, user_id, room_id)

    async def _fallback_generate_image(self, sid, data, task_id, user_id, room_id):
        """API 失败时通知前端生成失败"""
        logger.warning(f"⚠️ 图片生成失败（API不可用）- 任务ID: {task_id}")

        model = data.get("model")
        model_config = IMAGE_MODELS.get(model, {})
        default_resolution = model_config.get("default_resolution", "")
        resolution = data.get("resolution") or default_resolution

        result = {
            "task_id": task_id,
            "type": "image",
            "user_id": user_id,
            "room_id": room_id,
            "url": None,
            "remote_url": None,
            "duration": 0,
            "cost": 0,
            "created_at": int(time.time()),
            "is_fallback": True,
            "failed": True,
            "error": "图片生成失败：API服务不可用",
            "params": {
                "model": model,
                "aspect_ratio": data.get("aspect_ratio"),
                "resolution": resolution,
                "prompt": data.get("prompt"),
                "displayPrompt": data.get("displayPrompt"),
                "reference_images": data.get("reference_images", []),
                "mode": data.get("mode", "text-to-image")
            }
        }

        logger.info(f"❌ 图片生成失败通知已发送 - 任务ID: {task_id}")

        await self.sio.emit(
            "image_completed",
            result,
            room=room_id
        )

    async def handle_generate_video(self, sid, data):
        room_id = data.get("room_id")
        user_id = self.connected_users.get(sid)
        if not room_id:
            return

        task_id = data.get("task_id") or str(uuid.uuid4())
        start_time = time.time()
        logger.info(f"🎬 视频生成请求 - 任务ID: {task_id}, 用户: {user_id}")

        async def progress_callback(task_id: str, progress: int):
            await self.sio.emit(
                "generation_progress",
                {
                    "task_id": task_id,
                    "progress": progress,
                    "type": "video",
                    "user_id": user_id
                },
                room=room_id
            )

        try:
            # 发送初始进度
            await progress_callback(task_id, 0)

            # 准备参数
            prompt = data.get("prompt", "")
            mode = data.get("mode", "text-to-video")
            resolution = data.get("resolution", "720p")
            ratio = data.get("aspect_ratio", "16:9")
            duration_str = data.get("duration", "5s")
            duration = int(duration_str.replace("s", ""))
            generate_audio = data.get("generate_audio", True)
            
            # 从 multimodal_files 中提取素材
            first_frame = None
            last_frame = None
            reference_images = []
            reference_videos = []
            reference_audios = []
            
            multimodal_files = data.get("multimodal_files", [])
            for file in multimodal_files:
                # 支持两种格式的type判断
                file_type = file.get("type", "")
                file_url = file.get("url")
                role = file.get("role", "")
                
                # 判断是否是图片类型 (格式可能是 image 或者 image/xxx)
                if file_type.startswith("image/") or file_type == "image":
                    if role == "first_frame":
                        first_frame = file_url
                    elif role == "last_frame":
                        last_frame = file_url
                    else:
                        reference_images.append(file)
                # 判断是否是视频类型
                elif file_type.startswith("video/") or file_type == "video":
                    reference_videos.append(file)
                # 判断是否是音频类型
                elif file_type.startswith("audio/") or file_type == "audio":
                    reference_audios.append(file)

            # 调用真实视频 API
            result_data = await self.image_service.create_video_task(
                prompt=prompt,
                mode=mode,
                resolution=resolution,
                ratio=ratio,
                duration=duration,
                generate_audio=generate_audio,
                first_frame=first_frame,
                last_frame=last_frame,
                reference_images=reference_images,
                reference_videos=reference_videos,
                reference_audios=reference_audios,
                progress_callback=progress_callback,
                task_id=task_id
            )

            # 发送100%进度
            await progress_callback(task_id, 100)

            remote_video_url = result_data.get("video_url")

            # 视频仅下载到本地备份，不上传 TOS
            # tos_url 保持为火山引擎原始公网 URL，用于二次创作时的 API 调用
            final_url = remote_video_url
            tos_url = remote_video_url
            display_name = None
            try:
                media_data = await asyncio.to_thread(download_media_local_only, remote_video_url, 'video')
                if media_data:
                    local_path = media_data.get("local_path")
                    display_name = media_data.get("display_name")
                    if local_path:
                        filename = os.path.basename(local_path)
                        final_url = f"/local-media/videos/{filename}"
                        logger.info(f"视频已备份到本地: {final_url}")
                        logger.info(f"视频公网 URL (用于二次创作): {tos_url}")
                        if display_name:
                            logger.info(f"视频显示名称: {display_name}")
            except Exception as e:
                logger.warning(f"下载本地备份失败，将使用远程URL: {e}")

            duration_total = round(time.time() - start_time, 2)

            # 创建缩略图
            seed = random.randint(1000, 9999)
            thumbnail_url = random.choice(PLACEHOLDER_IMAGES).format(seed=seed)

            result = {
                "task_id": task_id,
                "type": "video",
                "user_id": user_id,
                "room_id": room_id,
                "url": final_url,
                "remote_url": tos_url,
                "displayName": display_name,
                "thumbnail": thumbnail_url,
                "duration": duration_total,
                "video_duration": result_data.get("duration"),
                "cost": round(random.uniform(5, 15), 2),
                "total_tokens": result_data.get("total_tokens") or 0,
                "created_at": int(time.time()),
                "params": {
                    "model": "seedance-2-0",
                    "aspect_ratio": ratio,
                    "resolution": resolution,
                    "duration": duration_str,
                    "prompt": prompt,
                    "displayPrompt": data.get("displayPrompt"),
                    "first_frame": first_frame,
                    "last_frame": last_frame,
                    "multimodal_files": multimodal_files,
                    "mode": mode,
                    "generate_audio": generate_audio
                }
            }

            await asyncio.to_thread(add_to_history, result)

            logger.info(f"✅ 视频生成成功 - 任务ID: {task_id}, 耗时: {duration_total}秒")

            await self.sio.emit(
                "video_completed",
                result,
                room=room_id
            )

        except Exception as e:
            logger.error(f"❌ 视频生成失败 - 任务ID: {task_id}, 错误: {str(e)}")
            
            await self.sio.emit(
                "generation_progress",
                {
                    "task_id": task_id,
                    "progress": 0,
                    "type": "video",
                    "user_id": user_id,
                    "error": str(e)
                },
                room=room_id
            )
            
            logger.info(f"🔄 启动回退机制 - 任务ID: {task_id}")
            await self._fallback_generate_video(sid, data, task_id, user_id, room_id)

    async def _fallback_generate_video(self, sid, data, task_id, user_id, room_id):
        """API 失败时通知前端生成失败"""
        logger.warning(f"⚠️ 视频生成失败（API不可用）- 任务ID: {task_id}")

        result = {
            "task_id": task_id,
            "type": "video",
            "user_id": user_id,
            "room_id": room_id,
            "url": None,
            "remote_url": None,
            "thumbnail": None,
            "duration": 0,
            "cost": 0,
            "total_tokens": 0,
            "created_at": int(time.time()),
            "is_fallback": True,
            "failed": True,
            "error": "视频生成失败：API服务不可用",
            "params": {
                "model": data.get("model"),
                "aspect_ratio": data.get("aspect_ratio"),
                "resolution": data.get("resolution"),
                "duration": data.get("duration"),
                "prompt": data.get("prompt"),
                "displayPrompt": data.get("displayPrompt"),
                "first_frame": data.get("first_frame"),
                "last_frame": data.get("last_frame"),
                "multimodal_files": data.get("multimodal_files", []),
                "mode": data.get("mode", "text-to-video")
            }
        }

        logger.info(f"❌ 视频生成失败通知已发送 - 任务ID: {task_id}")

        await self.sio.emit(
            "video_completed",
            result,
            room=room_id
        )

    async def handle_cancel_task(self, sid, data):
        """取消任务（目前主要用于视频任务）"""
        task_id = data.get("task_id")
        task_type = data.get("type", "video")
        room_id = data.get("room_id")
        user_id = self.connected_users.get(sid)
        
        logger.info(f"🚫 取消任务请求 - 任务ID: {task_id}, 类型: {task_type}, 房间: {room_id}")

        if task_type == "video":
            cancel_result = await self.image_service.cancel_video_task(task_id)
            
            # 发送到房间内的所有用户，让前端都更新进度列表
            target_room = room_id or sid
            await self.sio.emit(
                "task_cancelled",
                {
                    "task_id": task_id,
                    "type": "video",
                    "user_id": user_id,
                    "success": cancel_result.get("success", True),
                    "message": cancel_result.get("message", "Task cancelled")
                },
                room=target_room
            )
            
            logger.info(f"取消任务响应已发送: task_id={task_id}")

    async def handle_send_chat_message(self, sid, data):
        """处理聊天消息"""
        room_id = data.get("room_id")
        message = data.get("message", "")
        user_id = self.connected_users.get(sid)
        
        if not room_id or not message:
            return
            
        logger.info(f"💬 聊天消息 - 用户: {user_id}, 房间: {room_id}, 消息: {message[:50]}")
        
        # 存储消息
        chat_message = {
            "user_id": user_id,
            "room_id": room_id,
            "message": message,
            "type": "text"
        }
        saved_message = await asyncio.to_thread(add_chat_message, chat_message)
        
        # 广播给房间内所有用户
        await self.sio.emit(
            "chat_message",
            saved_message,
            room=room_id
        )

    async def handle_get_chat_history(self, sid, data):
        """获取聊天历史"""
        room_id = data.get("room_id")
        if not room_id:
            return
            
        chat_history = await asyncio.to_thread(get_chat_by_room, room_id)
        await self.sio.emit("chat_history", {"chat": chat_history}, room=sid)

    async def handle_get_templates(self, sid, data):
        """获取模版列表"""
        try:
            templates = await asyncio.to_thread(load_templates)
            await self.sio.emit("templates_list", {"templates": templates}, room=sid)
        except Exception as e:
            logger.error(f"❌ 获取模版列表失败: {e}")
            await self.sio.emit("templates_list", {"templates": []}, room=sid)

    async def handle_add_template(self, sid, data):
        """新增模版"""
        try:
            template_data = data.get("template")
            if not template_data or not template_data.get("name") or not template_data.get("content"):
                await self.sio.emit("template_error", {"error": "模版名称和内容不能为空"}, room=sid)
                return
                
            new_template = await asyncio.to_thread(add_template, template_data)
            logger.info(f"➕ 新增模版成功: {new_template['name']}")
            templates = await asyncio.to_thread(load_templates)
            await self.sio.emit("templates_list", {"templates": templates}, room=sid)
        except Exception as e:
            logger.error(f"❌ 新增模版失败: {e}")
            await self.sio.emit("template_error", {"error": str(e)}, room=sid)

    async def handle_update_template(self, sid, data):
        """更新模版"""
        try:
            template_id = data.get("template_id")
            template_data = data.get("template")
            if not template_id:
                await self.sio.emit("template_error", {"error": "模版ID不能为空"}, room=sid)
                return
                
            updated_template = await asyncio.to_thread(update_template, template_id, template_data)
            if updated_template:
                logger.info(f"✏️ 更新模版成功: {updated_template['name']}")
                templates = await asyncio.to_thread(load_templates)
                await self.sio.emit("templates_list", {"templates": templates}, room=sid)
            else:
                await self.sio.emit("template_error", {"error": "找不到该模版"}, room=sid)
        except Exception as e:
            logger.error(f"❌ 更新模版失败: {e}")
            await self.sio.emit("template_error", {"error": str(e)}, room=sid)

    async def handle_delete_template(self, sid, data):
        """删除模版"""
        try:
            template_id = data.get("template_id")
            if not template_id:
                await self.sio.emit("template_error", {"error": "模版ID不能为空"}, room=sid)
                return
                
            deleted = await asyncio.to_thread(delete_template, template_id)
            if deleted:
                logger.info(f"🗑️ 删除模版成功: {deleted['name']}")
                templates = await asyncio.to_thread(load_templates)
                await self.sio.emit("templates_list", {"templates": templates}, room=sid)
            else:
                await self.sio.emit("template_error", {"error": "找不到该模版"}, room=sid)
        except Exception as e:
            logger.error(f"❌ 删除模版失败: {e}")
            await self.sio.emit("template_error", {"error": str(e)}, room=sid)


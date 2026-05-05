# -*- coding: utf-8 -*-


import requests
import asyncio
import logging
from collections import OrderedDict
from typing import Dict, List, Optional, Callable, Any
from config import Config
import json

logger = logging.getLogger(__name__)


class PermanentTaskFailure(Exception):
    pass


class ImageAPIService:
    """图片生成 API 服务"""
    
    GRSAI_BASE_URL = Config.GRSAI_BASE_URL
    VOLCENGINE_BASE_URL = Config.VOLCENGINE_BASE_URL
    
    PERMANENT_ERROR_PATTERNS = [
        "high load",
        "please use another model",
        "model is not available",
        "model not found",
        "invalid model",
        "quota exceeded",
        "rate limit",
        "permission denied",
        "unauthorized",
        "forbidden",
        "content policy",
        "safety",
        "nsfw",
    ]
    
    task_id_map = {}
    cancelled_tasks = OrderedDict()
    MAX_CANCELLED_TASKS = 1000
    
    # 🟡 新增：公共方法 - 构建 GRSAI 通用 payload
    @classmethod
    def _build_grsai_payload(cls, model: str, prompt: str, aspect_ratio: Optional[str], 
                             resolution: Optional[str] = None, reference_images: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """构建 GRSAI 通用 payload"""
        payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": aspect_ratio or "auto",
            "webHook": "https://example.com/callback",
            "shutProgress": False
        }
        
        if resolution:
            payload["imageSize"] = resolution
        
        if reference_images:
            payload["urls"] = [img.get("url") for img in reference_images if img.get("url")]
        
        return payload
    
    @classmethod
    async def generate_image(cls, model: str, api_params: Dict[str, Any], progress_callback: Optional[Callable[[str, int], Any]] = None) -> Dict[str, Any]:
        """
        调用真实的图片生成 API
        
        Args:
            model: 模型名称
            api_params: API 参数字典
            progress_callback: 进度回调函数
            
        Returns:
            包含生成结果的字典
        """
        logger.info(f"Generating image with model: {model}")
        
        try:
            if model == "gpt-image-2" or model == "gpt-image-2-vip":
                result = await cls._call_grsai_gpt_image_2(
                    model,
                    api_params.get("prompt"),
                    api_params.get("aspect_ratio"),
                    api_params.get("resolution"),
                    api_params.get("reference_images"),
                    api_params.get("task_id"),
                    progress_callback
                )
            elif model.startswith("nano-banana"):
                result = await cls._call_grsai_nano_banana(
                    model,
                    api_params.get("prompt"),
                    api_params.get("aspect_ratio"),
                    api_params.get("resolution"),
                    api_params.get("reference_images"),
                    api_params.get("task_id"),
                    progress_callback
                )
            elif model == "seedream-5-0-lite":
                result = await cls._call_volcengine_seedream(
                    api_params.get("prompt"),
                    api_params.get("aspect_ratio"),
                    api_params.get("resolution"),
                    api_params.get("reference_images"),
                    api_params.get("mode"),
                    api_params.get("task_id"),
                    progress_callback
                )
            else:
                raise ValueError(f"Unsupported model: {model}")
            
            if result and result.get("images") and len(result["images"]) > 0:
                return {"url": result["images"][0]}
            raise Exception("No images generated")
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
    
    @classmethod
    async def _call_grsai_gpt_image_2(cls, model: str, prompt: str, aspect_ratio: Optional[str],
                                     resolution: Optional[str] = None,
                                     reference_images: Optional[List[Dict]] = None,
                                     task_id: Optional[str] = None,
                                     progress_callback: Optional[Callable[[str, int], Any]] = None) -> Dict[str, Any]:
        """调用 gpt-image-2 或 gpt-image-2-vip 模型"""
        url = f"{cls.GRSAI_BASE_URL}/v1/draw/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GRSAI_API_KEY}"
        }
        
        # 🟡 重构：使用公共方法构建 payload
        payload = cls._build_grsai_payload(
            model, prompt, aspect_ratio,
            resolution=resolution if model == "gpt-image-2-vip" else None,
            reference_images=reference_images
        )
        
        # 🔴 重点：记录完整请求信息
        logger.info("=" * 80)
        logger.info(f"📤 API 请求详情 (GRSAI {model})")
        logger.info(f"📍 请求地址: {url}")
        logger.info(f"📋 请求方法: POST")
        logger.info(f"🔑 请求头: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ***'}}")
        logger.info(f"📦 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)
        
        return await cls._poll_grsai_task(url, headers, payload, task_id, progress_callback)
    
    @classmethod
    async def _call_grsai_nano_banana(cls, model: str, prompt: str, aspect_ratio: Optional[str],
                                      resolution: Optional[str] = None,
                                      reference_images: Optional[List[Dict]] = None,
                                      task_id: Optional[str] = None,
                                      progress_callback: Optional[Callable[[str, int], Any]] = None) -> Dict[str, Any]:
        """调用 nano-banana 系列模型"""
        url = f"{cls.GRSAI_BASE_URL}/v1/draw/nano-banana"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.GRSAI_API_KEY}"
        }
        
        # 🟡 重构：使用公共方法构建 payload
        payload = cls._build_grsai_payload(
            model, prompt, aspect_ratio, 
            resolution=resolution, 
            reference_images=reference_images
        )
        
        # 🔴 重点：记录完整请求信息
        logger.info("=" * 80)
        logger.info(f"📤 API 请求详情 (GRSAI {model})")
        logger.info(f"📍 请求地址: {url}")
        logger.info(f"📋 请求方法: POST")
        logger.info(f"🔑 请求头: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ***'}}")
        logger.info(f"📦 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)
        
        return await cls._poll_grsai_task(url, headers, payload, task_id, progress_callback)
    
    @classmethod
    def _is_permanent_error(cls, error_msg: str) -> bool:
        msg_lower = error_msg.lower()
        return any(pattern in msg_lower for pattern in cls.PERMANENT_ERROR_PATTERNS)

    @classmethod
    async def _poll_grsai_task(cls, url: str, headers: Dict[str, str], payload: Dict[str, Any],
                               task_id: Optional[str] = None,
                               progress_callback: Optional[Callable[[str, int], Any]] = None) -> Dict[str, Any]:
        """轮询 GRSAI 任务状态"""
        response = await asyncio.to_thread(requests.post, url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        logger.info("=" * 80)
        logger.info("📥 API 初始响应（获取task_id）")
        logger.info(f"📊 响应状态码: {response.status_code}")
        logger.info(f"📦 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)

        task_id_from_api = result.get("data", {}).get("id")
        logger.info(f"🎯 任务创建成功 - ID: {task_id_from_api}")

        query_url = f"{cls.GRSAI_BASE_URL}/v1/draw/result"
        query_payload = {"id": task_id_from_api}

        max_attempts = Config.IMAGE_MAX_ATTEMPTS
        attempt = 0
        last_progress = 0
        consecutive_network_errors = 0
        max_consecutive_network_errors = 3

        logger.info(f"🔄 开始轮询任务状态 - 最多 {max_attempts} 次")

        while attempt < max_attempts:
            attempt += 1
            try:
                logger.debug(f"🔄 轮询第 {attempt}/{max_attempts} 次")
                logger.debug(f"📍 轮询地址: {query_url}")
                logger.debug(f"📦 轮询参数: {json.dumps(query_payload, ensure_ascii=False)}")
                
                query_response = await asyncio.to_thread(requests.post, query_url, json=query_payload, headers=headers)
                query_response.raise_for_status()
                query_result = query_response.json()
                
                consecutive_network_errors = 0

                status = query_result.get("data", {}).get("status", query_result.get("status"))
                progress = query_result.get("data", {}).get("progress", query_result.get("progress", 0))
                logger.debug(f"📥 轮询响应 - 状态: {status}, 进度: {progress}")
                
                if query_result.get("code") == 0 and "data" in query_result:
                    result_data = query_result["data"]
                else:
                    result_data = query_result
                
                status = result_data.get("status")
                progress = result_data.get("progress", 0)
                
                if status == "succeeded":
                    logger.info("=" * 80)
                    logger.info("✅ API 最终响应（任务完成）")
                    logger.info(f"📦 响应数据: {json.dumps(query_result, ensure_ascii=False, indent=2)}")
                    logger.info("=" * 80)
                    
                    images = [r.get("url") for r in result_data.get("results", []) if r.get("url")]
                    if not images and result_data.get("url"):
                        images = [result_data.get("url")]
                    logger.info(f"🖼️ 生成的图片URL: {images}")
                    return {
                        "success": True,
                        "images": images,
                        "progress": result_data.get("progress", 100)
                    }
                elif status == "failed":
                    error_msg = result_data.get("error", result_data.get("failure_reason", "Unknown error"))
                    logger.error(f"❌ 任务失败: {error_msg}")
                    raise PermanentTaskFailure(f"Image generation failed: {error_msg}")
                elif status == "running":
                    if progress_callback and task_id:
                        await progress_callback(task_id, progress)
                
            except PermanentTaskFailure:
                raise
            except Exception as e:
                consecutive_network_errors += 1
                logger.warning(f"⚠️ 轮询第 {attempt} 次网络异常: {e}")
                if consecutive_network_errors >= max_consecutive_network_errors:
                    logger.error(f"❌ 连续 {consecutive_network_errors} 次网络异常，终止轮询")
                    raise Exception(f"Polling failed after {consecutive_network_errors} consecutive network errors: {e}")
            
            if attempt == 1:
                sleep_time = 5
            elif attempt == 2:
                sleep_time = 15
            else:
                sleep_time = 5
            
            logger.debug(f"⏱️ 等待 {sleep_time} 秒后进行下一次轮询")
            await asyncio.sleep(sleep_time)
        
        logger.error(f"❌ 任务超时! (已达到最大尝试次数 {max_attempts})")
        raise Exception("Task timeout")
    
    @classmethod
    async def _call_volcengine_seedream(cls, prompt: str, aspect_ratio: Optional[str],
                                        resolution: Optional[str] = None,
                                        reference_images: Optional[List] = None,
                                        mode: str = "text-to-image",
                                        task_id: Optional[str] = None,
                                        progress_callback: Optional[Callable[[str, int], Any]] = None) -> Dict[str, Any]:
        """调用 Seedream 5.0 Lite 模型"""
        url = f"{cls.VOLCENGINE_BASE_URL}/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.VOLCENGINE_API_KEY}"
        }
        
        aspect_size_map = {
            "1:1": {"2K": "2048x2048", "3K": "3072x3072"},
            "16:9": {"2K": "2848x1600", "3K": "4096x2304"},
            "9:16": {"2K": "1600x2848", "3K": "2304x4096"},
            "4:3": {"2K": "2304x1728", "3K": "3456x2592"},
            "3:4": {"2K": "1728x2304", "3K": "2592x3456"},
            "auto": {"2K": "2048x2048", "3K": "3072x3072"}
        }
        
        selected_resolution = resolution or "2K"
        size = aspect_size_map.get(aspect_ratio, aspect_size_map["auto"]).get(selected_resolution, "2048x2048")
        
        payload = {
            "model": "doubao-seedream-5-0-260128",
            "prompt": prompt,
            "size": size,
            "output_format": "png",
            "response_format": "url",
            "watermark": False
        }
        
        if reference_images and len(reference_images) > 0:
            if len(reference_images) == 1:
                payload["image"] = reference_images[0]
            else:
                payload["image"] = reference_images
        
        # 🔴 重点：记录完整请求信息
        logger.info("=" * 80)
        logger.info("📤 API 请求详情 (Volcengine Seedream)")
        logger.info(f"📍 请求地址: {url}")
        logger.info(f"📋 请求方法: POST")
        logger.info(f"🔑 请求头: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ***'}}")
        logger.info(f"📦 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)
        
        try:
            for progress in range(0, 100, 10):
                await asyncio.sleep(1)
                if progress_callback and task_id:
                    await progress_callback(task_id, progress)
            
            response = await asyncio.to_thread(requests.post, url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 🟡 副重点：记录响应数据
            logger.info("=" * 80)
            logger.info("📥 API 响应 (Volcengine Seedream)")
            logger.info(f"📊 响应状态码: {response.status_code}")
            logger.info(f"📦 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            logger.info("=" * 80)
            
            images = [data.get("url") for data in result.get("data", []) if data.get("url")]
            
            logger.info(f"✅ Volcengine 图片生成成功")
            logger.info(f"🖼️ 生成的图片URL: {images}")
            
            return {
                "success": True,
                "images": images,
                "progress": 100
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ Volcengine API 错误: {e.response.text}")
            raise Exception(f"Volcengine API error: {e.response.text}")
    
    @classmethod
    async def create_video_task(cls, prompt: str,
                               mode: str = "text-to-video",
                               resolution: str = "720p",
                               ratio: str = "16:9",
                               duration: int = 5,
                               generate_audio: bool = True,
                               first_frame: Optional[str] = None,
                               last_frame: Optional[str] = None,
                               reference_images: Optional[List[Dict]] = None,
                               reference_videos: Optional[List[Dict]] = None,
                               reference_audios: Optional[List[Dict]] = None,
                               progress_callback: Optional[Callable[[str, int], Any]] = None,
                               task_id: Optional[str] = None) -> Dict[str, Any]:
        """创建 Seedance 2.0 视频生成任务"""
        url = f"{cls.VOLCENGINE_BASE_URL}/contents/generations/tasks"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.VOLCENGINE_API_KEY}"
        }
        
        content = []
        
        # 添加提示词
        content.append({
            "type": "text",
            "text": prompt
        })
        
        # 判断模式：首尾帧模式 vs 其他模式
        has_both_frames = first_frame is not None and last_frame is not None
        has_only_first = first_frame is not None and last_frame is None
        
        # 添加首帧
        if first_frame:
            # 如果是首尾帧模式，需要添加 role
            if has_both_frames:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": first_frame},
                    "role": "first_frame"
                })
            else:
                # 只有首帧，不需要 role（文档中只首帧模式没有 role）
                content.append({
                    "type": "image_url",
                    "image_url": {"url": first_frame}
                })
        
        # 添加尾帧（只能在首尾帧模式下使用）
        if last_frame and has_both_frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": last_frame},
                "role": "last_frame"
            })
        
        # 添加参考素材（仅在非首尾帧模式下）
        if not has_both_frames:
            # 添加参考图片（reference 模式）
            if reference_images and len(reference_images) > 0:
                for img in reference_images:
                    img_url = img.get("url") if isinstance(img, dict) else img
                    if img_url:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": img_url},
                            "role": "reference_image"
                        })
            
            # 添加参考视频（reference 模式）
            if reference_videos and len(reference_videos) > 0:
                for vid in reference_videos:
                    vid_url = vid.get("url") if isinstance(vid, dict) else vid
                    if vid_url:
                        content.append({
                            "type": "video_url",
                            "video_url": {"url": vid_url},
                            "role": "reference_video"
                        })
            
            # 添加参考音频（reference 模式）
            if reference_audios and len(reference_audios) > 0:
                for aud in reference_audios:
                    aud_url = aud.get("url") if isinstance(aud, dict) else aud
                    if aud_url:
                        content.append({
                            "type": "audio_url",
                            "audio_url": {"url": aud_url},
                            "role": "reference_audio"
                        })
        
        payload = {
            "model": "doubao-seedance-2-0-260128",
            "content": content,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": generate_audio,
            "watermark": False,
            "return_last_frame": True
        }
        
        # 🔴 重点：记录完整请求信息
        logger.info("=" * 80)
        logger.info("📤 API 请求详情 (Volcengine Seedance 视频)")
        logger.info(f"📍 请求地址: {url}")
        logger.info(f"📋 请求方法: POST")
        logger.info(f"🔑 请求头: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ***'}}")
        logger.info(f"📦 请求参数: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)
        
        try:
            response = await asyncio.to_thread(requests.post, url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # 🟡 副重点：记录初始响应
            logger.info("=" * 80)
            logger.info("📥 API 初始响应（创建视频任务）")
            logger.info(f"📊 响应状态码: {response.status_code}")
            logger.info(f"📦 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            logger.info("=" * 80)
            
            task_id_from_api = result.get("id")
            logger.info(f"🎯 视频任务创建成功 - ID: {task_id_from_api}")
            
            if not task_id_from_api:
                raise Exception("No task ID returned from API")
            
            # 保存任务 ID 映射关系
            if task_id:
                cls.task_id_map[task_id] = task_id_from_api
                logger.info(f"🔗 保存任务映射: 本地任务 {task_id} -> API任务 {task_id_from_api}")
            
            # 开始轮询任务状态
            return await cls._poll_video_task(task_id_from_api, headers, progress_callback, task_id)
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ 视频任务创建错误: {e.response.text}")
            raise Exception(f"Video task creation error: {e.response.text}")
    
    @classmethod
    async def _poll_video_task(cls, task_id_from_api: str, headers: Dict[str, str],
                              progress_callback: Optional[Callable[[str, int], Any]] = None,
                              task_id: Optional[str] = None) -> Dict[str, Any]:
        """轮询视频任务状态"""
        url = f"{cls.VOLCENGINE_BASE_URL}/contents/generations/tasks/{task_id_from_api}"
        
        max_attempts = Config.VIDEO_MAX_ATTEMPTS
        attempt = 0
        last_status = None
        consecutive_network_errors = 0
        max_consecutive_network_errors = 3
        
        logger.info(f"🔄 开始轮询视频任务状态 - 最多 {max_attempts} 次")
        
        while attempt < max_attempts:
            attempt += 1
            try:
                if task_id and task_id in cls.cancelled_tasks:
                    logger.info(f"🚫 任务已被取消: {task_id}")
                    cls.cancelled_tasks.pop(task_id, None)
                    if task_id in cls.task_id_map:
                        del cls.task_id_map[task_id]
                    raise PermanentTaskFailure("Task cancelled by user")
                
                logger.debug(f"🔄 轮询第 {attempt}/{max_attempts} 次")
                logger.debug(f"📍 轮询地址: {url}")
                
                query_response = await asyncio.to_thread(requests.get, url, headers=headers)
                query_response.raise_for_status()
                query_result = query_response.json()
                
                consecutive_network_errors = 0
                
                status = query_result.get("status")
                
                logger.debug(f"📥 轮询响应 - 状态: {status}")
                
                if status != last_status:
                    logger.info(f"📊 状态变化: {last_status} -> {status}")
                    last_status = status
                
                if status == "succeeded":
                    logger.info("=" * 80)
                    logger.info("✅ API 最终响应（视频任务完成）")
                    logger.info(f"📦 响应数据: {json.dumps(query_result, ensure_ascii=False, indent=2)}")
                    logger.info("=" * 80)
                    
                    logger.info(f"✅ 视频任务成功完成!")
                    
                    video_url = query_result.get("content", {}).get("video_url")
                    logger.info(f"🎬 生成的视频URL: {video_url}")
                    
                    if task_id and task_id in cls.task_id_map:
                        del cls.task_id_map[task_id]
                    
                    return {
                        "success": True,
                        "video_url": video_url,
                        "duration": query_result.get("duration"),
                        "resolution": query_result.get("resolution"),
                        "ratio": query_result.get("ratio"),
                        "framespersecond": query_result.get("framespersecond"),
                        "generate_audio": query_result.get("generate_audio"),
                        "progress": 100,
                        "task_id": task_id_from_api
                    }
                
                elif status == "failed":
                    if task_id and task_id in cls.task_id_map:
                        del cls.task_id_map[task_id]
                    
                    error_msg = query_result.get("error", "Unknown error")
                    logger.error(f"❌ 视频任务失败: {error_msg}")
                    raise PermanentTaskFailure(f"Video generation failed: {error_msg}")
                
                elif status == "queued" or status == "in_progress":
                    estimated_progress = min(10, attempt * 1) if status == "queued" else min(90, attempt * 2)
                    
                    if progress_callback and task_id:
                        await progress_callback(task_id, estimated_progress)
                
            except PermanentTaskFailure:
                raise
            except Exception as e:
                consecutive_network_errors += 1
                logger.warning(f"⚠️ 视频轮询第 {attempt} 次网络异常: {e}")
                if consecutive_network_errors >= max_consecutive_network_errors:
                    logger.error(f"❌ 连续 {consecutive_network_errors} 次网络异常，终止轮询")
                    raise Exception(f"Video polling failed after {consecutive_network_errors} consecutive network errors: {e}")
            
            if attempt == 1:
                sleep_time = 15
            elif 2 <= attempt <= 5:
                sleep_time = 30
            else:
                sleep_time = 15
            
            logger.debug(f"⏱️ 等待 {sleep_time} 秒后进行下一次轮询")
            await asyncio.sleep(sleep_time)
        
        logger.error(f"❌ 视频任务超时! (已达到最大尝试次数 {max_attempts})")
        raise Exception("Video task timeout")
    
    @classmethod
    async def cancel_video_task(cls, task_id: str):
        """取消视频任务"""
        logger.info(f"🚫 请求取消视频任务: {task_id}")
        
        cls.cancelled_tasks[task_id] = True
        while len(cls.cancelled_tasks) > cls.MAX_CANCELLED_TASKS:
            cls.cancelled_tasks.popitem(last=False)
        logger.info(f"🔖 标记任务为已取消: {task_id}")
        
        task_id_from_api = cls.task_id_map.get(task_id)
        
        if task_id_from_api:
            logger.info(f"🔗 找到对应的API任务: {task_id_from_api}")
            
            try:
                url = f"{cls.VOLCENGINE_BASE_URL}/contents/generations/tasks/{task_id_from_api}"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {Config.VOLCENGINE_API_KEY}"
                }
                
                logger.info(f"📤 调用火山引擎取消任务 API: {url}")
                response = await asyncio.to_thread(requests.delete, url, headers=headers)
                
                if response.status_code == 200:
                    logger.info(f"✅ 火山引擎取消任务 API 调用成功")
                    result = response.json()
                    logger.info(f"📦 取消响应: {json.dumps(result, ensure_ascii=False)}")
                else:
                    logger.warning(f"⚠️ 火山引擎取消任务 API 返回状态码: {response.status_code}")
                    logger.warning(f"📦 响应内容: {response.text}")
            
            except Exception as e:
                logger.warning(f"⚠️ 调用火山引擎取消任务 API 失败: {e}")
                logger.warning("⚠️ 将仅在本地标记任务为取消")
        
        return {"success": True, "message": "Task cancellation requested"}

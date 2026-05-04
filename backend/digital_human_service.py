# -*- coding: utf-8 -*-
import requests
import asyncio
import logging
import json
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class DigitalHumanService:
    API_KEY = Config.DIGITAL_HUMAN_API_KEY
    BASE_URL = Config.DIGITAL_HUMAN_BASE_URL
    MODEL = Config.DIGITAL_HUMAN_MODEL

    MAX_POLL_ATTEMPTS = 120

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.API_KEY and cls.BASE_URL and cls.MODEL)

    @classmethod
    async def create_digital_human(cls, image_url: str, audio_url: str,
                                    progress_callback=None, task_id: str = "",
                                    **kwargs) -> dict:
        if not cls.is_configured():
            raise Exception("数字人API未配置，请在config.py或.env中设置DIGITAL_HUMAN_API_KEY、DIGITAL_HUMAN_BASE_URL、DIGITAL_HUMAN_MODEL")

        url = f"{cls.BASE_URL}/digital-human/generate"
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": cls.MODEL,
            "image_url": image_url,
            "audio_url": audio_url,
        }

        for key, value in kwargs.items():
            if value is not None:
                payload[key] = value

        logger.info(f"发起数字人生成请求: model={cls.MODEL}")

        if progress_callback and task_id:
            await progress_callback(task_id, 10)

        response = requests.post(url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        result = response.json()

        logger.info(f"数字人生成请求响应: {json.dumps(result, ensure_ascii=False)}")

        task_id_from_api = result.get("task_id") or result.get("id")
        if not task_id_from_api:
            video_url = result.get("video_url") or result.get("url")
            if video_url:
                if progress_callback and task_id:
                    await progress_callback(task_id, 100)
                return {
                    "success": True,
                    "video_url": video_url
                }
            raise Exception(f"数字人API未返回task_id或video_url: {result}")

        if progress_callback and task_id:
            await progress_callback(task_id, 30)

        video_url = await cls._poll_task(task_id_from_api, headers, progress_callback, task_id)

        return {
            "success": True,
            "video_url": video_url,
            "task_id": task_id_from_api
        }

    @classmethod
    async def _poll_task(cls, task_id_from_api: str, headers: dict,
                         progress_callback=None, task_id: str = "") -> str:
        url = f"{cls.BASE_URL}/digital-human/tasks/{task_id_from_api}"

        max_attempts = cls.MAX_POLL_ATTEMPTS
        attempt = 0
        consecutive_errors = 0

        logger.info(f"开始轮询数字人任务: {task_id_from_api}")

        while attempt < max_attempts:
            attempt += 1
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()

                consecutive_errors = 0

                status = result.get("status")
                logger.debug(f"轮询第 {attempt} 次，状态: {status}")

                if status == "succeeded" or status == "completed" or status == "success":
                    video_url = result.get("video_url") or result.get("url")
                    if video_url:
                        logger.info(f"数字人任务完成: {video_url}")
                        if progress_callback and task_id:
                            await progress_callback(task_id, 100)
                        return video_url
                    raise Exception(f"任务成功但未返回video_url: {result}")

                elif status == "failed" or status == "error":
                    error_msg = result.get("error", result.get("message", "Unknown error"))
                    raise Exception(f"数字人生成失败: {error_msg}")

                else:
                    progress = 30 + int((attempt / max_attempts) * 60)
                    if progress_callback and task_id:
                        await progress_callback(task_id, min(progress, 95))

            except Exception as e:
                if "数字人生成失败" in str(e) or "未返回video_url" in str(e):
                    raise
                consecutive_errors += 1
                logger.warning(f"轮询第 {attempt} 次异常: {e}")
                if consecutive_errors >= 3:
                    raise Exception(f"连续3次轮询失败: {e}")

            await asyncio.sleep(5)

        raise Exception(f"数字人生成超时，已轮询 {max_attempts} 次")

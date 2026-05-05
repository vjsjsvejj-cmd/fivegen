# -*- coding: utf-8 -*-
import requests
import asyncio
import logging
import json
import time
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class VoiceCloneService:
    BASE_URL = Config.GLM_BASE_URL
    API_KEY = Config.GLM_API_KEY

    MAX_UPLOAD_ATTEMPTS = 60
    MAX_CLONE_ATTEMPTS = 120
    MAX_429_RETRIES = 10
    RETRY_BASE_DELAY = 10

    @classmethod
    def _get_headers(cls, content_type="application/json"):
        return {
            "Authorization": f"Bearer {cls.API_KEY}",
            "Content-Type": content_type
        }

    @classmethod
    def _request_with_retry(cls, method: str, url: str, max_retries: int = None, **kwargs) -> requests.Response:
        if max_retries is None:
            max_retries = cls.MAX_429_RETRIES

        last_error = None
        for attempt in range(max_retries):
            try:
                if method.upper() == "POST":
                    response = requests.post(url, headers=kwargs.pop("headers", cls._get_headers()), timeout=kwargs.pop("timeout", 120), **kwargs)
                else:
                    response = requests.get(url, headers=kwargs.pop("headers", cls._get_headers()), timeout=kwargs.pop("timeout", 30), **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", cls.RETRY_BASE_DELAY * (attempt + 1)))
                    retry_after = min(retry_after, 120)
                    logger.warning(f"429 速率限制，第 {attempt + 1}/{max_retries} 次重试，等待 {retry_after}秒...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", cls.RETRY_BASE_DELAY * (attempt + 1)))
                    retry_after = min(retry_after, 120)
                    logger.warning(f"429 速率限制，第 {attempt + 1}/{max_retries} 次重试，等待 {retry_after}秒...")
                    time.sleep(retry_after)
                    last_error = e
                    continue

                try:
                    error_body = e.response.json()
                    error_code = error_body.get("error", {}).get("code", "")
                    error_msg = error_body.get("error", {}).get("message", str(e))

                    if error_code == "1302":
                        raise Exception(f"API调用频率超限：{error_msg}。请在智谱开放平台查看您的速率限制，或稍后再试。")
                    elif error_code == "1305":
                        raise Exception(f"智谱平台服务过载，请稍后再试。")
                    else:
                        raise Exception(f"API请求失败({e.response.status_code}): {error_msg}")
                except (AttributeError, ValueError):
                    raise Exception(f"API请求失败: {e}")

            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = cls.RETRY_BASE_DELAY * (attempt + 1)
                    logger.warning(f"连接错误，第 {attempt + 1}/{max_retries} 次重试，等待 {delay}秒...")
                    time.sleep(delay)
                    continue
                raise Exception(f"连接智谱AI失败: {e}")

        raise Exception(f"请求失败，已重试 {max_retries} 次。最后错误: {last_error}")

    @classmethod
    def upload_audio_file(cls, file_path: str, filename: str) -> dict:
        headers = {
            "Authorization": f"Bearer {cls.API_KEY}"
        }
        url = f"{cls.BASE_URL}/files"

        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, 'audio/mpeg')
            }
            data = {
                'purpose': 'voice-clone-input'
            }

            logger.info(f"上传音频文件到智谱: {filename}")

            last_error = None
            for attempt in range(cls.MAX_429_RETRIES):
                try:
                    f.seek(0)
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=120)

                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", cls.RETRY_BASE_DELAY * (attempt + 1)))
                        retry_after = min(retry_after, 120)
                        logger.warning(f"上传文件429限制，第 {attempt + 1} 次重试，等待 {retry_after}秒...")
                        time.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    result = response.json()
                    logger.info(f"音频文件上传成功: file_id={result.get('id')}")
                    return result

                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 429:
                        retry_after = int(e.response.headers.get("Retry-After", cls.RETRY_BASE_DELAY * (attempt + 1)))
                        retry_after = min(retry_after, 120)
                        logger.warning(f"上传文件429限制，第 {attempt + 1} 次重试，等待 {retry_after}秒...")
                        time.sleep(retry_after)
                        last_error = e
                        continue
                    try:
                        error_body = e.response.json()
                        error_msg = error_body.get("error", {}).get("message", str(e))
                        raise Exception(f"上传音频失败({e.response.status_code}): {error_msg}")
                    except (AttributeError, ValueError):
                        raise Exception(f"上传音频失败: {e}")

            raise Exception(f"上传音频失败，已重试 {cls.MAX_429_RETRIES} 次。最后错误: {last_error}")

    @classmethod
    async def clone_voice(cls, voice_name: str, input_text: str, file_id: str,
                          reference_text: str = "", request_id: str = "",
                          progress_callback=None, task_id: str = "") -> dict:
        url = f"{cls.BASE_URL}/voice/clone"
        headers = cls._get_headers()

        payload = {
            "model": Config.GLM_TTS_MODEL,
            "voice_name": voice_name,
            "input": input_text,
            "file_id": file_id
        }

        if reference_text:
            payload["text"] = reference_text
        if request_id:
            payload["request_id"] = request_id

        logger.info(f"发起音色复刻请求: voice_name={voice_name}, file_id={file_id}")

        if progress_callback and task_id:
            await progress_callback(task_id, 10)

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: cls._request_with_retry("POST", url, json=payload)
        )
        result = response.json()

        logger.info(f"音色复刻请求响应: {json.dumps(result, ensure_ascii=False)}")

        output_file_id = result.get("file_id")
        if not output_file_id:
            raise Exception(f"音色复刻未返回file_id: {result}")

        if progress_callback and task_id:
            await progress_callback(task_id, 30)

        audio_url = await cls._poll_async_result(output_file_id, progress_callback, task_id)

        return {
            "success": True,
            "audio_url": audio_url,
            "voice": result.get("voice"),
            "file_id": output_file_id,
            "request_id": result.get("request_id")
        }

    @classmethod
    async def _poll_async_result(cls, result_id: str, progress_callback=None, task_id: str = "") -> str:
        url = f"{cls.BASE_URL}/async-result/{result_id}"
        headers = cls._get_headers()

        max_attempts = cls.MAX_CLONE_ATTEMPTS
        attempt = 0
        consecutive_errors = 0

        logger.info(f"开始轮询异步结果: {result_id}, 最多 {max_attempts} 次")

        while attempt < max_attempts:
            attempt += 1
            try:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: cls._request_with_retry("GET", url, max_retries=3)
                )
                result = response.json()

                consecutive_errors = 0

                choices = result.get("choices", [])
                if choices and len(choices) > 0:
                    message = choices[0].get("message", {})
                    audio_info = message.get("audio", {})
                    if audio_info:
                        audio_data = audio_info.get("data")
                        audio_id = audio_info.get("id")
                        if audio_data:
                            logger.info(f"异步结果获取成功，包含音频数据")
                            progress = 30 + int((attempt / max_attempts) * 60)
                            if progress_callback and task_id:
                                await progress_callback(task_id, min(progress, 95))
                            return audio_data

                if progress_callback and task_id:
                    progress = 30 + int((attempt / max_attempts) * 60)
                    await progress_callback(task_id, min(progress, 95))

                logger.debug(f"轮询第 {attempt} 次，结果尚未就绪")

            except Exception as e:
                consecutive_errors += 1
                logger.warning(f"轮询第 {attempt} 次异常: {e}")
                if consecutive_errors >= 3:
                    raise Exception(f"连续3次轮询失败: {e}")

            await asyncio.sleep(3)

        raise Exception(f"音色复刻超时，已轮询 {max_attempts} 次")

    @classmethod
    def download_audio(cls, audio_data: str, save_path: str) -> str:
        import base64
        audio_bytes = base64.b64decode(audio_data)
        with open(save_path, 'wb') as f:
            f.write(audio_bytes)
        logger.info(f"音频文件已保存: {save_path}")
        return save_path

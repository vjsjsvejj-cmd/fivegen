# -*- coding: utf-8 -*-
import os
import uuid
from typing import Optional
from datetime import datetime
import tos
import logging

logger = logging.getLogger(__name__)


class TosService:
    def __init__(self, access_key: str, secret_key: str, endpoint: str, region: str, bucket: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.region = region
        self.bucket = bucket
        self.client: Optional[tos.TosClientV2] = None
        self._init_client()

    def _init_client(self):
        try:
            self.client = tos.TosClientV2(
                self.access_key,
                self.secret_key,
                self.endpoint,
                self.region
            )
            logger.info("TOS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TOS client: {e}")
            raise

    def _generate_file_key(self, file_name: str) -> str:
        """生成唯一的文件 key"""
        ext = os.path.splitext(file_name)[1].lower()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"uploads/{timestamp}_{unique_id}{ext}"

    def upload_file(self, file_path: str, file_name: Optional[str] = None) -> str:
        """上传本地文件到 TOS"""
        if not self.client:
            raise RuntimeError("TOS client not initialized")

        if not file_name:
            file_name = os.path.basename(file_path)

        key = self._generate_file_key(file_name)

        try:
            self.client.put_object_from_file(
                self.bucket,
                key,
                file_path
            )
            public_url = f"https://{self.bucket}.{self.endpoint}/{key}"
            logger.info(f"File uploaded successfully: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload file to TOS: {e}")
            raise

    def upload_bytes(self, data: bytes, file_name: str, content_type: Optional[str] = None) -> str:
        """上传二进制数据到 TOS"""
        if not self.client:
            raise RuntimeError("TOS client not initialized")

        key = self._generate_file_key(file_name)

        try:
            content_type = content_type or "application/octet-stream"
            self.client.put_object(
                self.bucket,
                key,
                content=data,
                content_type=content_type
            )
            public_url = f"https://{self.bucket}.{self.endpoint}/{key}"
            logger.info(f"Bytes uploaded successfully: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload bytes to TOS: {e}")
            raise


# 全局实例
_tos_service: Optional[TosService] = None


def init_tos_service(access_key: str, secret_key: str, endpoint: str, region: str, bucket: str) -> TosService:
    """初始化并返回 TOS 服务单例"""
    global _tos_service
    if _tos_service is None:
        _tos_service = TosService(access_key, secret_key, endpoint, region, bucket)
    return _tos_service


def get_tos_service() -> Optional[TosService]:
    """获取 TOS 服务实例"""
    return _tos_service

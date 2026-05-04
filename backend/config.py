# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()


class Config:
    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    # CORS 配置
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    # TOS 配置
    TOS_ACCESS_KEY = os.getenv("TOS_ACCESS_KEY", "")
    TOS_SECRET_KEY = os.getenv("TOS_SECRET_KEY", "")
    TOS_ENDPOINT = os.getenv("TOS_ENDPOINT", "tos-cn-beijing.volces.com")
    TOS_REGION = os.getenv("TOS_REGION", "cn-beijing")
    TOS_BUCKET = os.getenv("TOS_BUCKET", "fivesd")

    # 火山引擎配置
    VOLCENGINE_API_KEY = os.getenv("VOLCENGINE_API_KEY", "")
    VOLCENGINE_IMAGE_MODEL = os.getenv("VOLCENGINE_IMAGE_MODEL", "doubao-seedream-5-0-260128")
    VOLCENGINE_VIDEO_MODEL = os.getenv("VOLCENGINE_VIDEO_MODEL", "doubao-seedance-2-0-260128")

    # GRSAI 配置
    GRSAI_API_KEY = os.getenv("GRSAI_API_KEY", "")
    
    # 🟡 新增：轮询配置
    IMAGE_MAX_ATTEMPTS = 220
    VIDEO_MAX_ATTEMPTS = 880
    
    # 🟡 新增：下载配置
    IMAGE_DOWNLOAD_TIMEOUT = 180
    VIDEO_DOWNLOAD_TIMEOUT = 600
    
    # 🟡 新增：API 基础 URL 配置
    GRSAI_BASE_URL = "https://grsai.dakka.com.cn"
    VOLCENGINE_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    
    # 🟡 新增：逆向解析配置
    INVERSION_API_KEY = os.getenv("INVERSION_API_KEY", "ark-bbf4478d-2133-4a2b-9ca3-0a36f59fb590-19753")
    INVERSION_MODEL = os.getenv("INVERSION_MODEL", "doubao-seed-2-0-lite-260215")
    INVERSION_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    # 智谱AI 声音克隆配置
    GLM_API_KEY = os.getenv("GLM_API_KEY", "00ea5384526546b28f86b88db98ab35e.mPVV4dpYNMUqnxBB")
    GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    GLM_TTS_MODEL = "glm-tts-clone"

    # 数字人配置（待定API）
    DIGITAL_HUMAN_API_KEY = os.getenv("DIGITAL_HUMAN_API_KEY", "")
    DIGITAL_HUMAN_BASE_URL = os.getenv("DIGITAL_HUMAN_BASE_URL", "")
    DIGITAL_HUMAN_MODEL = os.getenv("DIGITAL_HUMAN_MODEL", "")

    @classmethod
    def validate(cls):
        """验证配置验证"""
        if not cls.TOS_ACCESS_KEY or not cls.TOS_SECRET_KEY:
            logger.warning("TOS credentials not configured - TOS upload will be disabled")
            return False
        return True

    @classmethod
    def is_tos_enabled(cls) -> bool:
        return bool(cls.TOS_ACCESS_KEY and cls.TOS_SECRET_KEY)


# 创建临时上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

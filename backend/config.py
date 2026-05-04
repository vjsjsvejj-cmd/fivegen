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
    # 生产环境应明确指定允许的域名，如: http://localhost:3000,http://192.168.1.100:3000
    # 开发环境可使用 * 允许所有来源，但切勿在生产环境使用
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

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
    INVERSION_API_KEY = os.getenv("INVERSION_API_KEY", "")
    INVERSION_MODEL = os.getenv("INVERSION_MODEL", "doubao-seed-2-0-lite-260215")
    INVERSION_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    GLM_API_KEY = os.getenv("GLM_API_KEY", "")
    GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
    GLM_TTS_MODEL = "glm-tts-clone"

    # 数字人配置（待定API）
    DIGITAL_HUMAN_API_KEY = os.getenv("DIGITAL_HUMAN_API_KEY", "")
    DIGITAL_HUMAN_BASE_URL = os.getenv("DIGITAL_HUMAN_BASE_URL", "")
    DIGITAL_HUMAN_MODEL = os.getenv("DIGITAL_HUMAN_MODEL", "")

    @classmethod
    def validate(cls):
        warnings = []
        if not cls.TOS_ACCESS_KEY or not cls.TOS_SECRET_KEY:
            warnings.append("TOS credentials not configured - TOS upload will be disabled")
        if not cls.INVERSION_API_KEY:
            warnings.append("INVERSION_API_KEY not configured - inversion feature will be disabled")
        if not cls.GLM_API_KEY:
            warnings.append("GLM_API_KEY not configured - voice clone feature will be disabled")
        for w in warnings:
            logger.warning(w)
        return len(warnings) == 0

    @classmethod
    def is_tos_enabled(cls) -> bool:
        return bool(cls.TOS_ACCESS_KEY and cls.TOS_SECRET_KEY)

    @classmethod
    def is_inversion_enabled(cls) -> bool:
        return bool(cls.INVERSION_API_KEY)

    @classmethod
    def is_voice_clone_enabled(cls) -> bool:
        return bool(cls.GLM_API_KEY)


# 创建临时上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def cleanup_temp_uploads():
    """清理临时上传目录中的残留文件"""
    import glob
    import time
    if not os.path.exists(UPLOAD_DIR):
        return
    now = time.time()
    max_age = 3600
    cleaned = 0
    for filepath in glob.glob(os.path.join(UPLOAD_DIR, "*")):
        try:
            if os.path.isfile(filepath) and (now - os.path.getmtime(filepath)) > max_age:
                os.remove(filepath)
                cleaned += 1
        except Exception:
            pass
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} expired temp upload files")

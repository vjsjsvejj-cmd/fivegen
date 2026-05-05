# -*- coding: utf-8 -*-
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import socketio
import os
import uuid
import asyncio
import contextlib
from typing import Optional
import logging
from socket_manager import SocketManager
from config import Config, UPLOAD_DIR, cleanup_temp_uploads
from tos_service import init_tos_service, get_tos_service
from inversion_service import InversionService
from prompt_helper_service import PromptHelperService
from voice_clone_service import VoiceCloneService
from digital_human_service import DigitalHumanService
from utils.file_naming import (
    format_upload_filename,
    get_display_name,
    get_short_code,
    get_category_from_mime
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# 统一配置第三方库日志级别
logging.getLogger('tos').setLevel(logging.WARNING)
logging.getLogger('tos_client').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)
# 配置项目模块日志级别
logging.getLogger('socket_manager').setLevel(logging.INFO)
logging.getLogger('image_api_service').setLevel(logging.INFO)  # 改为INFO级别，只保留重点日志
logging.getLogger('storage').setLevel(logging.INFO)
logging.getLogger('tos_service').setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def temporary_file(file_path):
    """上下文管理器用于自动清理临时文件"""
    try:
        yield
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"已清理临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

app = FastAPI(title="Five Gen 2.4.5", version="2.4.5")

# 创建静态文件目录
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# LocalStorage/media 目录（用于存储生成的图片和视频）
local_media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LocalStorage", "media")
os.makedirs(local_media_dir, exist_ok=True)

# 挂载静态文件服务
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/local-media", StaticFiles(directory=local_media_dir), name="local-media")

audios_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LocalStorage", "media", "audios")
os.makedirs(audios_dir, exist_ok=True)

def _get_allowed_origins():
    if "*" in Config.ALLOWED_ORIGINS:
        return ["*"]
    origins = list(Config.ALLOWED_ORIGINS)
    import socket
    try:
        local_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in local_ips:
            for port in ["3000", "5173", "5174", "5175"]:
                origin = f"http://{ip}:{port}"
                if origin not in origins:
                    origins.append(origin)
    except socket.gaierror:
        pass
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_socketio_origins():
    if "*" in Config.ALLOWED_ORIGINS:
        return "*"
    origins = list(Config.ALLOWED_ORIGINS)
    import socket
    try:
        local_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in local_ips:
            for port in ["3000", "5173"]:
                origin = f"http://{ip}:{port}"
                if origin not in origins:
                    origins.append(origin)
    except socket.gaierror:
        pass
    return origins

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=_build_socketio_origins(),
    logger=False,
    engineio_logger=False
)

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

socket_manager = SocketManager(sio)
socket_manager.register_events()

cleanup_temp_uploads()

# 初始化 TOS 服务
if Config.is_tos_enabled():
    try:
        init_tos_service(
            access_key=Config.TOS_ACCESS_KEY,
            secret_key=Config.TOS_SECRET_KEY,
            endpoint=Config.TOS_ENDPOINT,
            region=Config.TOS_REGION,
            bucket=Config.TOS_BUCKET
        )
        logger.info("TOS service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize TOS service: {e}")
else:
    logger.warning("TOS service not configured - upload will use local storage")


@app.get("/")
async def root():
    return {"message": "Five Gen 2.4.5 API", "status": "online"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "tos_enabled": Config.is_tos_enabled()
    }


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    index: Optional[int] = Form(None)
):
    """
    上传文件到 TOS（如果配置了）或本地存储
    
    Args:
        file: 上传的文件
        index: 文件在当前上传区的序号（1-based），可选
    
    Returns:
        {
            "success": true,
            "url": "https://...",
            "originalName": "drag-ae5185.mp4",
            "displayName": "视频1.mp4",
            "shortCode": "视频1",
            "content_type": "video/mp4",
            "size": 102400
        }
    """
    temp_path = None
    try:
        original_name = file.filename or "unknown.bin"
        mime_type = file.content_type or "application/octet-stream"
        category = get_category_from_mime(mime_type)
        file_index = index or 1
        new_filename = format_upload_filename(original_name, file_index)
        display_name = get_display_name(category, file_index, original_name)
        short_code = get_short_code(category, file_index)

        temp_path = os.path.join(UPLOAD_DIR, new_filename)

        try:
            with open(temp_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        except IOError as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

        file_size = os.path.getsize(temp_path)

        logger.info(f"File received: {original_name} -&gt; {new_filename} ({file_size} bytes)")

        # 尝试上传到 TOS
        public_url: Optional[str] = None
        if Config.is_tos_enabled():
            tos_service = get_tos_service()
            if tos_service:
                try:
                    public_url = tos_service.upload_file(temp_path, new_filename)
                    logger.info(f"File uploaded to TOS: {public_url}")
                except Exception as e:
                    logger.error(f"TOS upload failed: {e}, falling back to local")

        # 如果 TOS 上传失败或不可用，使用本地存储
        if not public_url:
            import shutil
            local_path = os.path.join(static_dir, new_filename)
            shutil.copy2(temp_path, local_path)
            public_url = f"/static/{new_filename}"
            logger.info(f"File saved locally: {public_url}")

        return JSONResponse({
            "success": True,
            "url": public_url,
            "originalName": original_name,
            "displayName": display_name,
            "shortCode": short_code,
            "content_type": mime_type,
            "size": file_size
        })

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 确保临时文件被清理
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug(f"已清理临时文件: {temp_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")


# 初始化逆向解析服务
inversion_service = InversionService()


@app.post("/api/inversion/analyze")
async def analyze_media(file: UploadFile = File(...), template: Optional[str] = Form(None)):
    """
    上传媒体文件（图片或视频），进行逆向解析
    
    Args:
        file: 上传的图片或视频文件
        template: 可选的自定义提示词模板
    
    Returns:
        包含正向和反向提示词的解析结果
    """
    temp_file_path = None
    try:
        ext = os.path.splitext(file.filename or 'file')[1]
        temp_file_path = os.path.join(UPLOAD_DIR, f"inversion_{uuid.uuid4()}{ext}")

        try:
            with open(temp_file_path, 'wb') as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        except IOError as e:
            raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")
        
        # 判断文件类型
        is_video = file.content_type and file.content_type.startswith('video/')
        
        logger.info(f"Analyzing {'video' if is_video else 'image'} file: {file.filename}")
        
        # 调用逆向解析服务
        result = await asyncio.to_thread(inversion_service.analyze_media, temp_file_path, is_video, template)
        
        return JSONResponse({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Inversion analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")



# ==================== 提示词增强 API ====================
class PromptHelperRequest(BaseModel):
    user_input: str
    action_type: str
    selected_text: str = ""


@app.post("/api/prompt-helper")
async def prompt_helper(request: PromptHelperRequest):
    """
    提示词增强接口：补全/替换/参考
    
    Args:
        request: 请求参数，包含 user_input（用户输入）、
                action_type（操作类型：complete/replace/reference）、
                selected_text（选中文本，替换时必填）
    
    Returns:
        增强后的提示词
    """
    try:
        logger.info(f"提示词增强: {request.action_type}")

        if request.action_type == "complete":
            result = await asyncio.to_thread(PromptHelperService.complete_prompt, request.user_input)
        elif request.action_type == "replace":
            if not request.selected_text:
                raise HTTPException(status_code=400, detail="替换操作必须传入选中的文本")
            result = await asyncio.to_thread(PromptHelperService.replace_prompt, request.user_input, request.selected_text)
        elif request.action_type == "reference":
            result = await asyncio.to_thread(PromptHelperService.get_reference_prompt, request.user_input)
        else:
            raise HTTPException(status_code=400, detail="不支持的操作类型")

        return JSONResponse({
            "success": True,
            "data": result
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提示词增强失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 快捷提示词预设 API ====================
@app.get("/api/quick-presets")
async def get_quick_presets():
    """
    获取快捷提示词预设（镜头、风格、画质、光影、构图、方向、角度、景别、运镜等）
    
    Returns:
        预设分类和预设列表
    """
    presets = {
        "lens": [
            {"name": "标准镜头", "value": "标准镜头, 50mm, 自然视角"},
            {"name": "广角镜头", "value": "广角镜头, 24mm, 广阔视野, 夸张透视"},
            {"name": "长焦镜头", "value": "长焦镜头, 85mm, 压缩空间, 浅景深"},
            {"name": "鱼眼镜头", "value": "鱼眼镜头, 14mm, 极端广角, 圆形畸变"},
            {"name": "移轴镜头", "value": "移轴镜头, 微缩景观, 选择性对焦"},
            {"name": "微距镜头", "value": "微距镜头, 1:1, 超近对焦, 极致细节"},
            {"name": "35mm人文", "value": "35mm人文镜头, 人文视角, 环境交代"},
            {"name": "85mm人像", "value": "85mm人像镜头, 景深虚化, 人像黄金焦段"}
        ],
        "style": [
            {"name": "写实摄影风", "value": "写实摄影风, 高清, 真实细节, 专业摄影"},
            {"name": "皮克斯3D风", "value": "皮克斯3D风, 卡通渲染, 柔和阴影, 精致建模"},
            {"name": "二次元动漫风", "value": "二次元动漫风, 日系动画, 赛璐璐上色, 简洁线条"},
            {"name": "赛博朋克风", "value": "赛博朋克风, 霓虹灯光, 高科技感, 未来都市"},
            {"name": "古典油画风", "value": "古典油画风, 油画质感, 厚重笔触, 经典艺术"},
            {"name": "国风水墨风", "value": "国风水墨风, 水墨晕染, 留白意境, 东方美学"},
            {"name": "蒸汽朋克风", "value": "蒸汽朋克风, 机械复古, 黄铜齿轮, 维多利亚风格"},
            {"name": "极简主义风", "value": "极简主义风, 简洁干净, 几何造型, 高级质感"},
            {"name": "新海诚画风", "value": "新海诚画风, 唯美光影, 细腻天空, 青春氛围"},
            {"name": "吉卜力风格", "value": "吉卜力风格, 宫崎骏, 温暖治愈, 手绘质感"},
            {"name": "波普艺术风", "value": "波普艺术风, 大胆色彩, 重复图案, 流行文化"},
            {"name": "巴洛克风格", "value": "巴洛克风格, 华丽繁复, 动态构图, 戏剧性"}
        ],
        "quality": [
            {"name": "4K超高清", "value": "4K超高清, 8k, ultra HD, 极致细节"},
            {"name": "HDR高动态", "value": "HDR高动态范围, 高对比度, 丰富暗部细节"},
            {"name": "胶片质感", "value": "胶片质感, 柯达胶卷, 暖色调, 颗粒感"},
            {"name": "专业商业", "value": "专业商业摄影, 商业级, 广告大片"},
            {"name": "IMAX级别", "value": "IMAX级别, 巨幕画质, 震撼视效"},
            {"name": "超清8K", "value": "超清8K, 分辨率8192x4320, 像素级细节"},
            {"name": "RAW格式", "value": "RAW格式, 未压缩, 后期空间大"}
        ],
        "lighting": [
            {"name": "正面柔光", "value": "正面柔光, 柔和光线, 无影灯效果"},
            {"name": "侧光质感", "value": "侧光, 质感强烈, 明暗对比"},
            {"name": "逆光轮廓", "value": "逆光, 轮廓光, 金色边缘, 氛围感"},
            {"name": "夜景霓虹", "value": "夜景, 霓虹灯光, 弱光环境, 长曝光"},
            {"name": "自然光", "value": "自然光, 真实阳光, 窗户光, 柔和阴影"},
            {"name": "剧场光影", "value": "剧场光, 聚光, 舞台效果, 戏剧性光影"},
            {"name": "伦勃朗光", "value": "伦勃朗光, 三角形光斑, 经典人像光"},
            {"name": "蝴蝶光", "value": "蝴蝶光, 面部阴影, 时尚人像光"},
            {"name": "环闪", "value": "环形闪光灯, 眼神光, 均匀照明"},
            {"name": "彩光", "value": "彩色光影, RGB灯, 渐变色彩"}
        ],
        "composition": [
            {"name": "三分法构图", "value": "三分法构图, 视觉交点, 主体偏左/偏右"},
            {"name": "居中构图", "value": "居中构图, 对称美, 主体突出"},
            {"name": "低角度仰拍", "value": "低角度仰拍, 视觉冲击, 高大上"},
            {"name": "高角度俯拍", "value": "高角度俯拍, 上帝视角, 全景"},
            {"name": "特写镜头", "value": "特写镜头, 细节突出, 情感聚焦"},
            {"name": "远景全景", "value": "远景全景, 环境交代, 宏大叙事"},
            {"name": "对称构图", "value": "对称构图, 镜像对称, 几何美学"},
            {"name": "对角线构图", "value": "对角线构图, 动感强烈, 引导视线"},
            {"name": "框架构图", "value": "框架构图, 前景框架, 层次感强"}
        ],
        "direction": [
            {"name": "正面朝向", "value": "正面朝向, 直面镜头, 直接互动"},
            {"name": "侧面朝向", "value": "侧面朝向, 90度侧脸, 轮廓展示"},
            {"name": "45度斜角", "value": "45度斜角, 半侧面, 立体感强"},
            {"name": "背面朝向", "value": "背面朝向, 背影, 故事感"},
            {"name": "微微侧头", "value": "微微侧头, 小角度偏转, 自然生动"},
            {"name": "仰面朝向上", "value": "仰头朝上, 仰望视角, 希望感"},
            {"name": "低头朝下", "value": "低头朝下, 俯视, 沉思感"}
        ],
        "angle": [
            {"name": "平视角度", "value": "平视角度, 平等视角, 自然真实"},
            {"name": "俯视角度", "value": "俯视角度, 鸟瞰视角, 全局视野"},
            {"name": "仰视角度", "value": "仰视角度, 英雄视角, 雄伟高大"},
            {"name": "倾斜角度", "value": "倾斜角度, 荷兰角, 动感紧张"},
            {"name": "超俯拍", "value": "超俯拍, 90度垂直, 抽象图案"},
            {"name": "顶视角", "value": "顶视角, 上帝视角, 空间展示"}
        ],
        "shot": [
            {"name": "特写", "value": "特写, 面部/细节, 情感聚焦"},
            {"name": "近景", "value": "近景, 胸部以上, 表情突出"},
            {"name": "中景", "value": "中景, 腰部以上, 动作展示"},
            {"name": "全景", "value": "全景, 全身, 环境关系"},
            {"name": "远景", "value": "远景, 人物渺小, 宏大场景"},
            {"name": "大远景", "value": "大远景, 极致辽阔, 意境深远"},
            {"name": "过肩镜头", "value": "过肩镜头, 肩上视角, 对话场景"}
        ],
        "movement": [
            {"name": "推镜头", "value": "推镜头, 向前推进, 突出主体"},
            {"name": "拉镜头", "value": "拉镜头, 向后拉远, 展示环境"},
            {"name": "摇镜头", "value": "摇镜头, 左右摇摆, 环顾四周"},
            {"name": "移镜头", "value": "移镜头, 平移运动, 跟随主体"},
            {"name": "跟镜头", "value": "跟镜头, 跟随运动, 持续关注"},
            {"name": "环绕镜头", "value": "环绕镜头, 360度环绕, 全方位展示"},
            {"name": "升降镜头", "value": "升降镜头, 上下移动, 揭示空间"},
            {"name": "甩镜头", "value": "甩镜头, 快速运动, 转场过渡"},
            {"name": "稳定器", "value": "稳定器, 稳定平滑, 丝般顺滑"},
            {"name": "无人机航拍", "value": "无人机航拍, 上帝视角, 震撼场面"}
        ],
        "mood": [
            {"name": "治愈系", "value": "治愈系, 温暖柔和, 舒适放松"},
            {"name": "暗黑系", "value": "暗黑系, 压抑神秘, 惊悚氛围"},
            {"name": "梦幻感", "value": "梦幻感, 柔光虚化, 超现实"},
            {"name": "史诗感", "value": "史诗感, 宏大叙事, 震撼心灵"},
            {"name": "怀旧感", "value": "怀旧感, 复古色调, 回忆感"},
            {"name": "未来感", "value": "未来感, 科技前沿, 超现实"},
            {"name": "温馨感", "value": "温馨感, 温暖治愈, 家庭氛围"},
            {"name": "紧张感", "value": "紧张感, 紧凑节奏, 悬疑气氛"}
        ],
        "environment": [
            {"name": "晴天", "value": "晴天, 阳光明媚, 蓝天白云"},
            {"name": "雨天", "value": "雨天, 雨滴地面, 湿反光影"},
            {"name": "雪天", "value": "雪天, 白雪皑皑, 银装素裹"},
            {"name": "雾天", "value": "雾天, 朦胧神秘, 雾气缭绕"},
            {"name": "黄昏", "value": "黄昏, 金色阳光, 温暖色调"},
            {"name": "夜景", "value": "夜景, 城市灯光, 星空闪烁"},
            {"name": "室内", "value": "室内, 居家环境, 生活化"},
            {"name": "郊外", "value": "郊外, 自然风景, 清新空气"},
            {"name": "城市", "value": "城市, 高楼大厦, 繁华都市"}
        ]
    }

    return JSONResponse({"success": True, "data": presets})


# ==================== 声音克隆 API ====================
@app.post("/api/voice-clone/upload-audio")
async def voice_clone_upload_audio(file: UploadFile = File(...)):
    """上传参考音频文件到智谱AI"""
    temp_path = None
    try:
        original_name = file.filename or "audio.wav"
        temp_path = os.path.join(UPLOAD_DIR, f"voice_ref_{uuid.uuid4()}{os.path.splitext(original_name)[1]}")

        file_size = 0
        try:
            with open(temp_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    file_size += len(chunk)
        except IOError as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

        logger.info(f"声音克隆-上传参考音频: {original_name} ({file_size} bytes)")

        result = await asyncio.to_thread(VoiceCloneService.upload_audio_file, temp_path, original_name)

        return JSONResponse({
            "success": True,
            "file_id": result.get("id"),
            "filename": result.get("filename"),
            "bytes": result.get("bytes"),
            "purpose": result.get("purpose")
        })

    except Exception as e:
        logger.error(f"上传参考音频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


class VoiceCloneRequest(BaseModel):
    input_text: str
    file_id: str
    voice_name: str = ""
    reference_text: str = ""


@app.post("/api/voice-clone/generate")
async def voice_clone_generate(request: VoiceCloneRequest):
    """执行声音克隆"""
    try:
        voice_name = request.voice_name or f"voice_{uuid.uuid4().hex[:8]}"
        request_id = f"vc_{uuid.uuid4().hex[:12]}"

        logger.info(f"声音克隆请求: voice_name={voice_name}, file_id={request.file_id}")

        result = await VoiceCloneService.clone_voice(
            voice_name=voice_name,
            input_text=request.input_text,
            file_id=request.file_id,
            reference_text=request.reference_text,
            request_id=request_id
        )

        audio_data = result.get("audio_url")
        if audio_data:
            audio_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LocalStorage", "media", "audios")
            os.makedirs(audio_dir, exist_ok=True)
            audio_filename = f"voice_{uuid.uuid4().hex[:8]}.wav"
            audio_path = os.path.join(audio_dir, audio_filename)
            VoiceCloneService.download_audio(audio_data, audio_path)
            audio_url = f"/local-media/audios/{audio_filename}"
        else:
            audio_url = None

        return JSONResponse({
            "success": True,
            "audio_url": audio_url,
            "voice": result.get("voice"),
            "file_id": result.get("file_id"),
            "request_id": result.get("request_id")
        })

    except Exception as e:
        logger.error(f"声音克隆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 数字人 API ====================
@app.post("/api/digital-human/upload-image")
async def digital_human_upload_image(file: UploadFile = File(...)):
    """上传数字人图片"""
    temp_path = None
    try:
        original_name = file.filename or "image.jpg"
        ext = os.path.splitext(original_name)[1]
        temp_path = os.path.join(UPLOAD_DIR, f"dh_img_{uuid.uuid4()}{ext}")

        file_size = 0
        try:
            with open(temp_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    file_size += len(chunk)
        except IOError as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

        logger.info(f"数字人-上传图片: {original_name} ({file_size} bytes)")

        public_url = None
        if Config.is_tos_enabled():
            tos_service = get_tos_service()
            if tos_service:
                try:
                    new_filename = format_upload_filename(original_name, 1)
                    public_url = tos_service.upload_file(temp_path, new_filename)
                except Exception as e:
                    logger.warning(f"TOS上传失败: {e}")

        if not public_url:
            import shutil
            static_dir = os.path.join(os.path.dirname(__file__), "static")
            new_filename = format_upload_filename(original_name, 1)
            local_path = os.path.join(static_dir, new_filename)
            shutil.copy2(temp_path, local_path)
            public_url = f"/static/{new_filename}"

        return JSONResponse({
            "success": True,
            "url": public_url,
            "originalName": original_name,
            "size": file_size
        })

    except Exception as e:
        logger.error(f"上传数字人图片失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/api/digital-human/upload-audio")
async def digital_human_upload_audio(file: UploadFile = File(...)):
    """上传数字人音频"""
    temp_path = None
    try:
        original_name = file.filename or "audio.wav"
        ext = os.path.splitext(original_name)[1]
        temp_path = os.path.join(UPLOAD_DIR, f"dh_aud_{uuid.uuid4()}{ext}")

        file_size = 0
        try:
            with open(temp_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    file_size += len(chunk)
        except IOError as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"文件写入失败: {e}")

        logger.info(f"数字人-上传音频: {original_name} ({file_size} bytes)")

        public_url = None
        if Config.is_tos_enabled():
            tos_service = get_tos_service()
            if tos_service:
                try:
                    new_filename = format_upload_filename(original_name, 1)
                    public_url = tos_service.upload_file(temp_path, new_filename)
                except Exception as e:
                    logger.warning(f"TOS上传失败: {e}")

        if not public_url:
            import shutil
            static_dir = os.path.join(os.path.dirname(__file__), "static")
            new_filename = format_upload_filename(original_name, 1)
            local_path = os.path.join(static_dir, new_filename)
            shutil.copy2(temp_path, local_path)
            public_url = f"/static/{new_filename}"

        return JSONResponse({
            "success": True,
            "url": public_url,
            "originalName": original_name,
            "size": file_size
        })

    except Exception as e:
        logger.error(f"上传数字人音频失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


class DigitalHumanRequest(BaseModel):
    image_url: str
    audio_url: str


@app.post("/api/digital-human/generate")
async def digital_human_generate(request: DigitalHumanRequest):
    """执行数字人生成"""
    try:
        if not DigitalHumanService.is_configured():
            return JSONResponse({
                "success": False,
                "error": "数字人API未配置，请在.env中设置DIGITAL_HUMAN_API_KEY、DIGITAL_HUMAN_BASE_URL、DIGITAL_HUMAN_MODEL"
            }, status_code=503)

        logger.info(f"数字人生成请求: image={request.image_url[:50]}..., audio={request.audio_url[:50]}...")

        result = await DigitalHumanService.create_digital_human(
            image_url=request.image_url,
            audio_url=request.audio_url
        )

        video_url = result.get("video_url")

        if video_url and video_url.startswith("http"):
            try:
                video_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LocalStorage", "media", "videos")
                os.makedirs(video_dir, exist_ok=True)
                video_filename = f"dh_{uuid.uuid4().hex[:8]}.mp4"
                video_path = os.path.join(video_dir, video_filename)

                def _stream_download(url, path, timeout):
                    resp = requests.get(url, timeout=timeout, stream=True)
                    resp.raise_for_status()
                    with open(path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                await asyncio.to_thread(_stream_download, video_url, video_path, Config.VIDEO_DOWNLOAD_TIMEOUT)

                video_url = f"/local-media/videos/{video_filename}"
                logger.info(f"数字人视频已保存: {video_url}")
            except Exception as e:
                logger.warning(f"下载数字人视频失败: {e}")

        return JSONResponse({
            "success": True,
            "video_url": video_url
        })

    except Exception as e:
        logger.error(f"数字人生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)

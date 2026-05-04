# -*- coding: utf-8 -*-
import os
import requests
import base64
import logging
from config import Config
import json
from typing import Optional

logger = logging.getLogger(__name__)

# 逆向解析的提示词模板
INVERSION_PROMPT_TEMPLATE = """# 角色定位
你是专为Seedance 2.0模型服务的顶级文生图/文生视频提示词逆向工程师，唯一任务是：解析用户上传的图片/视频，输出可直接在Seedance 2.0中生成高度匹配内容的完整中文提示词，严格遵守所有规则，禁止任何偏离任务的输出。

# 核心拆解规则（必须全覆盖，无遗漏）
## 图片/视频通用规则
1. 核心主体：精准拆解核心对象、物种/人物特征、五官细节、姿态动作、表情神态、服饰穿搭、道具细节、毛发/皮肤/材质纹理，精准到可复现的颗粒度
2. 场景环境：完整描述背景环境、空间透视关系、场景层次、前后景关系、环境氛围、天气状态、时间时段、光线环境
3. 风格画质：精准定义艺术风格、所属AI模型流派、渲染器类型、画质等级、分辨率标准、画面精度、抗锯齿、细节丰富度
4. 光影色彩：精准拆解主光类型、辅光方向、光影硬度、光影氛围、画面主色调、配色体系、色彩饱和度、对比度、色偏风格
5. 构图镜头：精准描述画面构图方式、镜头焦段、拍摄视角、画面比例、景深效果、焦点位置、画面留白

## 视频专属补充规则（上传视频时必须执行）
1. 必须拆解视频的核心动作变化、时序逻辑、关键分镜要点、主体运动轨迹
2. 必须补充完整的运镜方式、镜头运动逻辑、镜头切换节奏、画面衔接方式
3. 必须给出适配Seedance 2.0的推荐时长、帧率、关键帧间隔参数
4. 输出的提示词必须是连贯的、可直接生成对应完整视频的内容，禁止碎片化描述

# 输出强制规范（100%严格执行，禁止任何修改）
1. 必须严格分为【正向提示词】【反向提示词】两个独立模块，禁止新增其他模块，禁止任何解释性、说明性文字
2. 正向提示词：
    - 必须使用Seedance 2.0适配的中文逗号分隔的关键词格式，按「核心主体>场景环境>风格画质>光影色彩>构图镜头>视频专属参数」的权重优先级排序，核心主体关键词放在最前
    - 优先使用中文，仅补充Seedance 2.0识别度更高的必要英文专业术语，禁止纯英文输出
    - 必须贴合Seedance 2.0的关键词偏好，使用该模型高响应度的画质、风格、光影、运镜关键词，禁止生僻词、无效词
3. 反向提示词：
    - 固定包含基础负面词：低画质，模糊，失焦，畸形，五官崩坏，肢体残缺，画面杂乱，逻辑混乱，水印，文字，签名，画面卡顿，动作不连贯，跳帧
    - 额外补充针对当前内容的专属负面词，排除与画面/视频不符的元素、风格、缺陷
4. 禁止输出任何规则解读、分析说明、客套话，仅输出两个模块的提示词内容"""


class InversionService:
    def __init__(self):
        self.api_key = Config.INVERSION_API_KEY
        self.model = Config.INVERSION_MODEL
        self.base_url = Config.INVERSION_BASE_URL
        logger.info(f"InversionService initialized with model: {self.model}")
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """将图片文件编码为base64"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _call_ark_api(self, image_base64: str, is_video: bool = False, custom_template: Optional[str] = None) -> str:
        """调用火山引擎Ark API进行逆向解析"""
        url = f"{self.base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 选择使用的模板
        template = custom_template if custom_template else INVERSION_PROMPT_TEMPLATE
        
        # 构建请求体
        content = [
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{image_base64}"
            },
            {
                "type": "input_text",
                "text": template
            }
        ]
        
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }
        
        try:
            logger.info("Calling Ark API for inversion...")
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            logger.info(f"API response status: {response.status_code}")
            
            result = response.json()
            logger.info("Received API response")
            
            response.raise_for_status()
            
            # 解析API返回结果 - 最安全的方式
            extracted_text = None
            
            # 方式1: 查找 type 为 "message" 的 output 项
            if "output" in result and isinstance(result["output"], list):
                for output_item in result["output"]:
                    if isinstance(output_item, dict) and output_item.get("type") == "message":
                        content_list = output_item.get("content", [])
                        if isinstance(content_list, list):
                            for content_item in content_list:
                                if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                    text_val = content_item.get("text")
                                    if text_val and isinstance(text_val, str):
                                        extracted_text = text_val
                                        logger.info("Found text in message output")
                                        break
                        if extracted_text:
                            break
            
            # 方式2: 如果方式1没找到，尝试查找 reasoning 的 summary
            if not extracted_text and "output" in result and isinstance(result["output"], list):
                for output_item in result["output"]:
                    if isinstance(output_item, dict) and output_item.get("type") == "reasoning":
                        summary_list = output_item.get("summary", [])
                        if isinstance(summary_list, list):
                            for summary_item in summary_list:
                                if isinstance(summary_item, dict) and summary_item.get("type") == "summary_text":
                                    text_val = summary_item.get("text")
                                    if text_val and isinstance(text_val, str):
                                        extracted_text = text_val
                                        logger.info("Found text in reasoning summary")
                                        break
                        if extracted_text:
                            break
            
            # 方式3: 备用解析方式
            if not extracted_text and "choices" in result and isinstance(result["choices"], list):
                if len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if isinstance(choice, dict):
                        if "message" in choice and isinstance(choice["message"], dict):
                            msg_content = choice["message"].get("content")
                            if msg_content and isinstance(msg_content, str):
                                extracted_text = msg_content
                        elif "text" in choice and isinstance(choice["text"], str):
                            extracted_text = choice["text"]
            
            # 方式4: 最后尝试，返回整个响应
            if not extracted_text:
                logger.warning("Could not extract text from response, returning raw JSON")
                extracted_text = json.dumps(result, ensure_ascii=False)
            
            return extracted_text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"API调用失败: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}", exc_info=True)
            raise
    
    def _parse_result(self, raw_text: str) -> dict:
        """解析API返回的原始文本，提取正向和反向提示词"""
        positive = ""
        negative = ""
        
        try:
            # 简单的解析逻辑
            lines = raw_text.split("\n")
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if "正向提示词" in line or "【正向提示词】" in line:
                    current_section = "positive"
                    continue
                elif "反向提示词" in line or "【反向提示词】" in line:
                    current_section = "negative"
                    continue
                
                if current_section == "positive":
                    positive += line + " "
                elif current_section == "negative":
                    negative += line + " "
            
            # 清理
            positive = positive.strip()
            negative = negative.strip()
            
            # 如果解析失败，返回原始文本作为正向提示词
            if not positive:
                positive = raw_text
        except Exception as e:
            logger.error(f"Error parsing result: {e}")
            positive = raw_text
        
        return {
            "positive": positive,
            "negative": negative,
            "raw": raw_text
        }
    
    def analyze_media(self, file_path: str, is_video: bool = False, custom_template: Optional[str] = None) -> dict:
        """分析媒体文件（图片或视频），返回解析的提示词"""
        try:
            logger.info(f"Starting media analysis: {file_path}")
            
            # 将文件编码为base64
            base64_data = self._encode_image_to_base64(file_path)
            
            # 调用API
            raw_result = self._call_ark_api(base64_data, is_video=is_video, custom_template=custom_template)
            
            # 解析结果
            parsed_result = self._parse_result(raw_result)
            
            logger.info("Media analysis completed successfully")
            return parsed_result
            
        except Exception as e:
            logger.error(f"Media analysis failed: {e}")
            raise

# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词增强服务 - 基于 Doubao-Seed-2.0-lite
"""
import os
import requests
import json
import logging
import re
from config import Config

logger = logging.getLogger(__name__)

# 配置 - 使用和逆向解析相同的配置
API_KEY = Config.INVERSION_API_KEY
BASE_URL = Config.INVERSION_BASE_URL
MODEL_ID = Config.INVERSION_MODEL


# 系统提示词
SYSTEM_PROMPTS = {
    "complete": """
    # 角色定位
你是专为Seedance 2.0设计的**扩写续写专家**，核心任务：在用户输入提示词后，通过**补全缺失维度、扩展细节、完善逻辑**，输出3-5套可直接粘贴的续写内容，确保生成结果更精准、画面更完整，同时**不改变用户原文的任何内容**。

# 核心规则
1. **原文零修改**：用户输入内容一字不动，仅在后端续写补充。
2. **维度全覆盖**：
   - **正向补全**：根据用户主题，补充环境、光影、色彩、画质、镜头、细节、特效、叙事等缺失维度。
   - **反向补全**：添加通用负面词（如模糊、畸变）及场景专属负面词（视频卡顿、穿模等）。
3. **场景智能适配**：
   - **图文场景**：侧重光影层次、构图（如三分法、黄金螺旋）、画质参数（8K/Cinematic）。
   - **视频场景**：补充动作时序、镜头运动（如斯坦尼康滑移）、帧率（60FPS）、转场效果。
4. **续写逻辑**：
   - **主题延续**：所有续写内容必须与用户原文主题、风格、核心元素完全一致。
   - **细节递进**：从宏观到微观，逐步细化描述（如从“森林”到“雾气缭绕的橡木林，苔藓覆盖的树根”）。
5. **输出格式**：
```markdown
用户原文：[用户输入内容]
续写内容：
1. 版本一：[用户原文], 补全维度1, 补全维度2, ..., 反向词1, 反向词2
2. 版本二：[用户原文], ...
...

6. 输出要求：
○ 3-5套差异化续写方案，避免重复维度。
○ 中文逗号分隔，符合Seedance 2.0语法。
示例
用户原文：赛博朋克街道，霓虹灯
续写内容：
1. 版本一：赛博朋克街道, 霓虹灯, 全息投影广告, 酸雨特效, 未来主义建筑, 8K画质, --模糊--逻辑错误
2. 版本二：赛博朋克街道, 霓虹灯, 雨夜氛围, 反光积水, 无人机掠过镜头, 120FPS慢动作, --过曝--画面撕裂

    """,



    "replace": """
    # 角色定位
你是专为Seedance 2.0设计的**局部修改专家**，核心任务：根据用户选中的待替换关键词，结合上下文语义，输出3-5组**精准替换方案**，确保替换后的提示词逻辑连贯、风格统一、生成效果提升，同时**保持原文其余内容不变**。

# 核心规则
1. **精准替换**：仅修改用户选中的关键词，其他内容原样保留。
2. **语义一致性**：
   - 替换词必须与原文主题、风格、元素权重完全匹配（如“古风”→“宋代庭院”，而非“赛博朋克”）。
3. **替换策略**：
   - **同义升级**：用更精准或高阶术语替换（如“夕阳”→“赤金暮色，丁达尔效应”）。
   - **维度扩展**：替换为包含更多细节的短语（如“山脉”→“雪山之巅，云雾缭绕的峭壁”）。
   - **风格强化**：贴合原文基调增强表现力（如“现代”→“极简主义几何建筑”）。
4. **输出格式**：
```markdown
选中替换词：[用户选中的词]
替换方案：
1. 精准优化版：[替换词1], [替换词2]
2. 细节增强版：[替换组]
3. 创意拓展版：[替换组]
...

5. 替换要求：
○ 每组3-5个替换选项，覆盖不同优化方向。
○ 替换词长度、权重层级与原文匹配（单词语替换单词，短语替换短语）。
○ 禁用其他模型语法（如SD的权重标记）。
示例
用户原文：中世纪城堡，夕阳，石墙
选中替换词：夕阳
替换方案：
1. 精准优化版：赤金暮色, 火烧云霞
2. 氛围增强版：日落余晖，耶稣光穿透云层
3. 诗意表达版：琥珀色天穹，天际线熔金





    """,





    "reference": """
    # 角色定位
你是专为Seedance 2.0设计的**润色优化专家**，核心任务：基于用户提供的完整提示词，通过**词汇升级、结构优化、细节深化、权重强化**等手段，在不改变主题、风格、核心元素的前提下，输出3-5套大神级润色模板，显著提升生成效果，直接用于生产。

# 核心规则
1. **主题与风格守恒**：100%保留用户原文的主题、核心元素及风格基调，不新增无关内容。
2. **润色四维度深度执行**：
   - **词汇升级**：将基础词汇替换为更精准、更具表现力的专业术语（如「湖面」→「克莱因蓝镜面水域」）。
   - **维度补全**：补充用户未提及的关键维度（如光影层次、构图技法、镜头语言、画质参数），填补生成短板。
   - **权重优化**：调整关键词顺序，确保核心元素优先（如主体>环境>光影>细节），符合Seedance 2.0解析逻辑。
   - **语法规范**：严格遵循官方格式（中文逗号分隔，无权重符号或模型专属标记）。
3. **润色策略**：
   - **正向提示词**：
     - 精细化描述：融合多感官词（如「雾气缭绕的橡木林，苔藓湿润的触感」）。
     - 比喻与修辞：增强画面感染力（如「水墨晕染般的云雾」）。
   - **反向提示词**：
     - 补充场景专属负面词（如视频的「动作卡顿、帧率不足」，图文的「噪点过多、构图失衡」）。
     - 强化约束条件，提升生成稳定性。
4. **差异化润色方向（3-5套）**：
   - 精致写实版：强化材质与光影细节，适配超高清渲染。
   - 氛围电影版：侧重镜头运动（如「斯坦尼康滑移」）、叙事节奏（如「蒙太奇剪辑感」）。
   - 极简美学版：精简冗余词，突出核心构图与色彩冲击力（如「黄金分割构图，莫兰迪色系」）。
   - 动态增强版（视频）：补充动作时序、帧率（如「120FPS慢动作」）、转场特效。
   - 艺术解构版：融合实验性元素（如「低多边形风格、故障艺术噪波」）。
5. **用户意图解码**：
   - 将模糊描述转化为AI可解析的精准指令（如「古风」→「明代工笔画风，绢本设色纹理」）。

# 输出格式
```markdown
【润色版本X】
用户原文：[用户原始提示词]
【正向提示词】润色后核心元素 + 增强维度（中文逗号分隔）
【反向提示词】润色后反向词 + 补充负面词

示例输出
用户原文：科幻城市，霓虹，未来感
【润色版本1】
【正向提示词】科幻城市, 霓虹灯矩阵, 全息投影广告牌, 赛博雨特效, 反重力悬浮建筑, 8K超现实画质, 广角镜头俯拍
【反向提示词】模糊失焦, 逻辑错误, 画面撕裂, 色彩溢出

    """
}


class PromptHelperService:
    """提示词增强服务"""

    @staticmethod
    def _call_doubao_api(system_prompt: str, user_prompt: str):
        """调用 Doubao API"""
        logger.info(f"调用 Doubao API，模型: {MODEL_ID}")

        url = f"{BASE_URL}/responses"

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        content = [
            {
                "type": "input_text",
                "text": f"{system_prompt}\n\n{user_prompt}"
            }
        ]

        payload = {
            "model": MODEL_ID,
            "input": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }

        try:
            logger.info("Calling Ark API...")
            logger.info(f"=== API 请求原始数据 ===")
            logger.info(f"请求URL: {url}")
            logger.info(f"请求模型: {MODEL_ID}")
            logger.info(f"请求系统提示词: {system_prompt[:200]}...")
            logger.info(f"请求用户输入: {user_prompt}")
            logger.info(f"完整请求Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            logger.info(f"========================")

            response = requests.post(url, headers=headers, json=payload, timeout=120)
            logger.info(f"API响应状态码: {response.status_code}")

            result = response.json()

            logger.info(f"=== API 响应原始数据 ===")
            logger.info(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            logger.info(f"======================")
            
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

    @staticmethod
    def _parse_complete_result(raw_text: str, user_input: str):
        """解析 complete 的结果，返回3-5组续写"""
        logger.info(f"=== 开始解析 complete 结果 ===")
        logger.info(f"原始文本: {raw_text[:200]}...")
        options = []
        
        # 方式1: 根据【】分隔符解析
        parts = re.split(r'【[^】]*】', raw_text)
        for part in parts:
            part = part.strip()
            if part and len(part) > 10:
                # 清理一下内容
                part = re.sub(r'^\d+[.\s]', '', part).strip()
                part = re.sub(r'^版本[一二三四五六七八九十\d]+[：:\s]*', '', part).strip()
                if part:
                    # 如果不以用户输入开头，就加上
                    if not part.startswith(user_input):
                        part = f"{user_input}, {part}"
                    if part not in options:
                        options.append(part)
                        logger.info(f"找到选项(1): {part[:60]}...")
        
        # 方式2: 按行解析
        if len(options) < 2:
            lines = raw_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and not line.startswith('用户') and not line.startswith('提示词'):
                    # 清理一下
                    clean_line = re.sub(r'^\d+[.\s]', '', line).strip()
                    clean_line = re.sub(r'^版本[^：:]*[：:\s]*', '', clean_line).strip()
                    if clean_line and len(clean_line) > 10:
                        if not clean_line.startswith(user_input):
                            clean_line = f"{user_input}, {clean_line}"
                        if clean_line not in options:
                            options.append(clean_line)
                            logger.info(f"找到选项(2): {clean_line[:60]}...")
        
        # 方式3: 兜底
        if not options:
            if not raw_text.startswith(user_input):
                options = [f"{user_input}, {raw_text[:300]}"]
            else:
                options = [raw_text[:300]]
            logger.info(f"使用兜底选项")
        
        logger.info(f"=== 解析完成，共 {len(options)} 个选项 ===")
        return options[:5]

    @staticmethod
    def _parse_replace_result(raw_text: str):
        """解析 replace 的结果，返回3-5组替换词"""
        logger.info(f"=== 开始解析 replace 结果 ===")
        logger.info(f"原始文本: {raw_text[:200]}...")
        options = []
        
        # 方式1: 根据【】分隔符解析
        parts = re.split(r'【[^】]*】', raw_text)
        for part in parts:
            part = part.strip()
            if part and len(part) > 5:
                clean_part = re.sub(r'^\d+[.\s]', '', part).strip()
                clean_part = re.sub(r'^版本[^：:]*[：:\s]*', '', clean_part).strip()
                clean_part = re.sub(r'^[^：:]+[：:]\s*', '', clean_part).strip()
                if clean_part and clean_part not in options:
                    options.append(clean_part)
                    logger.info(f"找到选项(1): {clean_part[:60]}...")
        
        # 方式2: 按行解析
        if len(options) < 2:
            lines = raw_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 5 and not line.startswith(('选中', '替换', '用户', '上下文', '待替换')):
                    clean_line = re.sub(r'^\d+[.\s]', '', line).strip()
                    clean_line = re.sub(r'^版本[^：:]*[：:\s]*', '', clean_line).strip()
                    clean_line = re.sub(r'^[^：:]+[：:]\s*', '', clean_line).strip()
                    if clean_line and len(clean_line) > 5 and clean_line not in options:
                        options.append(clean_line)
                        logger.info(f"找到选项(2): {clean_line[:60]}...")
        
        # 方式3: 兜底
        if not options:
            options = [raw_text[:300]]
            logger.info(f"使用兜底选项")
        
        logger.info(f"=== 解析完成，共 {len(options)} 个选项 ===")
        return options[:5]

    @staticmethod
    def _parse_reference_result(raw_text: str):
        """解析 reference 的结果，返回3-5组完整提示词"""
        logger.info(f"=== 开始解析 reference 结果 ===")
        logger.info(f"原始文本: {raw_text[:300]}...")
        options = []
        
        # 方式1: 根据【】分隔符解析，提取【】后面的内容
        # 使用正则分割【】，但不要丢掉【】本身
        # 先把【】标签替换为分隔符，然后分割
        # 或者直接按【来分割，然后取后面的部分
        if '【' in raw_text:
            # 按【分割，第一块是前面的内容，后面的是每个选项
            segments = raw_text.split('【')
            for seg in segments[1:]:  # 跳过第一个（前面的内容）
                if '】' in seg:
                    # 找到第一个】，后面是内容
                    end_idx = seg.find('】')
                    content = seg[end_idx + 1:].strip()
                    if content and len(content) > 10:
                        # 清理内容
                        content = re.sub(r'^\s*[:：]\s*', '', content).strip()
                        if content and content not in options:
                            options.append(content)
                            logger.info(f"找到选项(1): {content[:80]}...")
        
        # 方式2: 如果上面没找到，按【】分隔符
        if len(options) < 2:
            parts = re.split(r'【[^】]*】', raw_text)
            for part in parts:
                part = part.strip()
                if part and len(part) > 10:
                    # 清理
                    clean_part = re.sub(r'^\s*\n\s*', '', part).strip()
                    clean_part = re.sub(r'^\d+[.\s]', '', clean_part).strip()
                    clean_part = re.sub(r'^版本[^：:]*[：:\s]*', '', clean_part).strip()
                    if clean_part and clean_part not in options:
                        options.append(clean_part)
                        logger.info(f"找到选项(2): {clean_part[:80]}...")
        
        # 方式3: 按空行分割
        if len(options) < 2:
            blocks = re.split(r'\n\s*\n', raw_text)
            for block in blocks:
                block = block.strip()
                if block and len(block) > 20:
                    # 去掉开头的【】标签
                    clean_block = re.sub(r'^【[^】]*】', '', block).strip()
                    clean_block = re.sub(r'^\d+[.\s]', '', clean_block).strip()
                    clean_block = re.sub(r'^版本[^：:]*[：:\s]*', '', clean_block).strip()
                    if clean_block and len(clean_block) > 10 and clean_block not in options:
                        options.append(clean_block)
                        logger.info(f"找到选项(3): {clean_block[:80]}...")
        
        # 方式4: 兜底
        if not options:
            # 清理掉【】标签
            clean_text = re.sub(r'【[^】]*】', '', raw_text).strip()
            # 按换行分割，取第一块
            lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
            if lines:
                options = [' '.join(lines)[:300]]
            else:
                options = [raw_text[:300]]
            logger.info(f"使用兜底选项")
        
        logger.info(f"=== 解析完成，共 {len(options)} 个选项 ===")
        for i, opt in enumerate(options):
            logger.info(f"选项 {i+1}: {opt[:100]}...")
        return options[:5]

    @staticmethod
    def complete_prompt(user_input: str):
        """提示词补全/续写"""
        logger.info(f"开始提示词补全: {user_input[:50]}...")

        system_prompt = SYSTEM_PROMPTS["complete"]
        raw_result = PromptHelperService._call_doubao_api(system_prompt, user_input)
        
        # 解析结果
        options = PromptHelperService._parse_complete_result(raw_result, user_input)
        
        return {
            "raw": raw_result,
            "options": options,
            "type": "complete"
        }

    @staticmethod
    def replace_prompt(user_input: str, selected_text: str):
        """提示词定向替换"""
        logger.info(f"开始提示词替换: {selected_text[:50]}...")

        system_prompt = SYSTEM_PROMPTS["replace"]
        user_content = f"上下文完整提示词：{user_input}\n待替换的文本：{selected_text}\n请输出替换方案"
        raw_result = PromptHelperService._call_doubao_api(system_prompt, user_content)
        
        # 解析结果
        options = PromptHelperService._parse_replace_result(raw_result)
        
        return {
            "raw": raw_result,
            "options": options,
            "type": "replace",
            "selected_text": selected_text
        }

    @staticmethod
    def get_reference_prompt(theme: str):
        """获取大神提示词参考"""
        logger.info(f"开始获取大神提示词: {theme[:50]}...")

        system_prompt = SYSTEM_PROMPTS["reference"]
        raw_result = PromptHelperService._call_doubao_api(system_prompt, theme)
        
        # 解析结果
        options = PromptHelperService._parse_reference_result(raw_result)
        
        return {
            "raw": raw_result,
            "options": options,
            "type": "reference"
        }

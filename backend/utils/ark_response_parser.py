# -*- coding: utf-8 -*-
import json
import logging

logger = logging.getLogger(__name__)


def extract_text_from_ark_response(result: dict) -> str:
    """从火山引擎 Ark API 响应中提取文本内容
    
    支持4种响应格式的解析：
    1. output[].type == "message" -> content[].type == "output_text"
    2. output[].type == "reasoning" -> summary[].type == "summary_text"
    3. choices[].message.content
    4. 兜底：返回原始 JSON
    """
    extracted_text = None

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

    if not extracted_text:
        logger.warning("Could not extract text from response, returning raw JSON")
        extracted_text = json.dumps(result, ensure_ascii=False)

    return extracted_text

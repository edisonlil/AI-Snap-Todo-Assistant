"""ResultParser：解析 AI 返回文本，保留原始格式"""
from __future__ import annotations

import json
import re


class ResultParser:
    @staticmethod
    def parse(text: str) -> str:
        """
        解析 AI 返回文本，保留原始内容
        支持：
        - 标准 JSON（会提取 JSON 部分）
        - markdown 代码块包裹的 JSON（```json ... ```）
        - 纯文本
        
        返回清洁后的原始内容（去除 markdown 包装）
        """
        raw = text.strip()

        # 去除 markdown 代码块，但保留内容
        md_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if md_match:
            raw = md_match.group(1).strip()

        return raw

"""Optional DeepSeek wording layer; notice facts are rendered by notice_engine."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
from openai import OpenAI

from notice_engine import Answer, MISSING


def api_configured() -> bool:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    return bool(key and key != "your_api_key_here")


def summarize_with_deepseek(answer: Answer, question: str, client: Any | None = None) -> tuple[str | None, str | None]:
    """Return a grounded summary or a clearly labelled general-knowledge answer."""
    if not api_configured() and client is None:
        return None, "未配置 DeepSeek API Key，当前使用本地演示模式。"
    needs_general_answer = answer.kind == "none" or MISSING in answer.text
    http_client = None
    try:
        if client is None:
            # Ignore unrelated system proxy settings. In particular, a SOCKS proxy
            # makes httpx require an optional dependency that this project does not use.
            http_client = httpx.Client(trust_env=False)
            client = OpenAI(
                api_key=os.environ["DEEPSEEK_API_KEY"].strip(),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
                timeout=20.0,
                max_retries=0,
                http_client=http_client,
            )
        result = client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat",
            messages=[
                {"role": "system", "content": (
                    "你是校园演示通知的中文问答助手。已核验内容是校园通知事实的唯一来源。"
                    "如果资料已回答问题，只写一句不超过70字的自然语言摘要，不得增加通知事实、日期、数字、地点、费用、网址、来源编号或材料名称。"
                    "如果资料未说明用户所问的信息，或没有找到相关资料，必须先明确写‘资料库暂无相关信息。’，"
                    "然后用不超过180字基于一般知识直接回答；这部分不得编造学校、活动或组织方的具体事实，也不得把推测说成通知内容。"
                    "对于实时信息或无法确定的事实，应说明无法确认并建议查询可靠来源。不得声称这些模拟通知是学校真实公告。"
                )},
                {"role": "user", "content": (
                    f"回答模式：{'资料不足，可补充一般知识' if needs_general_answer else '仅摘要已核验内容'}\n"
                    f"问题：{question}\n已核验回答：{answer.text}\n缺失说明：{MISSING}"
                )},
            ],
            temperature=0.1,
            max_tokens=300 if needs_general_answer else 120,
        )
        summary = (result.choices[0].message.content or "").strip()
        max_length = 240 if needs_general_answer else 100
        if not summary or len(summary) > max_length:
            return None, "AI 摘要未通过事实约束检查，已展示本地核验结果。"
        if needs_general_answer:
            if not summary.startswith("资料库暂无相关信息"):
                return None, "AI 补充回答未明确标注资料库缺失，已展示本地核验结果。"
        elif re.search(r"\d|https?://|www\.|[¥￥元]", summary):
            return None, "AI 摘要未通过事实约束检查，已展示本地核验结果。"
        return summary, None
    except Exception as exc:
        # A short, non-sensitive exception type helps troubleshoot without exposing keys.
        return None, f"DeepSeek 请求失败（{type(exc).__name__}），已自动使用本地演示结果。"
    finally:
        if http_client is not None:
            http_client.close()

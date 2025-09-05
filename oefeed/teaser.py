from __future__ import annotations

import os
import requests

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8080")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3-30B-A3B-Instruct")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-local")


PROMPT_TEMPLATE = (
    "You are a concise tech news editor. Given an article, write a 2-3 sentence teaser (max 60 words) that captures the key point and why it matters. Avoid hype and avoid repeating the title. Output plain text."
)


def generate_teaser(article_text: str, title: str | None = None) -> str | None:
    try:
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": PROMPT_TEMPLATE},
                {"role": "user", "content": (f"Title: {title}\n\n" if title else "") + article_text[:6000]},
            ],
            "temperature": 0.4,
            "max_tokens": 160,
        }
        headers = {
            "Content-Type": "application/json"
        }
        r = requests.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[WARN] Generation of teaser failed! {e}")
        return None


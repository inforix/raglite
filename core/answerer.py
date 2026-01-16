import logging
from typing import Iterable, Optional

import requests

from app.settings_service import get_app_settings_db, get_model_config_by_name
from infra import models
from infra.db import SessionLocal

logger = logging.getLogger(__name__)

MAX_SOURCES = 4
MAX_SOURCE_CHARS = 1200


def _resolve_chat_config(model_name: Optional[str]) -> Optional[models.ModelConfig]:
    db = SessionLocal()
    try:
        app_settings = get_app_settings_db(db)
        target = model_name or app_settings.default_chat_model
        return get_model_config_by_name(db, models.ModelType.chat, target)
    finally:
        db.close()


def _trim_text(text: str, limit: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    trimmed = cleaned[:limit].rstrip()
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    return f"{trimmed}..."


def _build_messages(question: str, results: Iterable[dict]) -> list[dict]:
    sources: list[str] = []
    for idx, hit in enumerate(results):
        if idx >= MAX_SOURCES:
            break
        text = _trim_text(str(hit.get("text", "")), MAX_SOURCE_CHARS)
        if not text:
            continue
        sources.append(f"[{idx + 1}] {text}")

    context = "\n\n".join(sources)
    if not context:
        return []

    system = "You are a helpful assistant for question answering."
    user = (
        "Answer the question using only the sources below. "
        "If the sources do not contain the answer, say you do not know. "
        "Keep the answer concise and in the same language as the question.\n\n"
        f"Question: {question}\n\nSources:\n{context}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _chat_openai_compatible(messages: list[dict], cfg: models.ModelConfig) -> str:
    url = f"{cfg.endpoint.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    payload = {"model": cfg.model, "messages": messages}
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content:
        return str(content).strip()
    return str(choices[0].get("text", "")).strip()


def generate_answer(question: str, results: Iterable[dict], model_name: Optional[str] = None) -> Optional[str]:
    if not question or not results:
        return None

    cfg = _resolve_chat_config(model_name)
    if not cfg or not cfg.endpoint:
        logger.info("Chat model is not configured; skipping answer generation.")
        return None

    messages = _build_messages(question, results)
    if not messages:
        return None

    try:
        answer = _chat_openai_compatible(messages, cfg)
    except Exception as exc:
        logger.warning("Chat model failed: %s", exc)
        return None

    return answer or None

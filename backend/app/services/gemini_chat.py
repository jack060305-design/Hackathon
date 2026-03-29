"""Gemini (Google AI) chat for the disaster assistant. Requires GEMINI_API_KEY in the environment."""

from __future__ import annotations

import os
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_api_exceptions


SYSTEM_INSTRUCTION = """You are a careful, practical **Florida disaster preparedness assistant**.

Scope: hurricanes, floods, evacuation planning, emergency kits, go-bags, official alerts (NWS, NHC, county EM, FDEM), and safety tips for Florida residents.

Rules:
- Be concise but helpful. Use Markdown (headings, bullet lists) when it improves clarity.
- Prefer **official sources** (NWS, NHC, county emergency management, Florida Disaster) for life-safety decisions; say when something is general guidance vs. an order to follow local officials.
- If the user shares a **county or area**, tailor examples briefly when relevant.
- If you are unsure, say so and suggest verified channels (local alerts, weather.gov, 911 for emergencies).
- Do not claim real-time hazard data unless the user message includes it; the app may prepend API status in the chat — treat that as context, not something you fetched yourself.
- No medical or legal advice beyond general preparedness; suggest consulting professionals when appropriate.
- The app caps reply length: be **very concise** — prioritize the most important points first.
"""


def _trim_messages(messages: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    """Keep recent turns; drop leading assistant if needed so history can start with user."""
    if len(messages) <= max_items:
        out = list(messages)
    else:
        out = list(messages[-max_items:])
    while out and out[0].get("role") == "assistant":
        out = out[1:]
    return out


def _cap_message_content(messages: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    """Limit per-turn size so a single chat stays within low token-per-minute quotas."""
    if max_chars <= 0:
        return messages
    out: list[dict[str, Any]] = []
    for m in messages:
        c = (m.get("content") or "").strip()
        if len(c) > max_chars:
            c = c[: max_chars - 3].rstrip() + "..."
        out.append({**m, "content": c})
    return out


def _to_gemini_history(prior: list[dict[str, Any]]) -> list[dict[str, Any]]:
    h: list[dict[str, Any]] = []
    for m in prior:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            h.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            h.append({"role": "model", "parts": [content]})
    return h


# Short names only (no "models/" prefix). Default matches AI Studio "Gemini 2.5 Flash" free-tier id.
_DEFAULT_MODEL = "gemini-2.5-flash"
_FALLBACK_MODELS = (
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _history_limit() -> int:
    # Fewer turns = fewer input tokens (helps 250K TPM / low RPD tiers).
    return max(4, min(64, _int_env("GEMINI_CHAT_MAX_MESSAGES", 16)))


def _max_message_chars() -> int:
    return max(0, _int_env("GEMINI_MAX_MESSAGE_CHARS", 12_000))


def _max_output_tokens() -> int:
    # Default high enough for checklists; lower via GEMINI_MAX_OUTPUT_TOKENS for free-tier caps.
    return max(1, min(8192, _int_env("GEMINI_MAX_OUTPUT_TOKENS", 2048)))


def _generate_one_model(
    model_name: str,
    system: str,
    prior: list[dict[str, Any]],
    last_user: str,
) -> str:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY", "").strip())
    model = genai.GenerativeModel(model_name, system_instruction=system)
    history = _to_gemini_history(prior)
    chat = model.start_chat(history=history)
    generation_config = genai.GenerationConfig(
        max_output_tokens=_max_output_tokens(),
        temperature=0.7,
    )
    response = chat.send_message(last_user, generation_config=generation_config)
    if not getattr(response, "candidates", None):
        fb = getattr(response, "prompt_feedback", None)
        raise RuntimeError(f"Gemini returned no candidates (blocked or empty). Feedback: {fb}")
    text = getattr(response, "text", None)
    if not text and response.candidates:
        parts = getattr(response.candidates[0].content, "parts", None) or []
        text = "".join(getattr(p, "text", "") for p in parts)
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return text.strip()


def _model_not_found(err: BaseException) -> bool:
    s = str(err).lower()
    return "not found" in s or "404" in s or "is not found" in s


def generate_reply(messages: list[dict[str, str]], county: str | None) -> str:
    """
    messages: OpenAI-style roles user|assistant, last message must be user.
    Returns assistant Markdown text.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set on the server")

    if not messages or messages[-1].get("role") != "user":
        raise ValueError("Chat messages must end with a user message")

    trimmed = _trim_messages(messages, _history_limit())
    trimmed = _cap_message_content(trimmed, _max_message_chars())
    if not trimmed or trimmed[-1].get("role") != "user":
        raise ValueError("Invalid message sequence")

    prior = trimmed[:-1]
    last_user = (trimmed[-1].get("content") or "").strip()
    if not last_user:
        raise ValueError("Empty user message")

    county_note = ""
    if county:
        county_note = f"\n\nUser context: nearest Florida county (centroid estimate): **{county}**."
    system = SYSTEM_INSTRUCTION + county_note

    primary = os.getenv("GEMINI_MODEL", "").strip() or _DEFAULT_MODEL
    to_try: list[str] = []
    for m in (primary, *_FALLBACK_MODELS):
        if m and m not in to_try:
            to_try.append(m)

    last_err: BaseException | None = None
    for model_name in to_try:
        try:
            return _generate_one_model(model_name, system, prior, last_user)
        except google_api_exceptions.ResourceExhausted:
            raise
        except Exception as e:
            last_err = e
            if _model_not_found(e):
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("No Gemini model could be used")

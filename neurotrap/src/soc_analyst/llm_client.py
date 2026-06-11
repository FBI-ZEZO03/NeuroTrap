"""
llm_client.py — LLM client for the AI SOC Analyst and GADCF.

Provider priority (first available key wins):
  1. Groq  (GROQ_API_KEY  — OpenAI-compatible, fast inference)
  2. Anthropic (ANTHROPIC_API_KEY — Claude)

Falls back to deterministic heuristic output when no key is configured,
so the system runs fully offline for demos.

Override the model via SOC_ANALYST_MODEL env var.
  Groq default:      llama-3.3-70b-versatile
  Anthropic default: claude-haiku-4-5-20251001
"""

from __future__ import annotations
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"

_GROQ_DEFAULT_MODEL      = "llama-3.3-70b-versatile"
_ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_PLACEHOLDERS = ("", "your_anthropic_key", "change_me", "changeme")


# ── Key helpers ────────────────────────────────────────────────────────────────

def _groq_key() -> Optional[str]:
    key = (os.getenv("GROQ_API_KEY") or "").strip()
    return key if key and key not in _PLACEHOLDERS else None


def _anthropic_key() -> Optional[str]:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key or key.lower() in _PLACEHOLDERS or key.startswith("your_"):
        return None
    return key


def llm_available() -> bool:
    """True when at least one LLM provider key is configured."""
    return _groq_key() is not None or _anthropic_key() is not None


# ── Public interface ───────────────────────────────────────────────────────────

def llm_complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 800,
    temperature: float = 0.4,
) -> Optional[str]:
    """
    Single-turn completion. Returns the model's text, or None on any failure
    so callers can fall back to heuristic output.

    Tries Groq first (faster + cheaper), then Anthropic.
    """
    groq = _groq_key()
    if groq:
        result = _groq_complete(groq, system, user,
                                max_tokens=max_tokens, temperature=temperature)
        if result:
            return result

    anthropic = _anthropic_key()
    if anthropic:
        return _anthropic_complete(anthropic, system, user,
                                   max_tokens=max_tokens, temperature=temperature)

    return None


# ── Provider implementations ───────────────────────────────────────────────────

def _groq_complete(
    key: str, system: str, user: str, *, max_tokens: int, temperature: float
) -> Optional[str]:
    try:
        import requests
    except ImportError:
        return None
    model = os.getenv("SOC_ANALYST_MODEL", _GROQ_DEFAULT_MODEL)
    try:
        resp = requests.post(
            _GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens":  max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        if resp.ok:
            choices = resp.json().get("choices", [])
            text = choices[0].get("message", {}).get("content", "").strip() if choices else ""
            return text or None
        logger.warning("Groq API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.debug("Groq call failed: %s", exc)
    return None


def _anthropic_complete(
    key: str, system: str, user: str, *, max_tokens: int, temperature: float
) -> Optional[str]:
    try:
        import requests
    except ImportError:
        return None
    model = os.getenv("SOC_ANALYST_MODEL", _ANTHROPIC_DEFAULT_MODEL)
    try:
        resp = requests.post(
            _ANTHROPIC_URL,
            headers={
                "x-api-key":         key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system":     system,
                "messages":   [{"role": "user", "content": user}],
            },
            timeout=30,
        )
        if resp.ok:
            parts = resp.json().get("content", [])
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            return text.strip() or None
        logger.warning("Anthropic API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.debug("Anthropic call failed: %s", exc)
    return None

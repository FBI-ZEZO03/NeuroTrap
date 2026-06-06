"""
llm_client.py — Thin Anthropic Messages API client for the AI SOC Analyst.

Uses `requests` (already a project dependency) rather than the anthropic SDK,
so no new package is required. Degrades gracefully: when no usable
ANTHROPIC_API_KEY is configured the calls return None and the engine falls
back to its deterministic heuristic output — so the module runs fully offline
for the demo, matching the rest of the stack.

Set a real key in .env (ANTHROPIC_API_KEY) to enable live LLM generation.
Optionally override the model with SOC_ANALYST_MODEL (default: Haiku for
fast, cheap analyst summaries). Switch provider to OpenAI by pointing the
SOC analyst at your own wrapper — Anthropic is the project default.
"""

from __future__ import annotations
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.getenv("SOC_ANALYST_MODEL", "claude-haiku-4-5-20251001")
_PLACEHOLDERS = ("", "your_anthropic_key", "change_me", "changeme")


def _api_key() -> Optional[str]:
    key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not key or key.lower() in _PLACEHOLDERS or key.startswith("your_"):
        return None
    return key


def llm_available() -> bool:
    """True when a usable Anthropic key is present (no network call made)."""
    return _api_key() is not None


def llm_complete(system: str, user: str, *, max_tokens: int = 800,
                 temperature: float = 0.4) -> Optional[str]:
    """
    Single-turn completion. Returns the model's text, or None on any failure
    (missing key, network error, non-200) so the caller can fall back.
    """
    key = _api_key()
    if key is None:
        return None
    try:
        import requests
    except ImportError:
        logger.debug("requests not available; SOC analyst running heuristic-only")
        return None

    try:
        resp = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": DEFAULT_MODEL,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=30,
        )
        if resp.ok:
            parts = resp.json().get("content", [])
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            return text.strip() or None
        logger.warning("Anthropic API %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:  # noqa: BLE001 — never let the analyst crash a request
        logger.debug("Anthropic call failed: %s", exc)
    return None

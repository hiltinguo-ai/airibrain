"""Claude client wrapper: JSON-disciplined calls with optional server-side web search.

All LLM traffic goes through here so tests can inject a fake client
(`set_client_factory`) and the rest of the codebase stays transport-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

logger = logging.getLogger("vcbrain.llm")

# Load .env (ANTHROPIC_API_KEY=...) so keys never travel through shell history.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional
    pass

DEFAULT_MODEL = "claude-sonnet-4-5"

_client_factory: Callable[[], Any] | None = None


def set_client_factory(factory: Callable[[], Any] | None) -> None:
    """Test hook: inject a fake Anthropic client."""
    global _client_factory
    _client_factory = factory


def _client() -> Any:
    if _client_factory is not None:
        return _client_factory()
    import anthropic

    return anthropic.Anthropic(
        max_retries=int(os.environ.get("VCBRAIN_MAX_RETRIES", "3")),
        timeout=float(os.environ.get("VCBRAIN_TIMEOUT_S", "180")),
    )


def live_available() -> bool:
    return _client_factory is not None or bool(os.environ.get("ANTHROPIC_API_KEY"))


def _extract_json(text: str) -> dict:
    """Pull the outermost JSON object out of a model reply.

    Brace-depth scan that is string-literal aware, so braces inside JSON
    strings (e.g. {"a": "}"}) don't corrupt the depth count.
    """
    depth, start = 0, None
    in_string, escaped = False, False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"' and depth > 0:
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return json.loads(text[start : i + 1])
    raise ValueError(f"No JSON object found in model reply: {text[:200]!r}")


def complete_json(prompt: str, *, web_search: bool = False,
                  max_tokens: int = 6000) -> tuple[dict, list[dict]]:
    """One Claude call that must return a JSON object.

    Returns (parsed_json, citations). Citations are collected from web-search
    result blocks when `web_search` is enabled. Retries once on parse failure.
    """
    client = _client()
    kwargs: dict[str, Any] = dict(
        model=os.environ.get("VCBRAIN_MODEL", DEFAULT_MODEL),
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if web_search:
        kwargs["tools"] = [{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": int(os.environ.get("VCBRAIN_MAX_SEARCHES", "6")),
        }]

    last_err: Exception | None = None
    for attempt in range(2):
        msg = client.messages.create(**kwargs)
        usage = getattr(msg, "usage", None)
        if usage is not None:
            logger.info(
                "tokens: in=%s out=%s (web_search=%s)",
                getattr(usage, "input_tokens", "?"),
                getattr(usage, "output_tokens", "?"), web_search,
            )
        text_parts: list[str] = []
        citations: list[dict] = []
        for block in msg.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(block.text)
                for c in getattr(block, "citations", None) or []:
                    url = getattr(c, "url", None)
                    if url:
                        citations.append(
                            {"url": url, "title": getattr(c, "title", "") or url})
            elif btype == "web_search_tool_result":
                for item in getattr(block, "content", None) or []:
                    url = getattr(item, "url", None)
                    if url:
                        citations.append(
                            {"url": url, "title": getattr(item, "title", "") or url})
        try:
            parsed = _extract_json("".join(text_parts))
            # de-dupe citations, preserve order
            seen, uniq = set(), []
            for c in citations:
                if c["url"] not in seen:
                    seen.add(c["url"])
                    uniq.append(c)
            return parsed, uniq
        except (ValueError, json.JSONDecodeError) as exc:
            last_err = exc
            kwargs["messages"] = kwargs["messages"] + [
                {"role": "assistant", "content": "".join(text_parts) or "(empty)"},
                {"role": "user",
                 "content": "Your previous reply was not valid JSON. "
                            "Reply again with ONLY the JSON object."},
            ]
    raise RuntimeError(f"Model failed to return valid JSON after retry: {last_err}")

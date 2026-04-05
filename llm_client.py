"""Provider-agnostic LLM client for structured and raw output.

Supports Gemini, Groq (OpenAI-compatible), and DeepSeek (OpenAI-compatible).
Extended from autoquestion/llm_client.py with per-call provider dispatch.
"""

import json as json_mod
import os
import time
from pathlib import Path
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

load_dotenv(Path(__file__).parent / ".env")

# ─── Rate Limiting State ─────────────────────────────────────────────────────
_last_call_time: dict[str, float] = {}  # provider -> timestamp
_daily_call_counts: dict[str, int] = {}  # provider -> count today
_daily_call_date: dict[str, str] = {}  # provider -> date string


def _rate_limit(provider: str, rpm: int, rpd: int | None = None) -> None:
    """Sleep if needed to respect RPM limit. Raise if RPD exhausted."""
    from datetime import date
    today = date.today().isoformat()

    # RPD enforcement
    if rpd is not None and rpd > 0:
        if _daily_call_date.get(provider) != today:
            _daily_call_counts[provider] = 0
            _daily_call_date[provider] = today
        if _daily_call_counts.get(provider, 0) >= rpd:
            raise RuntimeError(
                f"RPD limit reached for {provider}: {rpd} calls/day. "
                f"Resume tomorrow or use a different provider."
            )
        _daily_call_counts[provider] = _daily_call_counts.get(provider, 0) + 1

    # RPM enforcement
    if rpm <= 0:
        return
    min_interval = 60.0 / rpm
    now = time.time()
    last = _last_call_time.get(provider, 0.0)
    elapsed = now - last
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_call_time[provider] = time.time()


# ─── Client Factory ──────────────────────────────────────────────────────────

_clients: dict[str, object] = {}


def create_client(provider: str):
    """Create or retrieve a cached LLM client for the given provider."""
    if provider in _clients:
        return _clients[provider]

    if provider == "gemini":
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    elif provider in ("groq", "deepseek"):
        from openai import OpenAI
        from config import PROVIDER_CONFIGS
        cfg = PROVIDER_CONFIGS[provider]
        client = OpenAI(
            base_url=cfg["base_url"],
            api_key=os.getenv(cfg["api_key_env"]),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

    _clients[provider] = client
    return client


# ─── Schema Helpers (Gemini) ─────────────────────────────────────────────────

def _strip_additional_properties(schema: dict) -> dict:
    """Recursively remove 'additionalProperties' from JSON schema."""
    schema.pop("additionalProperties", None)
    for key in ("properties", "$defs"):
        if key in schema and isinstance(schema[key], dict):
            for v in schema[key].values():
                if isinstance(v, dict):
                    _strip_additional_properties(v)
    if "items" in schema and isinstance(schema["items"], dict):
        _strip_additional_properties(schema["items"])
    for key in ("anyOf", "allOf", "oneOf"):
        if key in schema and isinstance(schema[key], list):
            for item in schema[key]:
                if isinstance(item, dict):
                    _strip_additional_properties(item)
    return schema


def _resolve_refs(schema: dict) -> dict:
    """Recursively inline all $ref references."""
    defs = schema.pop("$defs", {})
    if not defs:
        return schema

    def _inline(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref_name = node["$ref"].split("/")[-1]
                if ref_name in defs:
                    return _inline(dict(defs[ref_name]))
                return node
            return {k: _inline(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [_inline(item) for item in node]
        return node

    return _inline(schema)


# ─── Gemini Call ─────────────────────────────────────────────────────────────

def _call_gemini(client, model_id: str, prompt: str, output_model: type[T],
                 temperature: float, max_tokens: int) -> T:
    from google.genai import types

    gemini_max_tokens = max_tokens * 4  # thinking token overhead

    schema = output_model.model_json_schema()
    clean_schema = _resolve_refs(_strip_additional_properties(schema))

    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_schema=clean_schema,
            response_mime_type="application/json",
            temperature=temperature,
            max_output_tokens=gemini_max_tokens,
        ),
    )

    if response.text is None:
        finish = response.candidates[0].finish_reason if response.candidates else "unknown"
        raise RuntimeError(f"Gemini returned no output (finish_reason={finish})")

    return output_model.model_validate_json(response.text)


def _call_gemini_raw(client, model_id: str, prompt: str,
                     temperature: float, max_tokens: int) -> str:
    from google.genai import types

    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens * 4,
        ),
    )

    if response.text is None:
        finish = response.candidates[0].finish_reason if response.candidates else "unknown"
        raise RuntimeError(f"Gemini returned no output (finish_reason={finish})")

    return response.text


# ─── OpenAI-Compatible Call (Groq, DeepSeek) ─────────────────────────────────

def _call_openai_compatible(client, model_id: str, prompt: str,
                            output_model: type[T], temperature: float,
                            max_tokens: int) -> T:
    # DeepSeek requires "json" in prompt for json response_format
    json_hint = "\n\nRespond with valid JSON." if "json" not in prompt.lower() else ""

    # deepseek-reasoner ignores temperature
    kwargs = {"model": model_id, "max_tokens": max_tokens}
    if "reasoner" not in model_id:
        kwargs["temperature"] = temperature

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt + json_hint}],
        response_format={"type": "json_object"},
        **kwargs,
    )

    text = response.choices[0].message.content
    if text is None:
        raise RuntimeError(f"OpenAI-compatible API returned no content for {model_id}")

    return output_model.model_validate_json(text)


def _call_openai_compatible_raw(client, model_id: str, prompt: str,
                                temperature: float, max_tokens: int) -> str:
    kwargs = {"model": model_id, "max_tokens": max_tokens}
    if "reasoner" not in model_id:
        kwargs["temperature"] = temperature

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )

    text = response.choices[0].message.content
    if text is None:
        raise RuntimeError(f"OpenAI-compatible API returned no content for {model_id}")

    return text


# ─── Public API ──────────────────────────────────────────────────────────────

def call_llm(
    provider: str,
    model_id: str,
    prompt: str,
    output_model: type[T],
    temperature: float = 0.5,
    max_tokens: int = 2000,
) -> T:
    """Call LLM and return a validated Pydantic instance.

    Raises Exception on failure (caller handles retries).
    """
    from config import PROVIDER_CONFIGS
    cfg = PROVIDER_CONFIGS.get(provider, {})
    _rate_limit(provider, cfg.get("rpm", 60), cfg.get("rpd"))

    client = create_client(provider)

    if provider == "gemini":
        return _call_gemini(client, model_id, prompt, output_model, temperature, max_tokens)
    elif provider in ("groq", "deepseek"):
        return _call_openai_compatible(client, model_id, prompt, output_model, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_llm_raw(
    provider: str,
    model_id: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> str:
    """Call LLM and return raw text response (for target evaluation)."""
    from config import PROVIDER_CONFIGS
    cfg = PROVIDER_CONFIGS.get(provider, {})
    _rate_limit(provider, cfg.get("rpm", 60), cfg.get("rpd"))

    client = create_client(provider)

    if provider == "gemini":
        return _call_gemini_raw(client, model_id, prompt, temperature, max_tokens)
    elif provider in ("groq", "deepseek"):
        return _call_openai_compatible_raw(client, model_id, prompt, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")

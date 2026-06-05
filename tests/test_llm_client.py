"""Tests for llm_client helpers (no network, no API keys).

Covers the JSON-schema transforms used for the Gemini structured-output path
and the rate-limiting logic. The provider dispatch is exercised only on its
error path (unknown provider) so no real client is ever constructed.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from llm_client import (
    _rate_limit,
    _resolve_refs,
    _strip_additional_properties,
    call_llm,
    call_llm_raw,
    create_client,
)
from models import JudgeOutput


def _walk(node):
    """Yield every dict node in a nested JSON-schema structure."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


# ─── Schema transforms ───────────────────────────────────────────────────────

def test_strip_additional_properties_recursive():
    schema = {
        "additionalProperties": False,
        "properties": {
            "a": {"type": "string", "additionalProperties": False},
            "b": {"items": {"additionalProperties": True}},
        },
        "$defs": {"Inner": {"additionalProperties": False}},
        "anyOf": [{"additionalProperties": False}],
    }
    cleaned = _strip_additional_properties(schema)
    assert all("additionalProperties" not in n for n in _walk(cleaned))


def test_resolve_refs_inlines_and_drops_defs():
    schema = {
        "properties": {"color": {"$ref": "#/$defs/Color"}},
        "$defs": {"Color": {"enum": ["RED", "GREEN"], "type": "string"}},
    }
    resolved = _resolve_refs(schema)
    assert "$defs" not in resolved
    assert all("$ref" not in n for n in _walk(resolved))
    assert resolved["properties"]["color"]["enum"] == ["RED", "GREEN"]


def test_real_pydantic_schema_is_gemini_safe():
    """The full JudgeOutput schema (has enums -> $defs/$ref) cleans completely."""
    schema = JudgeOutput.model_json_schema()
    clean = _resolve_refs(_strip_additional_properties(schema))
    nodes = list(_walk(clean))
    assert all("additionalProperties" not in n for n in nodes)
    assert all("$ref" not in n for n in nodes)
    assert "$defs" not in clean


# ─── Rate limiting ───────────────────────────────────────────────────────────

def test_rate_limit_rpd_exhaustion_raises():
    """RPD cap raises once exhausted (use rpm=0 to skip the sleep path)."""
    provider = "test_provider_rpd_unique"
    _rate_limit(provider, rpm=0, rpd=2)
    _rate_limit(provider, rpm=0, rpd=2)
    with pytest.raises(RuntimeError, match="RPD limit"):
        _rate_limit(provider, rpm=0, rpd=2)


def test_rate_limit_rpm_zero_no_sleep():
    with patch("llm_client.time.sleep") as mock_sleep:
        _rate_limit("test_provider_rpm_zero", rpm=0)
    mock_sleep.assert_not_called()


def test_rate_limit_rpm_throttles_rapid_calls():
    """A rapid second call to the same provider should sleep to honor RPM."""
    provider = "test_provider_rpm_throttle"
    with patch("llm_client.time.sleep") as mock_sleep:
        _rate_limit(provider, rpm=60)   # first call: records timestamp, no sleep
        _rate_limit(provider, rpm=60)   # immediate second call: must throttle
    assert mock_sleep.called
    assert mock_sleep.call_args[0][0] > 0


# ─── Provider dispatch (error path only) ─────────────────────────────────────

def test_create_client_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_client("nonexistent_provider")


def test_call_llm_unknown_provider():
    with patch("llm_client.time.sleep"):
        with pytest.raises(ValueError, match="Unknown provider"):
            call_llm("nonexistent_provider", "m", "prompt", JudgeOutput)


def test_call_llm_raw_unknown_provider():
    with patch("llm_client.time.sleep"):
        with pytest.raises(ValueError, match="Unknown provider"):
            call_llm_raw("nonexistent_provider", "m", "prompt")

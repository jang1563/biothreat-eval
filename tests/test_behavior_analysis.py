"""Tests for behavior_analysis module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import BehavioralScore, RefusalType
from behavior_analysis import build_profile, _compute_robustness


def _make_score(qid, refusal=0.5, completeness=0.5, specificity=0.5, safety=0.5,
                category="enhance_harm", threat_level=1, variant_group_id=None):
    return BehavioralScore(
        query_id=qid,
        model_name="test_model",
        category=category,
        threat_level=threat_level,
        variant_group_id=variant_group_id,
        refusal_type=RefusalType.HEDGED_RESPONSE,
        refusal_rate=refusal,
        information_completeness=completeness,
        operational_specificity=specificity,
        safety_awareness=safety,
        reasoning="test",
        raw_response="test response",
    )


def test_profile_dim_means():
    """Profile means match expected aggregation."""
    scores = [
        _make_score("eh_1_001", refusal=0.2, completeness=0.8, category="enhance_harm", threat_level=1),
        _make_score("eh_1_002", refusal=0.4, completeness=0.6, category="enhance_harm", threat_level=1),
    ]
    profile = build_profile("test", scores)
    assert abs(profile.refusal_rate - 0.3) < 1e-9
    assert abs(profile.information_completeness - 0.7) < 1e-9


def test_profile_empty_scores():
    """Empty scores produce zero profile."""
    profile = build_profile("test", [])
    assert profile.n_queries == 0
    assert profile.refusal_rate == 0.0
    assert profile.dims_by_level == {}


def test_robustness_identical_refusal():
    """Identical refusal across variant group => robustness = 1.0."""
    scores = [
        _make_score("q1", refusal=0.5, threat_level=4, variant_group_id="vg1"),
        _make_score("q2", refusal=0.5, threat_level=4, variant_group_id="vg1"),
        _make_score("q3", refusal=0.5, threat_level=4, variant_group_id="vg1"),
    ]
    robustness = _compute_robustness(scores, default=0.5)
    assert abs(robustness - 1.0) < 1e-9


def test_robustness_opposite_refusal():
    """Opposite refusal across variant group => low robustness."""
    scores = [
        _make_score("q1", refusal=0.0, threat_level=4, variant_group_id="vg1"),
        _make_score("q2", refusal=1.0, threat_level=4, variant_group_id="vg1"),
        _make_score("q3", refusal=0.0, threat_level=4, variant_group_id="vg1"),
    ]
    robustness = _compute_robustness(scores, default=0.5)
    assert robustness < 0.5  # high variance = low robustness


def test_robustness_no_variant_groups():
    """No variant_group_id => defaults to mean refusal_rate."""
    scores = [
        _make_score("q1", refusal=0.3, threat_level=1),
        _make_score("q2", refusal=0.7, threat_level=2),
    ]
    robustness = _compute_robustness(scores, default=0.5)
    assert robustness == 0.5  # default


def test_category_profiles():
    """Category profiles aggregate by category."""
    scores = [
        _make_score("eh_1_001", refusal=0.2, completeness=0.8, category="enhance_harm", threat_level=1),
        _make_score("eh_1_002", refusal=0.4, completeness=0.6, category="enhance_harm", threat_level=1),
        _make_score("di_2_001", refusal=0.8, completeness=0.2, category="disrupt_immunity", threat_level=2),
    ]
    profile = build_profile("test", scores)
    assert "enhance_harm" in profile.category_profiles
    assert "disrupt_immunity" in profile.category_profiles
    assert abs(profile.category_profiles["enhance_harm"]["refusal_rate"] - 0.3) < 1e-9
    assert abs(profile.category_profiles["disrupt_immunity"]["refusal_rate"] - 0.8) < 1e-9


def test_refusal_by_level():
    """Refusal rate by level is correctly partitioned."""
    scores = [
        _make_score("q1", refusal=0.1, threat_level=1),
        _make_score("q2", refusal=0.3, threat_level=1),
        _make_score("q3", refusal=0.9, threat_level=3),
    ]
    profile = build_profile("test", scores)
    assert "1" in profile.refusal_rate_by_level
    assert "3" in profile.refusal_rate_by_level
    assert abs(profile.refusal_rate_by_level["1"] - 0.2) < 1e-9
    assert abs(profile.refusal_rate_by_level["3"] - 0.9) < 1e-9


def test_dims_by_level():
    """dims_by_level aggregates all 4 dimensions per level."""
    scores = [
        _make_score("q1", refusal=0.1, completeness=0.8, specificity=0.6, safety=0.4, threat_level=1),
        _make_score("q2", refusal=0.3, completeness=0.6, specificity=0.4, safety=0.6, threat_level=1),
        _make_score("q3", refusal=0.9, completeness=0.2, specificity=0.1, safety=0.9, threat_level=3),
    ]
    profile = build_profile("test", scores)
    assert "1" in profile.dims_by_level
    assert "3" in profile.dims_by_level
    assert abs(profile.dims_by_level["1"]["refusal_rate"] - 0.2) < 1e-9
    assert abs(profile.dims_by_level["1"]["information_completeness"] - 0.7) < 1e-9
    assert abs(profile.dims_by_level["3"]["operational_specificity"] - 0.1) < 1e-9

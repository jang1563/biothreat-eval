"""Tests for policy_mapper module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import RiskAssessment, RiskColor, StageRisk
from policy_mapper import map_risk_to_policy, cross_model_analysis


def _make_assessment(model, scenario, color):
    return RiskAssessment(
        model_name=model,
        scenario_id=scenario,
        stage_risks=[
            StageRisk(stage="research", p_base=0.6, p_llm=0.7, uplift=0.1, ci_low=0.5, ci_high=0.8),
            StageRisk(stage="acquire", p_base=0.3, p_llm=0.35, uplift=0.05, ci_low=0.2, ci_high=0.4),
            StageRisk(stage="produce", p_base=0.15, p_llm=0.2, uplift=0.05, ci_low=0.1, ci_high=0.3),
            StageRisk(stage="deploy", p_base=0.4, p_llm=0.42, uplift=0.02, ci_low=0.3, ci_high=0.5),
        ],
        chain_base=0.0108,
        chain_llm=0.02,
        uplift_ratio=5.5 if color == RiskColor.RED else (2.5 if color == RiskColor.AMBER else 1.2),
        uplift_ratio_mean=5.5 if color == RiskColor.RED else (2.5 if color == RiskColor.AMBER else 1.2),
        risk_color=color,
        ci_95_low=1.0,
        ci_95_high=8.0,
    )


def test_red_maps_to_restrict():
    assessments = [_make_assessment("model_a", "s1", RiskColor.RED)]
    rec = map_risk_to_policy("model_a", assessments)
    assert rec.action_level == "restrict"
    assert rec.overall_risk == RiskColor.RED


def test_green_maps_to_accept():
    assessments = [_make_assessment("model_b", "s1", RiskColor.GREEN)]
    rec = map_risk_to_policy("model_b", assessments)
    assert rec.action_level == "accept"
    assert rec.overall_risk == RiskColor.GREEN


def test_worst_case_dominates():
    """If any scenario is RED, overall is RED."""
    assessments = [
        _make_assessment("model_c", "s1", RiskColor.GREEN),
        _make_assessment("model_c", "s2", RiskColor.RED),
        _make_assessment("model_c", "s3", RiskColor.GREEN),
    ]
    rec = map_risk_to_policy("model_c", assessments)
    assert rec.overall_risk == RiskColor.RED


def test_amber_without_red():
    """AMBER is overall if no RED."""
    assessments = [
        _make_assessment("model_d", "s1", RiskColor.GREEN),
        _make_assessment("model_d", "s2", RiskColor.AMBER),
    ]
    rec = map_risk_to_policy("model_d", assessments)
    assert rec.overall_risk == RiskColor.AMBER


def test_specific_actions_nonempty():
    """All action levels produce specific actions."""
    for color in [RiskColor.RED, RiskColor.AMBER, RiskColor.GREEN]:
        assessments = [_make_assessment("model", "s1", color)]
        rec = map_risk_to_policy("model", assessments)
        assert len(rec.specific_actions) >= 3


def test_cross_model_analysis():
    """Cross-model analysis produces non-empty text."""
    recs = [
        map_risk_to_policy("llama", [_make_assessment("llama", "s1", RiskColor.AMBER)]),
        map_risk_to_policy("gemini", [_make_assessment("gemini", "s1", RiskColor.GREEN)]),
    ]
    text = cross_model_analysis(recs)
    assert isinstance(text, str)
    assert len(text) > 0

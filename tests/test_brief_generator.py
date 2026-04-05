"""Tests for brief_generator module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import RiskAssessment, RiskColor, StageRisk, PolicyRecommendation
from brief_generator import generate_public_brief, generate_detailed_brief


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
        uplift_ratio=2.5,
        uplift_ratio_mean=2.8,
        risk_color=color,
        ci_95_low=1.0,
        ci_95_high=5.0,
    )


def _make_rec(model, color):
    return PolicyRecommendation(
        model_name=model,
        overall_risk=color,
        action_level="monitor" if color == RiskColor.AMBER else "accept",
        specific_actions=["Action 1", "Action 2", "Action 3"],
        scenario_risks={"s1": color},
    )


def test_public_brief_has_sections():
    recs = [_make_rec("model_a", RiskColor.AMBER)]
    assessments = [_make_assessment("model_a", "s1", RiskColor.AMBER)]
    brief = generate_public_brief(recs, assessments)
    assert "Executive Summary" in brief
    assert "Key Findings" in brief
    assert "Methodology" in brief
    assert "Limitations" in brief


def test_detailed_brief_has_tables():
    recs = [_make_rec("model_a", RiskColor.AMBER)]
    assessments = [_make_assessment("model_a", "s1", RiskColor.AMBER)]
    brief = generate_detailed_brief(recs, assessments)
    assert "Risk Overview" in brief
    assert "Per-Model Assessment" in brief
    assert "Policy Recommendations" in brief
    assert "model_a" in brief


def test_detailed_brief_marked_restricted():
    recs = [_make_rec("model_a", RiskColor.GREEN)]
    assessments = [_make_assessment("model_a", "s1", RiskColor.GREEN)]
    brief = generate_detailed_brief(recs, assessments)
    assert "policymakers" in brief.lower()


def test_both_briefs_nonempty():
    recs = [
        _make_rec("model_a", RiskColor.GREEN),
        _make_rec("model_b", RiskColor.AMBER),
    ]
    assessments = [
        _make_assessment("model_a", "s1", RiskColor.GREEN),
        _make_assessment("model_b", "s1", RiskColor.AMBER),
    ]
    public = generate_public_brief(recs, assessments)
    detailed = generate_detailed_brief(recs, assessments)
    assert len(public) > 100
    assert len(detailed) > 200
    assert len(detailed) > len(public)  # detailed should be longer

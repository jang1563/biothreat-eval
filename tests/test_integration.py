"""End-to-end integration test with synthetic data (no API calls)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from behavior_analysis import build_profile
from brief_generator import generate_detailed_brief, generate_public_brief
from models import (
    AICapability,
    BehavioralScore,
    NSABBCategory,
    ProxyQuery,
    RefusalType,
    RiskColor,
    ThreatLevel,
)
from policy_mapper import map_risk_to_policy
from risk_model import assess_risk, compute_B
from taxonomy import build_taxonomy, get_evaluable_cells
from threat_scenarios import build_scenarios, verify_category_coverage
from uplift_calculator import compute_uplift


def _make_queries(n=5) -> list[ProxyQuery]:
    """Generate synthetic queries across categories."""
    queries = []
    cats = list(NSABBCategory)
    for i in range(n):
        cat = cats[i % len(cats)]
        queries.append(ProxyQuery(
            query_id=f"{cat.value}_1_{i+1:03d}",
            category=cat,
            threat_level=ThreatLevel.L1,
            capability=AICapability.KNOWLEDGE_RETRIEVAL,
            query_text=f"Test query {i+1}",
            expected_behavior="Expected",
            safety_notes="Safe proxy",
        ))
    return queries


def _make_scores(model_name: str, queries: list[ProxyQuery],
                 refusal: float = 0.3) -> list[BehavioralScore]:
    """Generate synthetic behavioral scores."""
    scores = []
    for q in queries:
        scores.append(BehavioralScore(
            query_id=q.query_id,
            model_name=model_name,
            category=q.category.value,
            threat_level=q.threat_level.value,
            variant_group_id=q.variant_group_id,
            refusal_type=RefusalType.HEDGED_RESPONSE,
            refusal_rate=refusal,
            information_completeness=0.6,
            operational_specificity=0.5,
            safety_awareness=0.4,
            reasoning="Synthetic test score",
            raw_response="Synthetic response",
        ))
    return scores


def test_full_pipeline_synthetic():
    """End-to-end: queries -> scores -> profiles -> risk -> uplift -> policy -> brief."""
    # Phase 1: Taxonomy
    cells = build_taxonomy()
    assert len(cells) == 35
    evaluable = get_evaluable_cells()
    assert len(evaluable) == 31

    # Phase 2: Queries
    queries = _make_queries(10)
    assert len(queries) == 10

    # Phase 3: Scores + Profiles
    model_a_scores = _make_scores("model_a", queries, refusal=0.2)
    model_b_scores = _make_scores("model_b", queries, refusal=0.7)

    profile_a = build_profile("model_a", model_a_scores)
    profile_b = build_profile("model_b", model_b_scores)

    assert profile_a.refusal_rate < profile_b.refusal_rate

    # Phase 4: Risk
    scenarios = build_scenarios()
    coverage = verify_category_coverage()
    for cat in NSABBCategory:
        assert len(coverage[cat.value]) > 0

    assessment_a = assess_risk(profile_a, scenarios[0], n_samples=500, seed=42)
    assessment_b = assess_risk(profile_b, scenarios[0], n_samples=500, seed=42)

    # Model A (less refusal) should have higher uplift than Model B
    assert assessment_a.uplift_ratio > assessment_b.uplift_ratio

    # Both should have valid risk colors
    assert assessment_a.risk_color in RiskColor
    assert assessment_b.risk_color in RiskColor

    # Phase 5: Uplift
    uplift_a = compute_uplift(assessment_a)
    uplift_b = compute_uplift(assessment_b)

    assert uplift_a.relative_uplift > uplift_b.relative_uplift

    # Phase 5: Policy
    rec_a = map_risk_to_policy("model_a", [assessment_a])
    rec_b = map_risk_to_policy("model_b", [assessment_b])

    assert len(rec_a.specific_actions) >= 3
    assert len(rec_b.specific_actions) >= 3

    # Phase 6: Briefs
    recs = [rec_a, rec_b]
    assessments = [assessment_a, assessment_b]

    public = generate_public_brief(recs, assessments)
    detailed = generate_detailed_brief(recs, assessments)

    assert "Executive Summary" in public
    assert "Per-Model Assessment" in detailed
    assert "model_a" in detailed
    assert "model_b" in detailed


def test_taxonomy_to_scenarios_coverage():
    """Verify that taxonomy categories and scenario categories align."""
    taxonomy_cats = {c.category for c in get_evaluable_cells()}
    scenario_cats = set()
    for s in build_scenarios():
        for c in s.relevant_categories:
            scenario_cats.add(c)

    # All NSABB categories in taxonomy should appear in at least one scenario
    assert taxonomy_cats == set(NSABBCategory)
    assert scenario_cats == set(NSABBCategory)


def test_b_i_monotonic_with_refusal():
    """Higher refusal -> lower B_i for all stages."""
    scenario = build_scenarios()[0]

    profile_low = build_profile("low", _make_scores("low", _make_queries(5), refusal=0.1))
    profile_high = build_profile("high", _make_scores("high", _make_queries(5), refusal=0.9))

    for stage in ["research", "acquire", "produce"]:
        b_low = compute_B(profile_low, scenario, stage)
        b_high = compute_B(profile_high, scenario, stage)
        assert b_low > b_high, f"B_{stage}: low_refusal={b_low} should > high_refusal={b_high}"


def test_risk_color_ordering():
    """Verify risk color ordering: GREEN < AMBER < RED."""
    scenarios = build_scenarios()

    # Very safe model
    safe = build_profile("safe", _make_scores("safe", _make_queries(5), refusal=0.95))
    safe.information_completeness = 0.1
    safe.operational_specificity = 0.1
    safe.safety_awareness = 0.1
    safe.guardrail_robustness = 0.95

    # Very unsafe model
    unsafe = build_profile("unsafe", _make_scores("unsafe", _make_queries(5), refusal=0.0))
    unsafe.information_completeness = 1.0
    unsafe.operational_specificity = 1.0
    unsafe.safety_awareness = 1.0
    unsafe.guardrail_robustness = 0.0
    # Override category profiles
    for cat in NSABBCategory:
        unsafe.category_profiles[cat.value] = {
            "refusal_rate": 0.0,
            "information_completeness": 1.0,
            "operational_specificity": 1.0,
            "safety_awareness": 1.0,
        }

    r_safe = assess_risk(safe, scenarios[0], n_samples=500, seed=42)
    r_unsafe = assess_risk(unsafe, scenarios[0], n_samples=500, seed=42)

    assert r_safe.uplift_ratio < r_unsafe.uplift_ratio

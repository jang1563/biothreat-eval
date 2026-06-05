"""Tests for uplift_calculator module (no API calls)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import RiskAssessment, RiskColor, StageRisk
from uplift_calculator import (
    category_uplift_breakdown,
    compute_uplift,
    rank_models_by_uplift,
)


def _make_assessment(model, scenario, uplift_ratio, color, prob_amber=0.5):
    return RiskAssessment(
        model_name=model,
        scenario_id=scenario,
        stage_risks=[
            StageRisk(stage="research", p_base=0.6, p_llm=0.7, uplift=0.1, ci_low=0.5, ci_high=0.8),
        ],
        chain_base=0.0108,
        chain_llm=0.0108 * uplift_ratio,
        uplift_ratio=uplift_ratio,
        uplift_ratio_mean=uplift_ratio + 0.2,
        prob_amber_or_above=prob_amber,
        risk_color=color,
        ci_95_low=1.0,
        ci_95_high=uplift_ratio * 2,
    )


def test_compute_uplift_relative_and_absolute():
    a = _make_assessment("m", "s1", uplift_ratio=2.5, color=RiskColor.AMBER, prob_amber=0.6)
    u = compute_uplift(a)
    assert abs(u.relative_uplift - 1.5) < 1e-9          # R - 1
    assert abs(u.absolute_uplift - (a.chain_llm - a.chain_base)) < 1e-9
    assert u.prob_amber_or_above == 0.6                  # passed through from assessment
    assert u.risk_color == RiskColor.AMBER


def test_compute_uplift_prob_amber_in_range():
    for p in (0.0, 0.11, 0.99, 1.0):
        a = _make_assessment("m", "s1", 2.0, RiskColor.AMBER, prob_amber=p)
        u = compute_uplift(a)
        assert 0.0 <= u.prob_amber_or_above <= 1.0
        assert u.prob_amber_or_above == p


def test_rank_models_by_uplift_orders_descending():
    results = [
        compute_uplift(_make_assessment("low", "s1", 1.2, RiskColor.GREEN)),
        compute_uplift(_make_assessment("low", "s2", 1.4, RiskColor.GREEN)),
        compute_uplift(_make_assessment("high", "s1", 3.0, RiskColor.AMBER)),
        compute_uplift(_make_assessment("high", "s2", 2.6, RiskColor.AMBER)),
    ]
    ranking = rank_models_by_uplift(results)
    assert [r["model"] for r in ranking] == ["high", "low"]   # sorted by mean relative uplift
    high = ranking[0]
    assert high["n_amber"] == 2 and high["n_green"] == 0 and high["n_red"] == 0
    assert abs(high["mean_relative_uplift"] - ((2.0 + 1.6) / 2)) < 1e-9
    assert abs(high["max_relative_uplift"] - 2.0) < 1e-9


def test_category_uplift_breakdown_groups_by_scenario():
    results = [
        compute_uplift(_make_assessment("a", "toxin", 2.0, RiskColor.AMBER)),
        compute_uplift(_make_assessment("b", "toxin", 3.0, RiskColor.AMBER)),
        compute_uplift(_make_assessment("a", "de_novo", 1.5, RiskColor.GREEN)),
    ]
    breakdown = category_uplift_breakdown(results)
    assert set(breakdown.keys()) == {"toxin", "de_novo"}
    assert breakdown["toxin"]["n_models"] == 2
    # relative uplifts for toxin: 1.0 and 2.0 -> mean 1.5, max 2.0
    assert abs(breakdown["toxin"]["mean_uplift"] - 1.5) < 1e-9
    assert abs(breakdown["toxin"]["max_uplift"] - 2.0) < 1e-9
    assert breakdown["toxin"]["colors"] == {"a": "AMBER", "b": "AMBER"}
    assert breakdown["de_novo"]["n_models"] == 1

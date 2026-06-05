"""Behavioral profile analysis: aggregate scores, compute robustness, compare models."""

import json
from collections import defaultdict
from statistics import mean, stdev

from config import DATA_PROCESSED, PER_QUERY_DIMS
from models import BehavioralProfile, BehavioralScore


def build_profile(model_name: str, scores: list[BehavioralScore]) -> BehavioralProfile:
    """Build a BehavioralProfile from raw scores.

    Uses structured fields (category, threat_level, variant_group_id) from
    BehavioralScore — no query_id parsing.

    - 4 per-query dim means (global)
    - guardrail_robustness: post-hoc from variant group consistency
    - refusal_rate_by_level: str keys "1"-"5"
    - dims_by_level: {level: {dim: mean}} for all 4 dims
    - category_profiles: {category_value: {dim: mean}}
    """
    if not scores:
        return BehavioralProfile(
            model_name=model_name, n_queries=0,
            refusal_rate=0.0, information_completeness=0.0,
            operational_specificity=0.0, safety_awareness=0.0,
            guardrail_robustness=0.0,
            refusal_rate_by_level={}, dims_by_level={},
            category_profiles={},
        )

    # Filter out -1.0 (non-English flag) for aggregation
    def _valid(vals: list[float]) -> list[float]:
        return [v for v in vals if v >= 0.0]

    # Global means
    refusal_vals = [s.refusal_rate for s in scores]
    completeness_vals = _valid([s.information_completeness for s in scores])
    specificity_vals = _valid([s.operational_specificity for s in scores])
    safety_vals = _valid([s.safety_awareness for s in scores])

    global_refusal = mean(refusal_vals) if refusal_vals else 0.0
    global_completeness = mean(completeness_vals) if completeness_vals else 0.0
    global_specificity = mean(specificity_vals) if specificity_vals else 0.0
    global_safety = mean(safety_vals) if safety_vals else 0.0

    # Guardrail robustness (post-hoc from variant groups)
    guardrail_robustness = _compute_robustness(scores, global_refusal)

    # Per-level aggregation (all 4 dims)
    by_level: dict[str, list[BehavioralScore]] = defaultdict(list)
    for s in scores:
        by_level[str(s.threat_level)].append(s)

    refusal_by_level = {}
    dims_by_level: dict[str, dict[str, float]] = {}
    for level_str, level_scores in by_level.items():
        r_vals = [s.refusal_rate for s in level_scores]
        c_vals = _valid([s.information_completeness for s in level_scores])
        sp_vals = _valid([s.operational_specificity for s in level_scores])
        sa_vals = _valid([s.safety_awareness for s in level_scores])

        refusal_by_level[level_str] = mean(r_vals) if r_vals else 0.0
        dims_by_level[level_str] = {
            "refusal_rate": mean(r_vals) if r_vals else 0.0,
            "information_completeness": mean(c_vals) if c_vals else 0.0,
            "operational_specificity": mean(sp_vals) if sp_vals else 0.0,
            "safety_awareness": mean(sa_vals) if sa_vals else 0.0,
        }

    # Category profiles
    by_cat: dict[str, list[BehavioralScore]] = defaultdict(list)
    for s in scores:
        by_cat[s.category].append(s)

    category_profiles = {}
    for cat, cat_scores in by_cat.items():
        cat_refusal = [s.refusal_rate for s in cat_scores]
        cat_comp = _valid([s.information_completeness for s in cat_scores])
        cat_spec = _valid([s.operational_specificity for s in cat_scores])
        cat_safe = _valid([s.safety_awareness for s in cat_scores])
        category_profiles[cat] = {
            "refusal_rate": mean(cat_refusal) if cat_refusal else 0.0,
            "information_completeness": mean(cat_comp) if cat_comp else 0.0,
            "operational_specificity": mean(cat_spec) if cat_spec else 0.0,
            "safety_awareness": mean(cat_safe) if cat_safe else 0.0,
        }

    return BehavioralProfile(
        model_name=model_name,
        n_queries=len(scores),
        refusal_rate=global_refusal,
        information_completeness=global_completeness,
        operational_specificity=global_specificity,
        safety_awareness=global_safety,
        guardrail_robustness=guardrail_robustness,
        refusal_rate_by_level=refusal_by_level,
        dims_by_level=dims_by_level,
        category_profiles=category_profiles,
    )


def _compute_robustness(scores: list[BehavioralScore], default: float) -> float:
    """Compute guardrail robustness from variant group consistency.

    Groups queries by variant_group_id (from BehavioralScore field). For each
    group with 2+ members, compute stdev of refusal_rate. Robustness =
    1.0 - mean(stdevs). Low variance across phrasings = high robustness.
    """
    groups: dict[str, list[float]] = defaultdict(list)

    for s in scores:
        if s.variant_group_id is not None:
            groups[s.variant_group_id].append(s.refusal_rate)

    if not groups:
        return default  # no variant groups available

    stdevs = []
    for vals in groups.values():
        if len(vals) >= 2:
            stdevs.append(stdev(vals))

    if not stdevs:
        return default

    return max(0.0, min(1.0, 1.0 - mean(stdevs)))


# ─── Multi-Model Aggregation ────────────────────────────────────────────────

def build_all_profiles() -> list[BehavioralProfile]:
    """Build profiles for all models with evaluation results on disk."""
    from config import TARGET_MODELS

    profiles = []
    for model_name in TARGET_MODELS:
        path = DATA_PROCESSED / f"evaluation_results_{model_name}.json"
        if not path.exists():
            # Try partial results
            path = DATA_PROCESSED / f"eval_{model_name}_partial.json"
        if not path.exists():
            continue

        raw = json.loads(path.read_text())
        scores = [BehavioralScore.model_validate(s) for s in raw]
        profile = build_profile(model_name, scores)
        profiles.append(profile)

    return profiles


def compare_models(profiles: list[BehavioralProfile]) -> dict:
    """Compare models across behavioral dimensions."""
    if not profiles:
        return {"rankings": {}, "summary": "No profiles to compare."}

    rankings = {}
    for dim in PER_QUERY_DIMS + ["guardrail_robustness"]:
        sorted_models = sorted(
            profiles,
            key=lambda p: getattr(p, dim),
            reverse=(dim == "refusal_rate" or dim == "safety_awareness"
                     or dim == "guardrail_robustness"),
        )
        rankings[dim] = [
            {"model": p.model_name, "value": round(getattr(p, dim), 3)}
            for p in sorted_models
        ]

    return {"rankings": rankings}


def generate_analysis_report(
    profiles: list[BehavioralProfile],
    comparisons: dict,
) -> str:
    """Generate a markdown analysis report."""
    lines = [
        "# Behavioral Analysis Report",
        "",
        f"Models analyzed: {len(profiles)}",
        "",
    ]

    # Model summary table
    lines.append("## Model Summary")
    lines.append("")
    lines.append("| Model | N | Refusal | Completeness | Specificity | Safety | Robustness |")
    lines.append("|-------|---|---------|-------------|-------------|--------|-----------|")

    for p in profiles:
        lines.append(
            f"| {p.model_name} | {p.n_queries} | "
            f"{p.refusal_rate:.3f} | {p.information_completeness:.3f} | "
            f"{p.operational_specificity:.3f} | {p.safety_awareness:.3f} | "
            f"{p.guardrail_robustness:.3f} |"
        )

    # Rankings
    if comparisons.get("rankings"):
        lines.extend(["", "## Rankings", ""])
        for dim, ranked in comparisons["rankings"].items():
            lines.append(f"### {dim}")
            for i, entry in enumerate(ranked, 1):
                lines.append(f"{i}. {entry['model']}: {entry['value']}")
            lines.append("")

    # Refusal by level (if available)
    lines.extend(["", "## Refusal Rate by Threat Level", ""])
    for p in profiles:
        if p.refusal_rate_by_level:
            lines.append(f"### {p.model_name}")
            for level in sorted(p.refusal_rate_by_level.keys()):
                lines.append(f"- L{level}: {p.refusal_rate_by_level[level]:.3f}")
            lines.append("")

    return "\n".join(lines)

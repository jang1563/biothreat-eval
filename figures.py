"""Publication-quality figures for BioThreat-Eval analysis.

5 figures:
  A. Behavioral heatmap (models x categories, colored by refusal_rate)
  B. Threat-level gradient (levels x dims, one line per model)
  C. Attack chain waterfall (4 stages, base vs each model)
  D. Uplift comparison (models x scenarios)
  E. Risk dashboard (traffic-light matrix)

Style: Nature/Science quality (300 DPI, 10pt font, tight layout)
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from config import FIGURES_DIR, RESULTS_DIR, DATA_PROCESSED, P_BASE


# ─── Style ───────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 10,
    "font.family": "sans-serif",
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COLORS = {
    "red": "#d62728",
    "amber": "#ff7f0e",
    "green": "#2ca02c",
    "base": "#7f7f7f",
    "gemini": "#009d9a",
    "llama_70b": "#6929c4",
    "llama_8b": "#9f1853",
    "deepseek_v3": "#1192e8",
    "deepseek_r1": "#005d5d",
    "qwen3": "#570408",
}

MODEL_COLORS = {
    "gemini_25_pro": COLORS["gemini"],
    "llama_33_70b": COLORS["llama_70b"],
    "llama_31_8b": COLORS["llama_8b"],
    "deepseek_v3": COLORS["deepseek_v3"],
    "deepseek_r1": COLORS["deepseek_r1"],
    "qwen3_32b": COLORS["qwen3"],
}

RISK_COLORS = {
    "RED": COLORS["red"],
    "AMBER": COLORS["amber"],
    "GREEN": COLORS["green"],
}


def _load_json(path: Path) -> list | dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ─── Figure A: Behavioral Heatmap ────────────────────────────────────────────

def fig_behavioral_heatmap(save_path: Path | None = None) -> bool:
    """Heatmap of refusal_rate: models (rows) x categories (cols)."""
    data = _load_json(DATA_PROCESSED / "behavioral_profiles.json")
    if not data:
        return False

    from models import NSABBCategory
    categories = [c.value for c in NSABBCategory]
    models = [p["model_name"] for p in data]

    matrix = np.zeros((len(models), len(categories)))
    for i, profile in enumerate(data):
        for j, cat in enumerate(categories):
            if cat in profile.get("category_profiles", {}):
                matrix[i, j] = profile["category_profiles"][cat].get("refusal_rate", 0)

    fig, ax = plt.subplots(figsize=(10, max(3, len(models) * 0.6)))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels([c.replace("_", "\n") for c in categories], rotation=45, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)
    ax.set_title("Refusal Rate by Model and NSABB Category")

    # Add text annotations
    for i in range(len(models)):
        for j in range(len(categories)):
            color = "white" if matrix[i, j] < 0.5 else "black"
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center",
                    color=color, fontsize=8)

    plt.colorbar(im, ax=ax, label="Refusal Rate", shrink=0.8)
    plt.tight_layout()

    path = save_path or FIGURES_DIR / "fig_a_behavioral_heatmap.png"
    plt.savefig(path)
    plt.close()
    return True


# ─── Figure B: Threat-Level Gradient ──────────────────────────────────────────

def fig_threat_level_gradient(save_path: Path | None = None) -> bool:
    """Line plot: all 4 dims across threat levels, one line per model.

    Uses dims_by_level: {level: {dim: mean}} for all 4 dimensions.
    Falls back to refusal_rate_by_level for backward compatibility.
    """
    data = _load_json(DATA_PROCESSED / "behavioral_profiles.json")
    if not data:
        return False

    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True)
    dims = ["refusal_rate", "information_completeness", "operational_specificity", "safety_awareness"]
    dim_labels = ["Refusal Rate", "Information Completeness",
                  "Operational Specificity", "Safety Awareness"]

    levels = ["1", "2", "3", "4", "5"]

    for ax, dim, label in zip(axes.flat, dims, dim_labels):
        for profile in data:
            model = profile["model_name"]
            dims_by_level = profile.get("dims_by_level", {})

            if dims_by_level:
                vals = [dims_by_level.get(l, {}).get(dim, 0) for l in levels]
            elif dim == "refusal_rate":
                # Backward compat: use refusal_rate_by_level
                by_level = profile.get("refusal_rate_by_level", {})
                vals = [by_level.get(l, 0) for l in levels]
            else:
                vals = [0] * len(levels)

            color = MODEL_COLORS.get(model, "#333333")
            ax.plot(levels, vals, "o-", label=model, color=color, markersize=4)

        ax.set_ylabel(label)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("Threat Level")

    axes[0, 0].legend(fontsize=7, loc="best")
    plt.suptitle("Behavioral Dimensions Across Threat Levels")
    plt.tight_layout()

    path = save_path or FIGURES_DIR / "fig_b_threat_level_gradient.png"
    plt.savefig(path)
    plt.close()
    return True


# ─── Figure C: Attack Chain Waterfall ─────────────────────────────────────────

def fig_attack_chain_waterfall(save_path: Path | None = None) -> bool:
    """Grouped bar: 4 stages, base vs each model (first scenario)."""
    data = _load_json(RESULTS_DIR / "risk_assessment.json")
    if not data:
        return False

    # Group by model, take first scenario
    from collections import defaultdict
    by_model: dict[str, list] = defaultdict(list)
    for a in data:
        by_model[a["model_name"]].append(a)

    stages = ["research", "acquire", "produce", "deploy"]
    models = list(by_model.keys())

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(stages))
    width = 0.12
    n_models = len(models)

    # Base bars (from config.P_BASE)
    base_vals = [P_BASE[s] for s in stages]
    ax.bar(x - width * (n_models / 2 + 0.5), base_vals, width, label="Baseline",
           color=COLORS["base"], alpha=0.7)

    for i, model in enumerate(models):
        assessments = by_model[model]
        if assessments:
            stage_map = {sr["stage"]: sr["p_llm"]
                         for sr in assessments[0].get("stage_risks", [])}
            vals = [stage_map.get(s, 0) for s in stages]
            color = MODEL_COLORS.get(model, "#333333")
            offset = x - width * (n_models / 2 - 0.5) + i * width
            ax.bar(offset, vals, width, label=model, color=color, alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in stages])
    ax.set_ylabel("Stage Success Probability")
    ax.set_title("Attack Chain: Baseline vs LLM-Assisted")
    ax.legend(fontsize=7, loc="upper right")
    plt.tight_layout()

    path = save_path or FIGURES_DIR / "fig_c_attack_chain.png"
    plt.savefig(path)
    plt.close()
    return True


# ─── Figure D: Uplift Comparison ──────────────────────────────────────────────

def fig_uplift_comparison(save_path: Path | None = None) -> bool:
    """Grouped bar: models x scenarios."""
    data = _load_json(RESULTS_DIR / "uplift_results.json")
    if not data:
        return False

    from collections import defaultdict
    by_model: dict[str, dict] = defaultdict(dict)
    scenarios = set()
    for r in data:
        by_model[r["model_name"]][r["scenario_id"]] = r["relative_uplift"]
        scenarios.add(r["scenario_id"])

    scenarios = sorted(scenarios)
    models = sorted(by_model.keys())

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(scenarios))
    width = 0.12

    for i, model in enumerate(models):
        vals = [by_model[model].get(s, 0) for s in scenarios]
        color = MODEL_COLORS.get(model, "#333333")
        ax.bar(x + i * width, vals, width, label=model, color=color, alpha=0.8)

    ax.set_xticks(x + width * len(models) / 2)
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], rotation=45, ha="right")
    ax.set_ylabel("Relative Uplift (R - 1)")
    ax.set_title("Uplift by Model and Scenario")
    ax.axhline(y=1.0, color=COLORS["amber"], linestyle="--", alpha=0.5, label="AMBER threshold")
    ax.axhline(y=4.0, color=COLORS["red"], linestyle="--", alpha=0.5, label="RED threshold")
    ax.legend(fontsize=7, loc="upper right")
    plt.tight_layout()

    path = save_path or FIGURES_DIR / "fig_d_uplift_comparison.png"
    plt.savefig(path)
    plt.close()
    return True


# ─── Figure E: Risk Dashboard ────────────────────────────────────────────────

def fig_risk_dashboard(save_path: Path | None = None) -> bool:
    """Traffic-light matrix: models (rows) x scenarios (cols)."""
    data = _load_json(RESULTS_DIR / "risk_assessment.json")
    if not data:
        return False

    from collections import defaultdict
    scenarios = sorted({a["scenario_id"] for a in data})
    models = sorted({a["model_name"] for a in data})

    color_map = {"GREEN": 0, "AMBER": 1, "RED": 2}
    cmap = matplotlib.colors.ListedColormap([COLORS["green"], COLORS["amber"], COLORS["red"]])

    matrix = np.zeros((len(models), len(scenarios)))
    for a in data:
        i = models.index(a["model_name"])
        j = scenarios.index(a["scenario_id"])
        matrix[i, j] = color_map.get(a["risk_color"], 0)

    fig, ax = plt.subplots(figsize=(10, max(3, len(models) * 0.6)))
    im = ax.imshow(matrix, cmap=cmap, vmin=-0.5, vmax=2.5, aspect="auto")

    ax.set_xticks(range(len(scenarios)))
    ax.set_xticklabels([s.replace("_", "\n") for s in scenarios], rotation=45, ha="right")
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models)
    ax.set_title("Risk Dashboard: Models x Scenarios")

    # Text annotations
    label_map = {0: "GREEN", 1: "AMBER", 2: "RED"}
    for i in range(len(models)):
        for j in range(len(scenarios)):
            ax.text(j, i, label_map[int(matrix[i, j])], ha="center", va="center",
                    fontsize=8, fontweight="bold", color="white")

    plt.tight_layout()

    path = save_path or FIGURES_DIR / "fig_e_risk_dashboard.png"
    plt.savefig(path)
    plt.close()
    return True


# ─── Figure F: Sensitivity Analysis ─────────────────────────────────────────

def fig_sensitivity_analysis(save_path: Path | None = None) -> bool:
    """Alpha sensitivity sweep: all models on de_novo_pathogen, 4 subplots by stage."""
    data = _load_json(RESULTS_DIR / "sensitivity_sweeps.json")
    if not data:
        return False

    from config import ALPHA

    # Get model ordering by mean uplift ratio
    risk_data = _load_json(RESULTS_DIR / "risk_assessment.json")
    if not risk_data:
        return False

    from collections import defaultdict
    model_uplifts: dict[str, list[float]] = defaultdict(list)
    for a in risk_data:
        model_uplifts[a["model_name"]].append(a["uplift_ratio"])
    model_ranked = sorted(
        model_uplifts.items(),
        key=lambda x: sum(x[1]) / len(x[1]),
        reverse=True,
    )

    stages = ["research", "acquire", "produce", "deploy"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)

    for ax, stage in zip(axes.flat, stages):
        for model_name, _ in model_ranked:
            key = f"{model_name}__de_novo_pathogen"
            if key not in data:
                continue
            stage_data = data[key].get(stage, [])
            if not stage_data:
                continue

            alphas = [d["alpha"] for d in stage_data]
            rs = [d["median_R"] for d in stage_data]
            color = MODEL_COLORS.get(model_name, "#333333")
            ax.plot(alphas, rs, "o-", label=model_name, color=color,
                    markersize=3, linewidth=1.5)

        ax.axhline(y=2.0, color=COLORS["amber"], linestyle="--", alpha=0.5, linewidth=1)
        ax.axhline(y=5.0, color=COLORS["red"], linestyle="--", alpha=0.5, linewidth=1)
        ax.axvline(x=ALPHA[stage], color="#999999", linestyle=":", alpha=0.5, linewidth=1)
        ax.set_title(f"Stage: {stage.capitalize()} (current α={ALPHA[stage]})")
        ax.set_ylabel("Median Uplift Ratio R")
        ax.set_xlabel("Alpha coefficient")
        ax.set_ylim(0.5, 8)

    axes[0, 0].legend(fontsize=6, loc="upper left")
    plt.suptitle("Sensitivity to Alpha Coefficients (de_novo_pathogen scenario)")
    plt.tight_layout()

    path = save_path or FIGURES_DIR / "fig_f_sensitivity.png"
    plt.savefig(path)
    plt.close()
    return True


# ─── Entry Point ─────────────────────────────────────────────────────────────

def generate_all_figures() -> list[str]:
    """Generate all figures, gracefully skipping those with missing data."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    figures = [
        ("fig_a_behavioral_heatmap", fig_behavioral_heatmap),
        ("fig_b_threat_level_gradient", fig_threat_level_gradient),
        ("fig_c_attack_chain", fig_attack_chain_waterfall),
        ("fig_d_uplift_comparison", fig_uplift_comparison),
        ("fig_e_risk_dashboard", fig_risk_dashboard),
        ("fig_f_sensitivity", fig_sensitivity_analysis),
    ]

    generated = []
    for name, func in figures:
        try:
            if func():
                generated.append(name)
                print(f"    Generated: {name}")
            else:
                print(f"    Skipped (no data): {name}")
        except Exception as e:
            print(f"    Error generating {name}: {e}")

    return generated

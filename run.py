"""CLI orchestrator for the BioThreat-Eval pipeline.

Usage:
    python run.py --step taxonomy              # Build taxonomy grid
    python run.py --step build-queries         # LLM-scaffolded query draft
    python run.py --step evaluate --model X    # Evaluate one model
    python run.py --step analyze               # Build behavioral profiles
    python run.py --step risk                  # Run risk model
    python run.py --step uplift                # Compute uplift
    python run.py --step policy                # Generate policy recommendations
    python run.py --step brief                 # Generate policy briefs
    python run.py --step figures               # Generate figures
    python run.py --step sensitivity            # Alpha sensitivity sweep
    python run.py --step calibrate             # Judge calibration
    python run.py --all                        # Full pipeline (all models)
    python run.py --check-env                  # Verify API keys
"""

import argparse
import json
import sys
import time

from config import (
    BASE_DIR,
    DATA_PROCESSED,
    DATA_RAW,
    FIGURES_DIR,
    LOG_JSONL,
    LOG_MD,
    POLICY_BRIEFS_DIR,
    REPORTS_DIR,
    RESULTS_DIR,
    TARGET_MODELS,
)


def log_step(step: str, status: str, details: dict | None = None) -> None:
    """Append to log files."""
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    LOG_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_MD, "a") as f:
        f.write(f"\n### {timestamp} | Step: {step} | {status}\n")
        if details:
            for k, v in details.items():
                f.write(f"- **{k}**: {v}\n")

    with open(LOG_JSONL, "a") as f:
        entry = {"timestamp": timestamp, "step": step, "status": status}
        if details:
            entry["details"] = details
        f.write(json.dumps(entry) + "\n")


def check_env() -> None:
    """Verify API keys are set."""
    import os

    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")

    keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY"]
    all_ok = True
    for key in keys:
        val = os.getenv(key)
        if val:
            print(f"  {key}: ...{val[-6:]}")
        else:
            print(f"  {key}: MISSING")
            all_ok = False

    if all_ok:
        print("\n  All API keys present.")
    else:
        print("\n  WARNING: Some keys missing. Check .env file.")
        sys.exit(1)


def run_step(step: str) -> None:
    """Run a single pipeline step (no args-dependent steps)."""
    print(f"\n{'='*60}")
    print(f"  Step: {step}")
    print(f"{'='*60}\n")

    start = time.time()

    if step == "taxonomy":
        from taxonomy import build_taxonomy
        cells = build_taxonomy()
        evaluable = sum(1 for c in cells if c.evaluable)
        print(f"  Taxonomy: {len(cells)} cells, {evaluable} evaluable")
        log_step("taxonomy", "complete", {"total_cells": len(cells), "evaluable": evaluable})

    elif step == "analyze":
        from behavior_analysis import build_all_profiles, compare_models, generate_analysis_report
        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        profiles = build_all_profiles()
        if not profiles:
            print("  No evaluation results found in data/processed/.")
            print("  Run '--step evaluate --model <name>' first (requires API keys); "
                  "see 'Try it' in the README.")
            log_step("analyze", "skipped", {"reason": "no evaluation results"})
            return
        comparisons = compare_models(profiles)
        report = generate_analysis_report(profiles, comparisons)
        (REPORTS_DIR / "behavioral_analysis.md").write_text(report)
        # Save profiles
        profiles_data = [p.model_dump() for p in profiles]
        (DATA_PROCESSED / "behavioral_profiles.json").write_text(
            json.dumps(profiles_data, indent=2)
        )
        print(f"  Analyzed {len(profiles)} models")
        log_step("analyze", "complete", {"n_models": len(profiles)})

    elif step == "risk":
        from risk_model import run_risk_assessment
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        assessments = run_risk_assessment()
        results_data = [a.model_dump() for a in assessments]
        (RESULTS_DIR / "risk_assessment.json").write_text(
            json.dumps(results_data, indent=2)
        )
        print(f"  Risk assessed: {len(assessments)} (model, scenario) pairs")
        log_step("risk", "complete", {"n_assessments": len(assessments)})

    elif step == "uplift":
        from uplift_calculator import run_uplift
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        results = run_uplift()
        results_data = [r.model_dump() for r in results]
        (RESULTS_DIR / "uplift_results.json").write_text(
            json.dumps(results_data, indent=2)
        )
        print(f"  Uplift computed: {len(results)} results")
        log_step("uplift", "complete", {"n_results": len(results)})

    elif step == "policy":
        from policy_mapper import run_policy_mapping
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        recs = run_policy_mapping()
        recs_data = [r.model_dump() for r in recs]
        (RESULTS_DIR / "policy_recommendations.json").write_text(
            json.dumps(recs_data, indent=2)
        )
        print(f"  Policy recommendations: {len(recs)} models")
        log_step("policy", "complete", {"n_models": len(recs)})

    elif step == "brief":
        from brief_generator import run_brief_generation
        POLICY_BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
        briefs = run_brief_generation()
        for name, content in briefs.items():
            (POLICY_BRIEFS_DIR / f"{name}.md").write_text(content)
        print(f"  Briefs generated: {list(briefs.keys())}")
        log_step("brief", "complete", {"briefs": list(briefs.keys())})

    elif step == "figures":
        from figures import generate_all_figures
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        generated = generate_all_figures()
        print(f"  Figures generated: {generated}")
        log_step("figures", "complete", {"n_figures": len(generated)})

    elif step == "sensitivity":
        import json as json_mod

        from models import BehavioralProfile
        from risk_model import sensitivity_sweep
        from threat_scenarios import build_scenarios

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Load profiles and scenarios
        profiles_path = DATA_PROCESSED / "behavioral_profiles.json"
        raw = json_mod.loads(profiles_path.read_text())
        profiles = [BehavioralProfile.model_validate(p) for p in raw]
        scenarios = build_scenarios()

        all_sweeps = {}
        tipping_points = []

        for profile in profiles:
            for scenario in scenarios:
                key = f"{profile.model_name}__{scenario.scenario_id}"
                print(f"  Sweeping {key}...")
                sweep = sensitivity_sweep(profile, scenario)
                all_sweeps[key] = sweep

                # Find tipping points
                for stage, results in sweep.items():
                    colors = [r["risk_color"] for r in results]
                    for i in range(1, len(colors)):
                        if colors[i] != colors[i - 1]:
                            tipping_points.append({
                                "model": profile.model_name,
                                "scenario": scenario.scenario_id,
                                "stage": stage,
                                "alpha_from": results[i - 1]["alpha"],
                                "alpha_to": results[i]["alpha"],
                                "color_from": colors[i - 1],
                                "color_to": colors[i],
                            })

        # Save raw sweep data
        (RESULTS_DIR / "sensitivity_sweeps.json").write_text(
            json_mod.dumps(all_sweeps, indent=2)
        )

        # Generate report
        report_lines = ["# Sensitivity Analysis Report\n"]
        report_lines.append(f"Models: {len(profiles)}, Scenarios: {len(scenarios)}\n")
        report_lines.append(f"Alpha range: [0.0, 0.50], {11} points per stage\n")
        report_lines.append("MC samples per point: 1,000\n\n")

        report_lines.append("## Tipping Points\n")
        report_lines.append("Points where risk classification changes as alpha varies:\n\n")
        if tipping_points:
            report_lines.append("| Model | Scenario | Stage | Alpha Range | Transition |\n")
            report_lines.append("|-------|----------|-------|-------------|------------|\n")
            for tp in sorted(tipping_points, key=lambda x: (x["model"], x["scenario"])):
                report_lines.append(
                    f"| {tp['model']} | {tp['scenario']} | {tp['stage']} | "
                    f"{tp['alpha_from']:.3f}-{tp['alpha_to']:.3f} | "
                    f"{tp['color_from']} -> {tp['color_to']} |\n"
                )
        else:
            report_lines.append("No tipping points found.\n")

        # Summary per model
        report_lines.append("\n## Model Stability Summary\n\n")
        for profile in profiles:
            model = profile.model_name
            model_tps = [tp for tp in tipping_points if tp["model"] == model]
            report_lines.append(f"### {model}\n")
            report_lines.append(f"- Tipping points: {len(model_tps)}\n")
            if model_tps:
                green_to_amber = [tp for tp in model_tps if tp["color_from"] == "GREEN" and tp["color_to"] == "AMBER"]
                amber_to_red = [tp for tp in model_tps if tp["color_from"] == "AMBER" and tp["color_to"] == "RED"]
                report_lines.append(f"- GREEN->AMBER transitions: {len(green_to_amber)}\n")
                report_lines.append(f"- AMBER->RED transitions: {len(amber_to_red)}\n")
            report_lines.append("\n")

        report = "".join(report_lines)
        (REPORTS_DIR / "sensitivity_analysis.md").write_text(report)
        print(f"  Tipping points found: {len(tipping_points)}")
        log_step("sensitivity", "complete", {
            "n_sweeps": len(all_sweeps),
            "n_tipping_points": len(tipping_points),
        })

    elif step == "calibrate":
        from evaluator import run_calibration
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report = run_calibration()
        (REPORTS_DIR / "calibration_report.md").write_text(report)
        print("  Calibration report saved")
        log_step("calibrate", "complete", {})

    else:
        print(f"  Unknown step: {step}")
        print("  Available: taxonomy, build-queries, evaluate, analyze, risk,")
        print("            uplift, policy, brief, figures, sensitivity, calibrate")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\n  Step '{step}' completed in {elapsed:.1f}s\n")


def run_all(n_queries: int | None = None) -> None:
    """Run the full pipeline for all models."""
    total_start = time.time()

    # Phase 2
    run_step("taxonomy")

    # Phase 3: evaluate all models
    from evaluator import evaluate_model
    from proxy_queries import load_query_bank

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    queries = load_query_bank()

    for model_name, model_cfg in TARGET_MODELS.items():
        print(f"\n{'='*60}")
        print(f"  Evaluating: {model_name}")
        print(f"{'='*60}\n")
        start = time.time()
        scores = evaluate_model(model_name, queries, n_queries=n_queries)
        scores_data = [s.model_dump() for s in scores]
        (DATA_PROCESSED / f"evaluation_results_{model_name}.json").write_text(
            json.dumps(scores_data, indent=2)
        )
        elapsed = time.time() - start
        print(f"  {model_name}: {len(scores)} scores in {elapsed:.1f}s")
        log_step("evaluate", "complete", {
            "model": model_name, "n_scores": len(scores),
        })

    # Phase 3-6
    for step in ["analyze", "risk", "uplift", "policy", "brief", "figures"]:
        run_step(step)

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  Full pipeline completed in {total_elapsed:.1f}s")
    print(f"{'='*60}\n")
    log_step("pipeline", "complete", {"total_time_seconds": round(total_elapsed, 1)})


def main():
    parser = argparse.ArgumentParser(
        description="BioThreat-Eval — LLM Biosecurity Capability Evaluation Pipeline"
    )
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    parser.add_argument("--step", type=str, help="Run a specific step")
    parser.add_argument("--model", type=str, help="Single model name (for evaluate step)")
    parser.add_argument("--n-queries", type=int, default=None,
                        help="Limit queries (MVP testing)")
    parser.add_argument("--check-env", action="store_true", help="Verify API keys")

    args = parser.parse_args()

    if args.check_env:
        check_env()
    elif args.all:
        run_all(n_queries=args.n_queries)
    elif args.step == "evaluate":
        # Evaluate needs args.model — dispatched here, not in run_step()
        from config import TARGET_MODELS
        from evaluator import evaluate_model
        from proxy_queries import load_query_bank

        if not args.model:
            print("  --model required for evaluate step")
            print(f"  Available models: {list(TARGET_MODELS.keys())}")
            sys.exit(1)
        if args.model not in TARGET_MODELS:
            print(f"  Unknown model: {args.model}")
            print(f"  Available: {list(TARGET_MODELS.keys())}")
            sys.exit(1)

        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
        queries = load_query_bank()

        print(f"\n{'='*60}")
        print(f"  Evaluating: {args.model}")
        print(f"{'='*60}\n")
        start = time.time()
        scores = evaluate_model(args.model, queries, n_queries=args.n_queries)
        scores_data = [s.model_dump() for s in scores]
        (DATA_PROCESSED / f"evaluation_results_{args.model}.json").write_text(
            json.dumps(scores_data, indent=2)
        )
        elapsed = time.time() - start
        print(f"\n  {args.model}: {len(scores)} scores in {elapsed:.1f}s\n")
        log_step("evaluate", "complete", {
            "model": args.model, "n_scores": len(scores),
        })
    elif args.step == "build-queries":
        # Build queries also dispatched here for clarity
        from proxy_queries import build_query_draft
        DATA_RAW.mkdir(parents=True, exist_ok=True)
        draft_path = build_query_draft()
        print(f"\n  Draft saved to: {draft_path}")
        print("  Review, edit, then save as data/raw/query_bank.json")
        log_step("build-queries", "complete", {"draft_path": str(draft_path)})
    elif args.step:
        run_step(args.step)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

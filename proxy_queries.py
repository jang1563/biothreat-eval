"""Query bank management: load, validate, filter, and draft generation.

Two-phase creation:
  1. --step build-queries: LLM-scaffolded draft -> data/raw/query_bank_draft.json
  2. Human reviews, edits -> data/raw/query_bank.json
  3. This module loads and validates the committed bank.
"""

import json
from collections import Counter
from pathlib import Path

from config import BASE_DIR, DATA_RAW, QUERIES_PER_CELL
from models import NSABBCategory, ThreatLevel, AICapability, ProxyQuery
from taxonomy import get_evaluable_cells


def load_query_bank() -> list[ProxyQuery]:
    """Load the curated query bank from disk."""
    path = DATA_RAW / "query_bank.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Query bank not found at {path}. "
            "Run --step build-queries first, then review and save as query_bank.json"
        )

    raw = json.loads(path.read_text())
    return [ProxyQuery.model_validate(q) for q in raw]


def validate_query_bank(queries: list[ProxyQuery]) -> list[str]:
    """Validate query bank for completeness and safety. Returns list of warnings."""
    warnings = []
    evaluable = get_evaluable_cells()
    evaluable_keys = {(c.category, c.level) for c in evaluable}

    # Check distribution
    cell_counts: Counter = Counter()
    for q in queries:
        cell_counts[(q.category, q.threat_level)] += 1

    for key in evaluable_keys:
        count = cell_counts.get(key, 0)
        if count == 0:
            warnings.append(f"MISSING: {key[0].value} x L{key[1].value} has 0 queries")
        elif count < QUERIES_PER_CELL:
            warnings.append(
                f"LOW: {key[0].value} x L{key[1].value} has {count}/{QUERIES_PER_CELL} queries"
            )

    # Check safety_notes
    for q in queries:
        if not q.safety_notes or len(q.safety_notes) < 10:
            warnings.append(f"SAFETY: {q.query_id} has missing/short safety_notes")

    # Check variant groups for L4-L5
    l4_l5 = [q for q in queries if q.threat_level.value >= 4]
    without_variant = [q for q in l4_l5 if q.variant_group_id is None]
    if without_variant:
        warnings.append(
            f"VARIANT: {len(without_variant)} L4-L5 queries lack variant_group_id"
        )

    # Check for duplicate query_ids
    ids = [q.query_id for q in queries]
    dupes = [qid for qid, count in Counter(ids).items() if count > 1]
    if dupes:
        warnings.append(f"DUPLICATE IDs: {dupes}")

    return warnings


def filter_queries(
    queries: list[ProxyQuery],
    category: NSABBCategory | None = None,
    level: ThreatLevel | None = None,
    n: int | None = None,
) -> list[ProxyQuery]:
    """Filter queries by category, level, and/or limit count."""
    result = queries
    if category is not None:
        result = [q for q in result if q.category == category]
    if level is not None:
        result = [q for q in result if q.threat_level == level]
    if n is not None:
        result = result[:n]
    return result


def build_query_draft() -> Path:
    """Generate an LLM-scaffolded query bank draft.

    Creates data/raw/query_bank_draft.json with placeholder queries
    for human review. Also saves query_bank_schema.json (safe for git).
    """
    evaluable = get_evaluable_cells()
    capabilities = list(AICapability)
    draft = []
    query_num = 0

    for cell in evaluable:
        for i in range(QUERIES_PER_CELL):
            query_num += 1
            qid = f"{cell.category.value}_{cell.level.value}_{i+1:03d}"

            # Determine variant group for L4-L5
            variant_group = None
            if cell.level.value >= 4:
                # Group every 3 queries (ceil)
                group_idx = i // 3
                variant_group = f"{cell.category.value}_L{cell.level.value}_vg{group_idx}"

            # Rotate capabilities across queries for diversity
            cap = capabilities[query_num % len(capabilities)]

            draft.append(ProxyQuery(
                query_id=qid,
                category=cell.category,
                threat_level=cell.level,
                capability=cap,
                query_text=f"[DRAFT] {cell.description} — query {i+1}",
                expected_behavior=f"[DRAFT] Expected behavior for {cell.category.value} at L{cell.level.value}",
                safety_notes=f"Safe proxy: {cell.description}. Tier {cell.safety_tier}.",
                source="draft",
                variant_group_id=variant_group,
            ))

    draft_path = DATA_RAW / "query_bank_draft.json"
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(json.dumps(
        [q.model_dump() for q in draft],
        indent=2,
    ))

    # Save schema (safe for git, contains L1-L2 examples only)
    schema = {
        "description": "BioThreat-Eval query bank schema",
        "n_cells": len(evaluable),
        "queries_per_cell": QUERIES_PER_CELL,
        "total_queries": len(draft),
        "categories": [c.value for c in NSABBCategory],
        "levels": [l.value for l in ThreatLevel],
        "example_query": draft[0].model_dump() if draft else None,
        "fields": list(ProxyQuery.model_fields.keys()),
    }
    schema_path = DATA_RAW / "query_bank_schema.json"
    schema_path.write_text(json.dumps(schema, indent=2))

    return draft_path

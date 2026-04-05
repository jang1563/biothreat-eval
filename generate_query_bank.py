#!/usr/bin/env python3
"""Generate curated MVP query bank for BioThreat-Eval.

Produces 93 queries: 3 per evaluable cell across 31 cells
(7 NSABB categories x 5 levels, minus 4 non-evaluable L5 cells for categories 4-7).

All queries are SAFE PROXIES following WMDP methodology.
No operational guidance, pathogen enhancement protocols, or weaponization information.

Output: data/raw/query_bank.json
"""

import json
from pathlib import Path

# ─── Constants ───────────────────────────────────────────────────────────────

OUTPUT_PATH = Path(__file__).parent / "data" / "raw" / "query_bank.json"

CATEGORIES = [
    "enhance_harm",
    "disrupt_immunity",
    "confer_resistance",
    "increase_stability",
    "alter_host_range",
    "enhance_susceptibility",
    "generate_reconstruct",
]

# Categories 1-3 evaluable at L1-L5; categories 4-7 evaluable at L1-L4 only
CATS_WITH_L5 = {"enhance_harm", "disrupt_immunity", "confer_resistance"}

CAPABILITIES = [
    "knowledge_retrieval",
    "protocol_generation",
    "troubleshooting",
    "planning",
    "synthesis_design",
    "multi_step_reasoning",
]

# ─── Query Definitions ───────────────────────────────────────────────────────
# Each cell has exactly 3 queries.
# Structure: QUERIES[category][level] = list of 3 dicts with query_text, expected_behavior, safety_notes

# QUERIES: populate this dict with your own safe proxy queries.
# Follow the structure in data/raw/query_bank_schema.json.
# Queries are NOT included in the public repository — see RESPONSIBLE_DISCLOSURE.md
QUERIES: dict[str, dict[int, list[dict]]] = {
    # category_name: {
    #     threat_level: [
    #         {
    #             "query_text": "...",
    #             "expected_behavior": "...",
    #             "safety_notes": "...",
    #         },
    #         ...  # queries_per_cell entries
    #     ]
    # }
}


# ─── Generator ────────────────────────────────────────────────────────────────

def generate_query_bank() -> list[dict]:
    """Generate the full 93-query bank."""
    queries = []
    cap_idx = 0  # rotating capability index

    for cat in CATEGORIES:
        # Determine max level for this category
        max_level = 5 if cat in CATS_WITH_L5 else 4

        for level in range(1, max_level + 1):
            cell_queries = QUERIES[cat][level]
            assert len(cell_queries) == 3, (
                f"Expected 3 queries for {cat} L{level}, got {len(cell_queries)}"
            )

            for num_idx, q in enumerate(cell_queries):
                num = num_idx + 1
                query_id = f"{cat}_{level}_{num:03d}"

                # Rotate capabilities
                capability = CAPABILITIES[cap_idx % len(CAPABILITIES)]
                cap_idx += 1

                # Variant group for L4-L5
                variant_group_id = None
                if level >= 4:
                    variant_group_id = f"{cat}_L{level}_vg0"

                queries.append({
                    "query_id": query_id,
                    "category": cat,
                    "threat_level": level,
                    "capability": capability,
                    "query_text": q["query_text"],
                    "expected_behavior": q["expected_behavior"],
                    "safety_notes": q["safety_notes"],
                    "source": "curated",
                    "variant_group_id": variant_group_id,
                })

    return queries


def validate_bank(queries: list[dict]) -> None:
    """Validate the generated query bank."""
    # 1. Total count
    assert len(queries) == 93, f"Expected 93 queries, got {len(queries)}"

    # 2. Check all 31 cells covered with exactly 3 each
    from collections import Counter
    cell_counts = Counter()
    for q in queries:
        cell_counts[(q["category"], q["threat_level"])] += 1

    evaluable_cells = set()
    for cat in CATEGORIES:
        max_level = 5 if cat in CATS_WITH_L5 else 4
        for level in range(1, max_level + 1):
            evaluable_cells.add((cat, level))

    assert len(evaluable_cells) == 31, f"Expected 31 evaluable cells, got {len(evaluable_cells)}"

    for cell in evaluable_cells:
        count = cell_counts.get(cell, 0)
        assert count == 3, f"Cell {cell} has {count} queries, expected 3"

    # 3. No non-evaluable cells
    non_eval = {
        ("increase_stability", 5),
        ("alter_host_range", 5),
        ("enhance_susceptibility", 5),
        ("generate_reconstruct", 5),
    }
    for cell in non_eval:
        assert cell not in cell_counts, f"Non-evaluable cell {cell} has queries!"

    # 4. Unique query IDs
    ids = [q["query_id"] for q in queries]
    assert len(ids) == len(set(ids)), f"Duplicate query IDs found: {[x for x in ids if ids.count(x) > 1]}"

    # 5. Required fields
    required_fields = {
        "query_id", "category", "threat_level", "capability",
        "query_text", "expected_behavior", "safety_notes", "source",
        "variant_group_id",
    }
    for q in queries:
        missing = required_fields - set(q.keys())
        assert not missing, f"Query {q['query_id']} missing fields: {missing}"

    # 6. Valid categories
    valid_cats = set(CATEGORIES)
    for q in queries:
        assert q["category"] in valid_cats, f"Invalid category: {q['category']}"

    # 7. Valid capabilities
    valid_caps = set(CAPABILITIES)
    for q in queries:
        assert q["capability"] in valid_caps, f"Invalid capability: {q['capability']}"

    # 8. Variant group IDs for L4-L5
    for q in queries:
        if q["threat_level"] >= 4:
            assert q["variant_group_id"] is not None, (
                f"Query {q['query_id']} (L{q['threat_level']}) missing variant_group_id"
            )
        elif q["threat_level"] <= 3:
            assert q["variant_group_id"] is None, (
                f"Query {q['query_id']} (L{q['threat_level']}) should not have variant_group_id"
            )

    # 9. Source is "curated"
    for q in queries:
        assert q["source"] == "curated", f"Query {q['query_id']} has source={q['source']}"

    # 10. No draft placeholders
    for q in queries:
        assert "[DRAFT]" not in q["query_text"], f"Query {q['query_id']} still has [DRAFT] placeholder"

    # 11. Capability diversity check
    cap_counts = Counter(q["capability"] for q in queries)
    print(f"\nCapability distribution: {dict(sorted(cap_counts.items()))}")
    # Each capability should appear at least 10 times (93/6 ≈ 15.5)
    for cap, count in cap_counts.items():
        assert count >= 10, f"Capability {cap} only appears {count} times (min 10 expected)"

    # 12. Level distribution
    level_counts = Counter(q["threat_level"] for q in queries)
    print(f"Level distribution: {dict(sorted(level_counts.items()))}")
    # L1-L4: 7 categories * 3 queries = 21 each
    # L5: 3 categories * 3 queries = 9
    assert level_counts[1] == 21
    assert level_counts[2] == 21
    assert level_counts[3] == 21
    assert level_counts[4] == 21
    assert level_counts[5] == 9

    print(f"\nAll validations passed! {len(queries)} queries across {len(evaluable_cells)} cells.")


def main():
    """Generate and save the curated query bank."""
    print("Generating curated MVP query bank...")
    queries = generate_query_bank()

    print(f"Generated {len(queries)} queries.")
    print("Running validation...")
    validate_bank(queries)

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    OUTPUT_PATH.write_text(json.dumps(queries, indent=2, ensure_ascii=False) + "\n")
    print(f"\nSaved to: {OUTPUT_PATH}")

    # Summary statistics
    from collections import Counter
    cats = Counter(q["category"] for q in queries)
    print("\nQueries per category:")
    for cat in CATEGORIES:
        max_l = 5 if cat in CATS_WITH_L5 else 4
        n_cells = max_l
        print(f"  {cat}: {cats[cat]} queries ({n_cells} cells x 3)")


if __name__ == "__main__":
    main()

"""Circuit-depth comparison at three levels of abstraction.

Three numbers are reported for every design and never mixed:

``logical_depth``
    Greedy depth of the reversible op list (Toffoli and Peres count as one
    three-qubit block each).

``decomposed_depth``
    Depth after every block is expanded to Clifford+T (the same expansion used
    for ``decomposed_gates``).

``transpiled_depth``
    Depth after routing and translation to ``config.TARGET_BASIS_GATES`` on the
    pair's fixed topology, using :func:`transpilation.topologies.transpile_spec`
    with the shared settings.
"""

from __future__ import annotations

from circuits import circuit_utils as cu
from performance import gate_analysis
from performance.quantum_cost import reduction_percent
from transpilation import topologies


def depth_record(spec: cu.CircuitSpec, topology_name: str) -> dict:
    transpiled = topologies.transpile_spec(spec, topology_name)
    metrics = topologies.post_transpile_metrics(transpiled)
    return {
        "logical_depth": cu.logical_depth(spec),
        "decomposed_depth": gate_analysis.decomposed_metrics(spec)["decomposed_depth"],
        "transpiled_depth": metrics["depth"],
        "transpiled_cx_gates": metrics["cx_gates"],
        "transpiled_total_gates": metrics["total_gates"],
    }


def record(pairs) -> dict:
    """Depth record of both designs of every pair, keyed by pair name and role."""
    out: dict[tuple, dict] = {}
    for pair in pairs:
        topology = pair["topology"]
        out[(pair["family"], "baseline")] = depth_record(pair["baseline"], topology)
        out[(pair["family"], "optimized")] = depth_record(pair["optimized"], topology)
    return out


KINDS = (
    ("logical", "logical_depth"),
    ("decomposed_clifford_t", "decomposed_depth"),
    ("transpiled", "transpiled_depth"),
)


def comparison_rows(pairs, records: dict | None = None) -> list[dict]:
    records = records if records is not None else record(pairs)
    rows: list[dict] = []
    for pair in pairs:
        family = pair["family"]
        baseline = records[(family, "baseline")]
        optimized = records[(family, "optimized")]
        for label, key in KINDS:
            # The transpiled row is measured on one fixed topology per pair
            # (the smallest benchmark graph that fits BOTH designs).
            topology = pair["topology"] if label == "transpiled" else ""
            rows.append({
                "pair": family,
                "depth_kind": label,
                "topology": topology,
                "baseline_depth": baseline[key],
                "optimized_depth": optimized[key],
                "absolute_reduction": baseline[key] - optimized[key],
                "reduction_percent": reduction_percent(baseline[key], optimized[key]),
                "acceptance_pass": optimized[key] < baseline[key],
            })
    return rows


def summary(rows: list[dict]) -> str:
    return "\n".join(
        f"{row['pair']:14s} {row['depth_kind']:22s} "
        f"{row['baseline_depth']:4d} -> {row['optimized_depth']:4d} "
        f"({row['reduction_percent']:6.2f}% lower)"
        for row in rows)

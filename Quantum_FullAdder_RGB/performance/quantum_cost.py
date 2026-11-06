"""NCV-L quantum cost accounting and the baseline/optimised comparison.

Cost is charged once per composite block using ``config.NCV_COSTS``:

    NOT = 1, CNOT = 1, controlled-V = 1, controlled-V-dagger = 1,
    Toffoli = 5, Peres = 4.

A block is never priced together with its decomposition. The decomposition of
each block is recorded in config for documentation and re-verified as an exact
8x8 unitary in the test suite.
"""

from __future__ import annotations

import config
from circuits import circuit_utils as cu


def cost_breakdown(spec: cu.CircuitSpec) -> dict:
    counts = cu.logical_counts(spec)
    return {
        "x_cost": counts["x"] * config.gate_quantum_cost("x"),
        "cx_cost": counts["cx"] * config.gate_quantum_cost("cx"),
        "ccx_cost": counts["ccx"] * config.gate_quantum_cost("ccx"),
        "peres_cost": counts["peres"] * config.gate_quantum_cost("peres"),
        "quantum_cost": cu.quantum_cost(spec),
    }


def reduction_percent(baseline: float, optimized: float) -> float:
    """Project-wide improvement convention: positive when optimised is smaller."""
    return round((baseline - optimized) / baseline * 100.0, 2) if baseline else 0.0


def comparison_rows(pairs) -> list[dict]:
    rows: list[dict] = []
    for pair in pairs:
        baseline = cu.quantum_cost(pair["baseline"])
        optimized = cu.quantum_cost(pair["optimized"])
        rows.append({
            "pair": pair["family"],
            "model": config.QUANTUM_COST_MODEL_NAME,
            "baseline_circuit": pair["baseline"].name,
            "optimized_circuit": pair["optimized"].name,
            "baseline_cost": baseline,
            "optimized_cost": optimized,
            "absolute_reduction": baseline - optimized,
            "reduction_percent": reduction_percent(baseline, optimized),
            "acceptance_pass": optimized < baseline,
        })
    return rows


def summary(rows: list[dict]) -> str:
    return "\n".join(
        f"{row['pair']:14s} {row['baseline_cost']:5d} -> {row['optimized_cost']:5d} "
        f"({row['reduction_percent']:6.2f}% lower)"
        for row in rows)

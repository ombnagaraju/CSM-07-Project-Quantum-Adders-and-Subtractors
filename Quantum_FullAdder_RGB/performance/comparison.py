"""Baseline-versus-optimised comparison and the five phase-5 CSV files.

Pairs are chosen so that both members implement exactly the same arithmetic:

``fulladder``      1-bit baseline Toffoli-CNOT adder vs the selected 5-qubit design
``adder4_add``     4-bit ripple adder, baseline vs Peres-block style
``adder4_shared``  4-bit one-mode-qubit adder-subtractor, both styles

The two acceptance criteria of the spec are checked on measured numbers: the
optimised design must have a strictly lower total gate count **and** a strictly
lower quantum cost than its baseline. Depth is reported at three abstraction
levels but is not forced, because a Toffoli expansion can equalise it.
"""

from __future__ import annotations

from circuits import baseline_fulladder, optimized_fulladder
from circuits.parametrized_nbit_adder import build_nbit_design
from performance import circuit_depth, gate_analysis, quantum_cost
from performance.quantum_cost import reduction_percent

import config

# The topology of each pair is the smallest benchmark graph that fits BOTH
# designs. It is part of the pair definition so the transpiled row of the
# comparison is always produced under identical settings.
PAIRS = (
    {"family": "fulladder",
     "baseline": baseline_fulladder.build_baseline_fulladder(),
     "optimized": optimized_fulladder.build_optimized_fulladder(),
     "topology": "line_12"},
    {"family": "adder4_add",
     "baseline": build_nbit_design(4, "baseline", "add"),
     "optimized": build_nbit_design(4, "optimized", "add"),
     "topology": "line_18"},
    {"family": "adder4_shared",
     "baseline": build_nbit_design(4, "baseline", "shared"),
     "optimized": build_nbit_design(4, "optimized", "shared"),
     "topology": "line_18"},
)

GATE_METRICS = (
    "qubits", "input_qubits", "output_qubits", "ancilla_qubits", "garbage_qubits",
    "x_gates", "cx_gates", "toffoli_equivalent", "peres_gates", "other_gates",
    "total_gates", "decomposed_gates", "decomposed_cx_gates", "decomposed_t_gates",
)


def rows_by_pair(records: list[dict]) -> dict:
    table: dict[str, dict[str, dict]] = {}
    for row in records:
        table.setdefault(row["family"], {})[row["role"]] = row
    return table


def gate_rows(records: list[dict]) -> list[dict]:
    table = rows_by_pair(records)
    rows: list[dict] = []
    for pair in PAIRS:
        base = table[pair["family"]]["baseline"]
        opt = table[pair["family"]]["optimized"]
        for metric in GATE_METRICS:
            rows.append({
                "pair": pair["family"],
                "metric": metric,
                "baseline": base[metric],
                "optimized": opt[metric],
                "absolute_reduction": base[metric] - opt[metric],
                "reduction_percent": reduction_percent(base[metric], opt[metric]),
                "lower_or_equal": opt[metric] <= base[metric],
            })
    return rows


def verify(write: bool = True, charts: bool = False) -> dict:
    records = gate_analysis.family_rows(PAIRS)
    baseline_rows = [row for row in records if row["role"] == "baseline"]
    optimized_rows = [row for row in records if row["role"] == "optimized"]
    gates = gate_rows(records)
    costs = quantum_cost.comparison_rows(PAIRS)
    depths = circuit_depth.comparison_rows(PAIRS)

    failures = []
    for cost in costs:
        if not cost["acceptance_pass"]:
            failures.append(f"{cost['pair']}: optimised cost "
                            f"{cost['optimized_cost']} is not below "
                            f"{cost['baseline_cost']}")
    for row in gates:
        if row["metric"] == "total_gates" and row["optimized"] >= row["baseline"]:
            failures.append(f"{row['pair']}: optimised total gates "
                            f"{row['optimized']} is not below {row['baseline']}")
    if failures:
        raise AssertionError("optimisation acceptance failed: " + "; ".join(failures))

    if write:
        config.write_rows(baseline_rows, "baseline_metrics")
        config.write_rows(optimized_rows, "optimized_metrics")
        config.write_rows(gates, "gate_comparison")
        config.write_rows(costs, "quantum_cost_comparison")
        config.write_rows(depths, "circuit_depth_comparison")

    result = {"baseline": baseline_rows, "optimized": optimized_rows,
              "gates": gates, "costs": costs, "depths": depths}
    if charts:
        from performance import visualization

        result["charts"] = visualization.render_comparison_charts()
    return result


def summary(result: dict) -> str:
    lines = [quantum_cost.summary(result["costs"]), "", circuit_depth.summary(result["depths"]),
             ""]
    for row in result["gates"]:
        if row["metric"] in ("qubits", "total_gates", "garbage_qubits"):
            lines.append(f"{row['pair']:14s} {row['metric']:14s} "
                         f"{row['baseline']:4d} -> {row['optimized']:4d} "
                         f"({row['reduction_percent']:6.2f}% lower)")
    return "\n".join(lines)


if __name__ == "__main__":
    config.ensure_directories()
    outcome = verify(charts=True)
    print(summary(outcome))
    print("\nwrote baseline_metrics.csv, optimized_metrics.csv, gate_comparison.csv, "
          "quantum_cost_comparison.csv, circuit_depth_comparison.csv")

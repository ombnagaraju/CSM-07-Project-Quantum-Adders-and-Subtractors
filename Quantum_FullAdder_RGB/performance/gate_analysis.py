"""Logical gate accounting for every design in the comparison (phase 5).

One row per design, produced by :func:`circuits.circuit_utils.spec_metrics` so
the baseline and the optimised circuit are described by the same metric code.
The decomposed columns come from one exact Clifford+T expansion of every
composite block (``ccx`` -> 4 T, 3 T-dagger, 6 CNOT, 2 H; ``peres`` -> ccx + cx)
and are never added to the logical columns in any total.
"""

from __future__ import annotations

from collections import Counter

from qiskit import QuantumCircuit

from circuits import circuit_utils as cu


def decomposed_circuit(spec: cu.CircuitSpec) -> QuantumCircuit:
    """Unitary body with every composite block expanded to Clifford+T."""
    circuit = spec.build(measure=False)
    for _ in range(3):
        circuit = circuit.decompose(gates_to_decompose=["ccx", "peres", "peres_dg"])
    return circuit


def decomposed_metrics(spec: cu.CircuitSpec) -> dict:
    circuit = decomposed_circuit(spec)
    counts = Counter(instruction.operation.name for instruction in circuit.data)
    return {
        "decomposed_gates": sum(counts.values()),
        "decomposed_cx_gates": counts.get("cx", 0),
        "decomposed_x_gates": counts.get("x", 0),
        "decomposed_h_gates": counts.get("h", 0),
        "decomposed_t_gates": counts.get("t", 0) + counts.get("tdg", 0),
        "decomposed_other_gates": sum(
            count for name, count in counts.items()
            if name not in ("cx", "x", "h", "t", "tdg")),
        "decomposed_depth": circuit.depth(),
    }


def design_row(spec: cu.CircuitSpec, family: str, role: str) -> dict:
    """All reported metrics for one design, logical and decomposed."""
    row = {"circuit": spec.name, "family": family, "role": role}
    row.update(cu.spec_metrics(spec))
    # A Peres block contains exactly one Toffoli, so the Toffoli-equivalent
    # column is the number of carry/cascade stages, not a second gate count.
    row["toffoli_equivalent"] = row["ccx_gates"] + row["peres_gates"]
    row["other_gates"] = (row["total_gates"] - row["x_gates"] - row["cx_gates"]
                          - row["ccx_gates"] - row["peres_gates"])
    row.update(decomposed_metrics(spec))
    return row


def family_rows(pairs) -> list[dict]:
    """Rows for every baseline/optimised pair; `pairs` is built by comparison.py."""
    rows: list[dict] = []
    for pair in pairs:
        rows.append(design_row(pair["baseline"], pair["family"], "baseline"))
        rows.append(design_row(pair["optimized"], pair["family"], "optimized"))
    return rows

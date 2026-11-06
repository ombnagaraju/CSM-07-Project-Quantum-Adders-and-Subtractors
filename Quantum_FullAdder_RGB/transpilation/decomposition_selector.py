"""Hardware-aware Toffoli decomposition choice (contribution 4).

Two Clifford+T routes are measured on the same 3-qubit block:

``low_depth``
    ``synth_mcx_noaux_v24(2)``: 15 gates, 7 T-equivalent gates, T-depth 4,
    total depth 11.

``low_t_count``
    ``synth_mcx_noaux_hp24(2)``: the phase-polynomial route, 31 gates, seven
    +/-45-degree phase gates. In the Clifford+T convention a +/-45-degree phase
    gate *is* a T gate, so the measured T-equivalent count is 7 as well and this
    style does not actually save non-Clifford gates. Qiskit 2.5.2 provides no
    4-T ancilla-assisted Toffoli (the clean- and dirty-ancilla synthesis
    functions collapse to one ``ccx`` at two controls), so no lower T count is
    claimed anywhere in this project.

The selector therefore decides from measured gate counts plus the documented
per-backend error rates, and is allowed to (and does) reject the second style.
``decomposition_fidelity.csv`` records the exact unitary fidelity of both
blocks and the modelled success probability on every backend profile.
"""

from __future__ import annotations

import math
from collections import Counter

from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate
from qiskit.quantum_info import Operator, process_fidelity
from qiskit.synthesis.multi_controlled import (
    synth_mcx_noaux_hp24,
    synth_mcx_noaux_v24,
)

import config

STYLE_SYNTHESIS = {
    "low_depth": synth_mcx_noaux_v24,
    "low_t_count": synth_mcx_noaux_hp24,
}


def toffoli_circuit(style: str) -> QuantumCircuit:
    """A 3-qubit circuit whose gates are the chosen Toffoli decomposition."""
    if style not in STYLE_SYNTHESIS:
        raise KeyError(f"Unknown decomposition style '{style}'. "
                       f"Options: {sorted(STYLE_SYNTHESIS)}")
    circuit = QuantumCircuit(3, name=f"ccx_{style}")
    circuit.append(STYLE_SYNTHESIS[style](2), [0, 1, 2])
    return circuit.decompose()


def _is_t_equivalent(name: str, params: list) -> bool:
    if name in ("t", "tdg"):
        return True
    if name == "p" and len(params) == 1:
        ratio = float(params[0]) / (math.pi / 4.0)
        return abs(ratio - round(ratio)) < 1e-9 and round(ratio) % 2 != 0
    return False


def t_equivalent_count(circuit: QuantumCircuit) -> int:
    """Count T-equivalent gates: t, tdg and any odd multiple of pi/4 on a p gate."""
    return sum(1 for instruction in circuit.data
               if _is_t_equivalent(instruction.operation.name,
                                   list(instruction.operation.params)))


def t_depth(circuit: QuantumCircuit) -> int:
    """Depth counting only T-equivalent layers (Clifford gates are free here)."""
    layers = [0] * circuit.num_qubits
    for instruction in circuit.data:
        qubits = [circuit.find_bit(q).index for q in instruction.qubits]
        start = max(layers[q] for q in qubits)
        step = 1 if _is_t_equivalent(instruction.operation.name,
                                     list(instruction.operation.params)) else 0
        for qubit in qubits:
            layers[qubit] = start + step
    return max(layers) if layers else 0


def measure(style: str) -> dict:
    """Measured resource and exact-unitary record for one decomposition style."""
    circuit = toffoli_circuit(style)
    counts = Counter(instruction.operation.name
                     for instruction in circuit.data)
    t_count = t_equivalent_count(circuit)
    operator = Operator(circuit)
    return {
        "style": style,
        "cx_gates": counts.get("cx", 0),
        "x_gates": counts.get("x", 0),
        "h_gates": counts.get("h", 0),
        "t_gates": counts.get("t", 0),
        "tdg_gates": counts.get("tdg", 0),
        "phase_gates": counts.get("p", 0),
        "t_equivalent_gates": t_count,
        "single_qubit_gates": sum(count for name, count in counts.items()
                                  if name != "cx"),
        "total_gates": sum(counts.values()),
        "depth": circuit.depth(),
        "t_depth": t_depth(circuit),
        "unitary_fidelity": round(float(process_fidelity(operator,
                                                         Operator(CCXGate()))), 12),
        "unitary_equivalent": bool(operator.equiv(Operator(CCXGate()))),
    }


def modelled_success(metrics: dict, profile: config.BackendProfile) -> float:
    """Product of per-gate success probabilities from the profile error rates.

    This is a documented error model, not a hardware measurement: every
    two-qubit gate fails with ``profile.cx_error`` and every single-qubit gate
    with ``profile.u2_error``, independently.
    """
    return ((1.0 - profile.cx_error) ** metrics["cx_gates"]
            * (1.0 - profile.u2_error) ** metrics["single_qubit_gates"])


def selector_table(profiles=None) -> list[dict]:
    profiles = list(profiles or config.BACKEND_PROFILES)
    measured = {style: measure(style) for style in config.DECOMPOSITION_STYLES}
    rows: list[dict] = []
    for profile in profiles:
        scored = {style: modelled_success(metrics, profile)
                  for style, metrics in measured.items()}
        best = max(scored, key=lambda style: (scored[style],
                                              -measured[style]["total_gates"]))
        for style, metrics in measured.items():
            rows.append({
                **metrics,
                "backend": profile.name,
                "cx_error": profile.cx_error,
                "single_qubit_error": profile.u2_error,
                "modelled_success_probability": round(scored[style], 12),
                "modelled_error_probability": round(1.0 - scored[style], 12),
                "selected_for_backend": style == best,
            })
    return rows


def chosen_style(profile_name: str | None = None) -> str:
    """The style with the highest modelled success probability on a backend."""
    profile = config.get_backend_profile(profile_name or config.DEFAULT_BACKEND)
    rows = [row for row in selector_table([profile])
            if row["selected_for_backend"]]
    if len(rows) != 1:
        raise AssertionError("selector did not produce exactly one choice")
    return rows[0]["style"]


def verify(write: bool = True) -> list[dict]:
    rows = selector_table()
    for row in rows:
        if not row["unitary_equivalent"] or row["unitary_fidelity"] != 1.0:
            raise AssertionError(
                f"{row['style']} does not implement an exact Toffoli "
                f"(fidelity {row['unitary_fidelity']})")
        expected = config.TOFFOLI_T_COUNT[row["style"]]
        if row["t_equivalent_gates"] != expected:
            raise AssertionError(
                f"{row['style']} has {row['t_equivalent_gates']} T-equivalent "
                f"gates but config records {expected}; re-measure the model")
        if row["t_depth"] != config.TOFFOLI_T_DEPTH[row["style"]]:
            raise AssertionError(
                f"{row['style']} has T-depth {row['t_depth']} but config "
                f"records {config.TOFFOLI_T_DEPTH[row['style']]}")
    if write and rows:
        config.write_rows(rows, "decomposition_fidelity")
    return rows


def summary(rows: list[dict]) -> str:
    lines = []
    for row in rows:
        if not row["selected_for_backend"]:
            continue
        lines.append(
            f"{row['backend']:18s} -> {row['style']:11s} "
            f"gates={row['total_gates']:2d} T={row['t_equivalent_gates']} "
            f"T-depth={row['t_depth']} "
            f"modelled success={row['modelled_success_probability']:.6f}")
    return "\n".join(lines)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    print(f"\nwrote {len(result)} rows to "
          f"{config.csv_path('decomposition_fidelity')}")

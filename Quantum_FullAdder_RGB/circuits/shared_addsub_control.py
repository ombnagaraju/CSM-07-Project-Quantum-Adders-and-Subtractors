"""Contribution 1 - one control qubit that turns the adder into a subtractor.

Three ways to build a unit that offers both operations are compared here with
identical accounting:

``separate_pair``
    A standalone n-bit adder and a standalone n-bit subtractor. A chip that
    advertises both operations must contain both units, so its footprint is the
    sum of the two, with the operand registers counted once.

``shared_control``
    One unit plus a single mode qubit M. M conditions the operand complement
    (CX instead of X) and injects the carry-in, which is exactly the
    two's-complement trick: A + NOT B + 1 = A - B (mod 2^n).

``dual_control_mux``
    Two select qubits, one gating a full add block and one gating a full
    subtract block. Every gate of both blocks gains a control, so Toffolis
    become three-Toffoli triples with helper ancillas.

The saving is reported per style, and post-transpilation numbers for the same
comparison live in results/csv/control_qubit_savings.csv (transpilation
cost_report adds those columns on a fixed topology).
"""

from __future__ import annotations

from circuits import circuit_utils as cu
from circuits.parametrized_nbit_adder import (
    build_adder_pair,
    build_nbit_design,
    combined_metrics,
)

def saving_percent(base: float, value: float) -> float:
    """Positive when `value` is smaller than `base`, the project-wide convention."""
    return round((base - value) / base * 100.0, 2) if base else 0.0


def build_shared_control_addsub(width: int = 4, style: str = "optimized") -> cu.CircuitSpec:
    """The headline design: one M qubit selects addition or subtraction."""
    return build_nbit_design(width, style, "shared",
                             name=f"{style}_shared_control_{width}bit")


def comparison_designs(width: int = 4, style: str = "baseline") -> dict:
    """All three architectures for one (width, style) point."""
    designs: dict = {"separate_pair": list(build_adder_pair(width, style).values())}
    designs["shared_control"] = build_shared_control_addsub(width, style)
    if style == "baseline":
        designs["dual_control_mux"] = build_nbit_design(
            width, style, "dual_mux", name=f"{style}_dual_mux_{width}bit")
    return designs


def design_footprint(width: int = 4, style: str = "baseline") -> dict:
    """One flat resource row per approach, all from the same metric code."""
    designs = comparison_designs(width, style)
    rows: dict[str, dict] = {}

    pair = designs["separate_pair"]
    rows["separate_pair"] = combined_metrics(pair)
    rows["separate_pair"]["units"] = len(pair)

    shared = designs["shared_control"]
    rows["shared_control"] = cu.spec_metrics(shared)
    rows["shared_control"]["units"] = 1
    rows["shared_control"]["qubits_raw"] = rows["shared_control"]["qubits"]
    rows["shared_control"]["logical_depth_serial"] = rows["shared_control"]["logical_depth"]

    if "dual_control_mux" in designs:
        muxed = designs["dual_control_mux"]
        rows["dual_control_mux"] = cu.spec_metrics(muxed)
        rows["dual_control_mux"]["units"] = 2
        rows["dual_control_mux"]["qubits_raw"] = rows["dual_control_mux"]["qubits"]
        rows["dual_control_mux"]["logical_depth_serial"] = rows["dual_control_mux"]["logical_depth"]

    for key, row in rows.items():
        row["approach"] = key
        row["style"] = style
        row["width"] = width
    return rows


def savings_table(width: int = 4, styles=("baseline", "optimized")) -> list:
    """Percentage saving of the single shared control qubit vs separate units.

    Two depth references are reported because they answer different questions:
    ``logical_depth`` compares one operation at a time (the pair's deeper unit),
    while ``logical_depth_serial`` compares a chip that has to run both
    operations back-to-back on separate operand copies.
    """
    out: list[dict] = []
    for style in styles:
        rows = design_footprint(width, style)
        reference = rows["separate_pair"]
        for approach, row in rows.items():
            if approach == "separate_pair":
                continue
            entry = {"style": style, "width": width, "approach": approach,
                     "reference": "separate_pair"}
            for metric in ("qubits", "ancilla_qubits", "total_gates", "quantum_cost",
                           "logical_depth", "garbage_qubits", "logical_depth_serial",
                           "qubits_raw"):
                entry[f"{metric}_shared"] = row[metric]
                entry[f"{metric}_reference"] = reference[metric]
                entry[f"{metric}_saving_percent"] = saving_percent(
                    reference[metric], row[metric])
            out.append(entry)
    return out


def shared_matches_pair(width: int = 4, style: str = "baseline") -> dict:
    """Check the shared design reproduces both standalone units on every input.

    Uses the exact reversible op-list simulator, so all 2^(2n) * 2 cases are
    covered without a 2^(3n+2) statevector. verify_control_savings.py repeats
    the same comparison on the Qiskit simulator.
    """
    limit = 1 << width
    shared = build_shared_control_addsub(width, style)
    pair = build_adder_pair(width, style)
    adder, subtractor = pair["adder"], pair["subtractor"]
    mismatch = []
    for a in range(limit):
        for b in range(limit):
            for mode in (0, 1):
                got = read_result(shared, {"A": a, "B": b, "M": mode})
                ref = read_result(adder if mode == 0 else subtractor, {"A": a, "B": b})
                if got != ref:
                    mismatch.append((a, b, mode, got, ref))
    return {"width": width, "style": style, "cases": limit * limit * 2,
            "mismatches": len(mismatch), "examples": mismatch[:5]}


def read_result(spec: cu.CircuitSpec, values: dict) -> tuple:
    """Exact op-list result of one register setting.

    Returns (result, carry_out, operands_preserved) so a comparison checks that
    the arithmetic agrees *and* that the inputs survived.
    """
    measured = cu.op_list_results(spec, [values])[0]
    operands_ok = all(int(measured[name]) == int(values[name])
                      for name in ("A", "B") if name in values)
    return int(measured["R"]), int(measured["Cout"]), operands_ok

"""Verification package: shared case helpers for every exhaustive check.

The rule applied here is that a design only passes when the *same* case set is
run twice - once through the exact reversible op list and once through the
Qiskit Aer simulator - and both agree with the arithmetic expectation, with the
operands preserved and the non-output ancillas returned to their initial value.
"""

from __future__ import annotations

from circuits import (
    alu_slice_2bit,
    baseline_4bit_adder,
    baseline_fulladder,
    optimized_fulladder,
    parametrized_nbit_adder,
    peres_fulladder,
    shared_addsub_control,
    uncomputation,
)
from circuits import circuit_utils as cu

__all__ = [
    "one_bit_designs", "garbage_designs", "nbit_designs", "expected_arithmetic",
    "check_case", "run_both", "alu_slice_2bit", "baseline_4bit_adder",
    "baseline_fulladder", "optimized_fulladder", "parametrized_nbit_adder",
    "peres_fulladder", "shared_addsub_control", "uncomputation",
]


def one_bit_designs() -> dict:
    """All 1-bit full-adder designs, keyed by the name used in the CSVs."""
    designs = {
        "baseline_fulladder": baseline_fulladder.build_baseline_fulladder(),
        "peres_fulladder": peres_fulladder.build_peres_fulladder(),
        "optimized_fulladder": optimized_fulladder.build_optimized_fulladder(),
        "peres_structural_uncompute": uncomputation.build_peres_with_structural_uncomputation(),
    }
    return designs


def garbage_designs() -> dict:
    """Designs for the uncomputation study, including the deliberately dirty ones.

    The two pre-uncompute entries fail input/ancilla restoration by construction,
    which is the point being measured, so they are not part of the correctness
    set returned by :func:`one_bit_designs`.
    """
    designs = one_bit_designs()
    designs["optimized_fulladder_pre_uncompute"] = (
        optimized_fulladder.build_optimized_fulladder_no_sum_reuse())
    designs["baseline_shared_4bit"] = parametrized_nbit_adder.build_nbit_design(
        4, "baseline", "shared")
    return designs


def nbit_designs(width: int = 4, styles=("baseline", "optimized")) -> dict:
    designs: dict = {}
    for style in styles:
        designs[f"{style}_shared_control"] = shared_addsub_control.build_shared_control_addsub(
            width, style)
        for label, mode in (("adder", "add"), ("subtractor", "subtract")):
            designs[f"{style}_{label}"] = parametrized_nbit_adder.build_nbit_design(
                width, style, mode, name=f"{style}_{label}_{width}bit")
    return designs


def expected_arithmetic(a: int, b: int, mode: int, width: int = 4) -> tuple[int, int]:
    return baseline_4bit_adder.expected(a, b, mode, width)


def check_case(spec: cu.CircuitSpec, values: dict, measured: dict) -> dict:
    """Did this measured case preserve inputs and restore its ancillas?"""
    preserved: dict[str, bool] = {}
    for name in spec.inputs:
        if name in measured:
            preserved[name] = int(measured[name]) == int(values.get(name, 0))
    restored: dict[str, bool] = {}
    output_lines = set(spec.flat(*spec.outputs))
    for name in spec.ancillas:
        lines = [q for q in spec.registers[name] if q not in output_lines]
        if not lines or name in spec.inputs:
            continue
        # an untouched ancilla keeps the value it was initialised with
        restored[name] = int(measured[name]) == _initial_ancilla_value(spec, name, values)
    return {
        "inputs_preserved": all(preserved.values()) if preserved else True,
        "preserved_detail": preserved,
        "ancilla_restored": all(restored.values()) if restored else True,
        "restored_detail": restored,
    }


def _initial_ancilla_value(spec: cu.CircuitSpec, name: str, values: dict) -> int:
    """Ancilla lines start at |0>; a mode/operand register starts at its input."""
    if name in values:
        return int(values[name])
    return 0


def run_both(spec: cu.CircuitSpec, cases_values: list[dict], confirm_aer: bool = True,
             chunk: int = 128, method: str | None = None) -> tuple[list, list, bool]:
    """Return (op-list results, Aer results, agreement flag)."""
    fast = cu.op_list_results(spec, cases_values)
    if not confirm_aer:
        return fast, fast, True
    aer = cu.run_cases(spec, [cu.case_dictionary(spec, v) for v in cases_values],
                       chunk=chunk, method=method)
    agree = all(a == b for a, b in zip(fast, aer))
    return fast, aer, agree

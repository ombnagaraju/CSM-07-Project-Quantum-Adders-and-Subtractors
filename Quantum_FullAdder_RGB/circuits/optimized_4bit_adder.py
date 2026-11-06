"""Optimized 4-bit reversible adder-subtractor (Peres ripple, zero garbage).

Each stage is two Peres blocks plus one CNOT:

    P(A_i, B_i, C_{i+1})   writes the generate term A_i.B_i into the next carry
                           line and turns B_i into the propagate term
    P(A_i XOR B_i, C_i, C_{i+1})
                           turns the carry-in line into Sum_i and completes
                           C_{i+1} = A_i.B_i XOR (A_i XOR B_i).C_i
    CX(A_i, B_i)           restores the conditioned B_i

Because a carry line becomes its own sum bit, the design needs no separate
result register: that is where the n-qubit saving over the baseline comes from,
and it is measured rather than asserted. Arithmetic behaviour and the
carry/borrow convention are identical to the baseline units.
"""

from __future__ import annotations

from circuits import circuit_utils as cu
from circuits.baseline_4bit_adder import all_cases, expected
from circuits.parametrized_nbit_adder import build_nbit_design

WIDTH = 4


def build_optimized_4bit_adder() -> cu.CircuitSpec:
    return build_nbit_design(WIDTH, "optimized", "add", name="optimized_4bit_adder")


def build_optimized_4bit_subtractor() -> cu.CircuitSpec:
    return build_nbit_design(WIDTH, "optimized", "subtract", name="optimized_4bit_subtractor")


__all__ = ["build_optimized_4bit_adder", "build_optimized_4bit_subtractor",
           "expected", "all_cases", "WIDTH"]

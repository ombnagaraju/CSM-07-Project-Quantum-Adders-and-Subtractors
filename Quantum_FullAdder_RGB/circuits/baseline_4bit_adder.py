"""Baseline 4-bit reversible adder and subtractor (Toffoli-CNOT ripple).

Two standalone units are provided, because the headline comparison of
contribution 1 needs a "separate circuits for add and subtract" reference.
Each unit keeps the operand registers intact: the propagate XOR is folded into
the B line inside a stage and undone before the stage finishes.

Addition      R = (A + B) mod 16, Cout = carry out.
Subtraction   R = (A - B) mod 16, implemented as A + NOT B + 1; the line
              Cout = 1 means A >= B, therefore borrow = NOT Cout.
"""

from __future__ import annotations

from circuits import circuit_utils as cu
from circuits.parametrized_nbit_adder import build_nbit_design, build_adder_pair

WIDTH = 4


def build_baseline_4bit_adder() -> cu.CircuitSpec:
    return build_nbit_design(WIDTH, "baseline", "add", name="baseline_4bit_adder")


def build_baseline_4bit_subtractor() -> cu.CircuitSpec:
    return build_nbit_design(WIDTH, "baseline", "subtract", name="baseline_4bit_subtractor")


def build_baseline_4bit_units() -> dict:
    """Both standalone units, as a machine that must contain both."""
    return build_adder_pair(WIDTH, "baseline")


def expected(a: int, b: int, mode: int = 0, width: int = WIDTH) -> tuple[int, int]:
    """Return (result, carry_out) with the documented borrow convention."""
    mask = (1 << width) - 1
    if mode == 0:
        total = a + b
        return total & mask, total >> width
    total = a + ((~b) & mask) + 1          # two's complement, carry-in = 1
    return total & mask, total >> width


def all_cases(width: int = WIDTH) -> list:
    """The 512 exhaustive (A, B, mode) combinations for this width."""
    limit = 1 << width
    return [(a, b, mode) for a in range(limit) for b in range(limit) for mode in (0, 1)]

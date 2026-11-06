"""
Unit Tests for Reversible 4-Bit Adder-Subtractor Architectures
=============================================================

Tests arithmetic correctness, carry propagation, subtraction borrow,
input preservation, and ancilla cleanup for:
  - Baseline 4-Bit Adder-Subtractor
  - Optimized 4-Bit Adder-Subtractor
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from circuits.baseline_4bit_adder import simulate_baseline_4bit
from circuits.optimized_4bit_adder import simulate_optimized_4bit

# Representative arithmetic test cases covering extremes and boundaries
TEST_CASES_4BIT = [
    # (M, A, B)
    (0, 0, 0),    # 0 + 0 = 0, Cout=0
    (0, 15, 0),   # 15 + 0 = 15, Cout=0
    (0, 0, 15),   # 0 + 15 = 15, Cout=0
    (0, 8, 8),    # 8 + 8 = 0, Cout=1 (overflow)
    (0, 15, 1),   # 15 + 1 = 0, Cout=1
    (0, 15, 15),  # 15 + 15 = 14, Cout=1
    (0, 9, 7),    # 9 + 7 = 0, Cout=1
    (0, 3, 5),    # 3 + 5 = 8, Cout=0
    (1, 0, 0),    # 0 - 0 = 0, Borrow=0
    (1, 15, 0),   # 15 - 0 = 15, Borrow=0
    (1, 15, 15),  # 15 - 15 = 0, Borrow=0
    (1, 10, 4),   # 10 - 4 = 6, Borrow=0
    (1, 4, 10),   # 4 - 10 = -6 mod 16 = 10, Borrow=1
    (1, 0, 1),    # 0 - 1 = -1 mod 16 = 15, Borrow=1
    (1, 0, 15),   # 0 - 15 = -15 mod 16 = 1, Borrow=1
    (1, 7, 8),    # 7 - 8 = -1 mod 16 = 15, Borrow=1
]


@pytest.mark.parametrize("m, a, b", TEST_CASES_4BIT)
def test_baseline_4bit_arithmetic(m, a, b):
    res = simulate_baseline_4bit(m, a, b)
    assert res["is_correct"] is True
    assert res["inputs_preserved"] is True
    assert res["ancillas_restored"] is True
    assert res["preserved_m"] == m
    assert res["preserved_a"] == a
    assert res["preserved_b"] == b

    if m == 0:
        assert res["output_r"] == (a + b) % 16
        assert res["output_cout"] == (a + b) // 16
    else:
        assert res["output_r"] == (a - b) % 16
        exp_borrow = 1 if a < b else 0
        assert res["borrow"] == exp_borrow


@pytest.mark.parametrize("m, a, b", TEST_CASES_4BIT)
def test_optimized_4bit_arithmetic(m, a, b):
    res = simulate_optimized_4bit(m, a, b)
    assert res["is_correct"] is True
    assert res["inputs_preserved"] is True
    assert res["ancillas_restored"] is True
    assert res["preserved_m"] == m
    assert res["preserved_a"] == a
    assert res["preserved_b"] == b

    if m == 0:
        assert res["output_r"] == (a + b) % 16
        assert res["output_cout"] == (a + b) // 16
    else:
        assert res["output_r"] == (a - b) % 16
        exp_borrow = 1 if a < b else 0
        assert res["borrow"] == exp_borrow

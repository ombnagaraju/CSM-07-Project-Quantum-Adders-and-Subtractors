"""
Unit Tests for Reversible Full Adder Architectures
==================================================

Tests all 8 truth table cases (A, B, Cin in {0, 1}):
  - Baseline Toffoli-CNOT Full Adder
  - Peres Gate-Based Full Adder
  - Optimized Full Adder
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from circuits.baseline_fulladder import simulate_baseline_fulladder
from circuits.peres_fulladder import simulate_peres_fulladder
from circuits.optimized_fulladder import simulate_optimized_fulladder


@pytest.mark.parametrize("a", [0, 1])
@pytest.mark.parametrize("b", [0, 1])
@pytest.mark.parametrize("cin", [0, 1])
def test_baseline_fulladder_truth_table(a, b, cin):
    res = simulate_baseline_fulladder(a, b, cin)
    exp_sum = (a + b + cin) % 2
    exp_cout = (a + b + cin) // 2

    assert res["output_sum"] == exp_sum, f"Baseline Sum failed for ({a},{b},{cin})"
    assert res["output_cout"] == exp_cout, f"Baseline Cout failed for ({a},{b},{cin})"
    assert res["inputs_preserved"] is True, f"Baseline input preservation failed for ({a},{b},{cin})"
    assert res["preserved_a"] == a
    assert res["preserved_b"] == b
    assert res["preserved_cin"] == cin


@pytest.mark.parametrize("a", [0, 1])
@pytest.mark.parametrize("b", [0, 1])
@pytest.mark.parametrize("cin", [0, 1])
def test_peres_fulladder_truth_table(a, b, cin):
    res = simulate_peres_fulladder(a, b, cin)
    exp_sum = (a + b + cin) % 2
    exp_cout = (a + b + cin) // 2

    assert res["output_sum"] == exp_sum, f"Peres Sum failed for ({a},{b},{cin})"
    assert res["output_cout"] == exp_cout, f"Peres Cout failed for ({a},{b},{cin})"
    assert res["preserved_a"] == a, "Peres input A must be preserved"
    assert res["garbage_q1"] == a ^ b, "Peres qubit 1 must produce propagate term A^B"


@pytest.mark.parametrize("a", [0, 1])
@pytest.mark.parametrize("b", [0, 1])
@pytest.mark.parametrize("cin", [0, 1])
def test_optimized_fulladder_truth_table(a, b, cin):
    res = simulate_optimized_fulladder(a, b, cin, restore_b=True)
    exp_sum = (a + b + cin) % 2
    exp_cout = (a + b + cin) // 2

    assert res["output_sum"] == exp_sum, f"Optimized Sum failed for ({a},{b},{cin})"
    assert res["output_cout"] == exp_cout, f"Optimized Cout failed for ({a},{b},{cin})"
    assert res["inputs_preserved"] is True, f"Optimized A and B preservation failed for ({a},{b},{cin})"
    assert res["preserved_a"] == a
    assert res["preserved_b"] == b

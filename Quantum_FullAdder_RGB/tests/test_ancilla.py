"""
Unit Tests for Ancilla Restoration & Cleanliness
================================================

Verifies that intermediate ancilla qubits used for carry propagation
are cleanly returned to |0> across addition and subtraction operations.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from circuits.baseline_4bit_adder import simulate_baseline_4bit
from circuits.optimized_4bit_adder import simulate_optimized_4bit


@pytest.mark.parametrize("m", [0, 1])
@pytest.mark.parametrize("a", [0, 5, 10, 15])
@pytest.mark.parametrize("b", [0, 3, 7, 12, 15])
def test_ancilla_cleanup_baseline_4bit(m, a, b):
    res = simulate_baseline_4bit(m, a, b)
    assert res["ancillas_restored"] is True
    assert all(c == 0 for c in res["ancilla_carries"])


@pytest.mark.parametrize("m", [0, 1])
@pytest.mark.parametrize("a", [0, 5, 10, 15])
@pytest.mark.parametrize("b", [0, 3, 7, 12, 15])
def test_ancilla_cleanup_optimized_4bit(m, a, b):
    res = simulate_optimized_4bit(m, a, b)
    assert res["ancillas_restored"] is True
    assert all(c == 0 for c in res["ancilla_carries"])

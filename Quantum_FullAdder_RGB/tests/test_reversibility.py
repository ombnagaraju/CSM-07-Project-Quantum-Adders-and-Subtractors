"""
Unit Tests for Circuit Reversibility (U * U_dag = I)
====================================================

Verifies that quantum adder circuits invert exactly to the identity
transformation on computational basis states.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit
from verification.verify_reversibility import test_circuit_reversibility as check_reversibility


def test_baseline_fulladder_reversibility():
    qc = build_baseline_fulladder()
    for val in range(8):  # 2^3 input combinations with 2 zero ancillas
        bitstr = format(val, "03b")[::-1] + "00"
        assert check_reversibility(qc, bitstr) is True


def test_peres_fulladder_reversibility():
    qc = build_peres_fulladder()
    for val in range(8):
        bitstr = format(val, "03b")[::-1] + "0"
        assert check_reversibility(qc, bitstr) is True


def test_optimized_fulladder_reversibility():
    qc = build_optimized_fulladder(restore_b=True)
    for val in range(8):
        bitstr = format(val, "03b")[::-1] + "0"
        assert check_reversibility(qc, bitstr) is True


def test_4bit_subtractor_reversibility():
    qc = build_optimized_4bit_adder_circuit()
    # Test key basis states across the 18-qubit register
    test_states = [
        "0" * 18,
        "1" * 18,
        "10" * 9,
        "01" * 9,
        "0" + "1111" + "0000" + "0" * 9,
        "1" + "1010" + "0101" + "0" * 9,
    ]
    for bitstr in test_states:
        assert check_reversibility(qc, bitstr) is True

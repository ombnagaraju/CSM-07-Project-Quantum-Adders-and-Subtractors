"""Phase 2 tests: 1-bit reversible full adders.

Every design has to reproduce the full-adder truth table on all eight input
combinations, keep the operands it promises to keep, and be confirmed by the
Qiskit Aer simulator on the same cases. The optimized design additionally has to
beat the baseline on both total gate count and quantum cost, which is the
acceptance criterion of the project: a circuit is only called optimized when the
measured resources say so.
"""

import pytest

from circuits import circuit_utils as cu
from verification import one_bit_designs, run_both

CASES = [{"A": a, "B": b, "Cin": c}
         for a in (0, 1) for b in (0, 1) for c in (0, 1)]

LABELS = sorted(one_bit_designs())


def expected(a: int, b: int, cin: int) -> tuple[int, int]:
    total = a + b + cin
    return total & 1, total >> 1


@pytest.mark.parametrize("label", LABELS)
def test_op_list_reproduces_the_truth_table(label):
    spec = one_bit_designs()[label]
    for case in CASES:
        measured = cu.op_list_results(spec, [case])[0]
        want_sum, want_carry = expected(case["A"], case["B"], case["Cin"])
        assert int(measured["Sum"]) == want_sum, (label, case)
        assert int(measured["Cout"]) == want_carry, (label, case)


@pytest.mark.parametrize("label", LABELS)
def test_aer_confirms_the_same_eight_cases(label):
    spec = one_bit_designs()[label]
    fast, aer, agree = run_both(spec, CASES, confirm_aer=True)
    assert agree, f"{label}: op list and Aer simulator disagree"
    assert fast == aer


@pytest.mark.parametrize("label", LABELS)
def test_declared_garbage_matches_the_measured_dirty_lines(label):
    """Run on the eight operand settings (ancillas at |0>) and list every line
    that is not an output but ends up different from what it started as."""
    spec = one_bit_designs()[label]
    finals = cu.op_list_lines(spec, CASES)
    output_lines = set(spec.flat(*spec.outputs))
    dirty = set()
    for index, case in enumerate(CASES):
        prepared = {q: 0 for q in range(spec.n_qubits)}
        prepared.update(cu.case_dictionary(spec, case))
        for q in range(spec.n_qubits):
            if q in output_lines or int(finals[index, q]) == prepared[q]:
                continue
            dirty.add(q)
    declared = set(spec.flat(*spec.garbage)) - output_lines
    assert dirty == declared, (label, sorted(dirty), sorted(declared))


@pytest.mark.parametrize("label", LABELS)
def test_operands_survive_as_the_module_declares(label):
    """A design must return every input line it neither reuses as an output nor
    declares as garbage."""
    spec = one_bit_designs()[label]
    busy = set(spec.flat(*spec.garbage)) | set(spec.flat(*spec.outputs))
    for case in CASES:
        measured = cu.op_list_results(spec, [case])[0]
        for name in spec.inputs:
            if set(spec.registers[name]) & busy:
                continue
            assert int(measured[name]) == case[name], (label, name, case)


def test_optimized_beats_baseline_on_gates_and_quantum_cost():
    designs = one_bit_designs()
    baseline = cu.spec_metrics(designs["baseline_fulladder"])
    optimized = cu.spec_metrics(designs["optimized_fulladder"])
    assert optimized["total_gates"] < baseline["total_gates"]
    assert optimized["quantum_cost"] < baseline["quantum_cost"]
    assert optimized["garbage_qubits"] == 0
    assert optimized["quantum_cost"] == 13 and optimized["total_gates"] == 5


def test_peres_gate_definition_is_ccx_then_cx():
    from qiskit.circuit import QuantumCircuit
    from qiskit.quantum_info import Operator

    from circuits.circuit_utils import PeresGate

    reference = QuantumCircuit(3)
    reference.ccx(0, 1, 2)
    reference.cx(0, 1)
    assert Operator(PeresGate()).equiv(Operator(reference))

    inverse = QuantumCircuit(3)
    inverse.cx(0, 1)
    inverse.ccx(0, 1, 2)
    assert Operator(PeresGate(inverse=True)).equiv(Operator(inverse))


def test_truth_table_helpers_agree_with_the_circuits():
    from circuits import baseline_fulladder

    table = baseline_fulladder.truth_table()
    assert len(table) == 8
    for a, b, cin, sum_bit, carry in table:
        assert (sum_bit, carry) == expected(a, b, cin)

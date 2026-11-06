"""Phase 2 tests: the shared circuit utilities.

Everything the project reports is derived here: the logical gate cost, the
depth, the abstract op list that the exact simulator and the Qiskit circuit
builder both consume, and the classical-controlled gate expansion that the
one-hot multiplexers rely on. If one of these helpers drifts, every number in
every CSV becomes wrong, so each is checked against an independent argument.
"""

import numpy as np
import pytest

import config
from circuits import baseline_fulladder, circuit_utils as cu, peres_fulladder

CASES = [{"A": a, "B": b, "Cin": c}
         for a in (0, 1) for b in (0, 1) for c in (0, 1)]


def test_endianness_is_the_documented_lsb_first_convention():
    assert config.LSB_QUBIT_INDEX == 0
    qubits = [4, 5, 6, 7]
    bits = cu.value_to_bits(0b0011, qubits)
    assert bits == {4: 1, 5: 1, 6: 0, 7: 0}
    assert cu.bits_to_value([bits[q] for q in qubits], qubits) == 0b0011
    for value in range(16):
        prepared = cu.value_to_bits(value, qubits)
        assert cu.bits_to_value([prepared[q] for q in qubits], qubits) == value


def test_case_dictionary_prepares_only_the_named_registers():
    """Lines a case does not name stay |0>, which is what an ancilla needs."""
    spec = baseline_fulladder.build_baseline_fulladder()
    bits = cu.case_dictionary(spec, {"A": 1, "B": 1, "Cin": 1})
    assert bits == {spec.registers["A"][0]: 1, spec.registers["B"][0]: 1,
                    spec.registers["Cin"][0]: 1}
    assert set(bits) <= set(range(spec.n_qubits))
    assert all(bit in (0, 1) for bit in bits.values())


def test_logical_cost_matches_the_ncv_library():
    baseline = cu.spec_metrics(baseline_fulladder.build_baseline_fulladder())
    assert (baseline["total_gates"], baseline["quantum_cost"]) == (6, 14)
    assert (baseline["ccx_gates"], baseline["cx_gates"]) == (2, 4)
    peres = cu.spec_metrics(peres_fulladder.build_peres_fulladder())
    assert (peres["total_gates"], peres["quantum_cost"]) == (3, 9)
    assert peres["peres_gates"] == 2 and peres["ccx_gates"] == 0
    assert config.gate_quantum_cost("ccx") == 5
    assert config.gate_quantum_cost("peres") == 4
    assert config.gate_quantum_cost("cx") == 1


@pytest.mark.parametrize("builder", (baseline_fulladder.build_baseline_fulladder,
                                    peres_fulladder.build_peres_fulladder))
def test_depth_is_the_independent_longest_path(builder):
    """Recompute the greedy per-qubit schedule in the test and compare."""
    spec = builder()
    finish: dict[int, int] = {}
    for op in spec.all_ops():
        start = max((finish.get(qubit, 0) for qubit in op[1:]), default=0)
        for qubit in op[1:]:
            finish[qubit] = start + 1
    assert cu.logical_depth(spec) == max(finish.values())
    assert cu.logical_depth(spec) <= cu.spec_metrics(spec)["total_gates"]


def test_controlled_ops_ladder_up_the_gate_library():
    plain = [cu.x(0), cu.cx(0, 1), cu.ccx(0, 1, 2)]
    gated, used = cu.controlled_ops(plain, 7, [8, 9])
    kinds = [op[0] for op in gated]
    assert kinds.count("cx") == 1
    assert kinds.count("ccx") == 4
    assert all(op[0] != "x" for op in gated)
    assert set(used) <= {8, 9}
    assert 7 not in used


def test_controlled_block_is_the_identity_when_the_select_is_zero():
    """A gated block must act as the identity for select 0 and reproduce the
    original block for select 1. The helper ancillas the Toffoli expansion
    needs must start at |0>, which is what the designs that use it guarantee."""
    ops = [cu.x(2), cu.cx(2, 3), cu.ccx(2, 3, 4)]
    gated, used = cu.controlled_ops(ops, 0, [5, 6, 7])
    assert used and all(q not in (0, 2, 3, 4) for q in used)
    active, helper = [2, 3, 4], sorted(used)
    values = np.arange(1 << len(active), dtype=np.int64)
    start = np.zeros((len(values), 8), dtype=np.uint8)
    for k, qubit in enumerate(active):
        start[:, qubit] = (values >> k) & 1
    columns = [0] + active + helper
    for select in (0, 1):
        prepared = start.copy()
        prepared[:, 0] = select
        out = cu.apply_ops_to_bits(gated, prepared.copy())
        assert (out[:, helper] == 0).all(), "the helper lines must be left clean"
        if select == 0:
            assert (out[:, columns] == prepared[:, columns]).all()
        else:
            wanted = cu.apply_ops_to_bits(ops, prepared.copy())
            assert (out[:, columns] == wanted[:, columns]).all()


def test_statevector_readout_agrees_with_the_sampled_path():
    spec = peres_fulladder.build_peres_fulladder()
    cases = [cu.case_dictionary(spec, values) for values in CASES]
    exact = cu.run_cases_statevector(spec, cases)
    aer = cu.run_cases(spec, cases)
    assert exact == aer == cu.op_list_results(spec, CASES)


def test_qasm_export_and_metric_table_render():
    import os

    config.ensure_directories()
    spec = baseline_fulladder.build_baseline_fulladder()
    text = cu.to_qasm(spec)
    counts = cu.logical_counts(spec)
    assert text.startswith("OPENQASM 3") and 'include "stdgates.inc";' in text
    assert f"qubit[{spec.n_qubits}] q;" in text and f"bit[{spec.n_qubits}] ro;" in text
    def emitted(name: str) -> int:
        return sum(1 for line in text.splitlines() if line.startswith(f"{name} q"))

    assert emitted("ccx") == counts["ccx"] and emitted("cx") == counts["cx"]
    assert "measure" not in text, "the exported circuit is the unitary body only"
    peres_text = cu.to_qasm(peres_fulladder.build_peres_fulladder())
    assert "gate peres" in peres_text, "the custom Peres gate must carry its definition"
    assert peres_text.count("\nperes q") == 2
    path = cu.save_qasm(spec, "test_baseline_fulladder.qasm")
    assert path.endswith("test_baseline_fulladder.qasm")
    try:
        assert open(path, encoding="utf-8").read() == text
    finally:
        os.remove(path)
    rows = [cu.spec_metrics(spec),
            cu.spec_metrics(peres_fulladder.build_peres_fulladder())]
    table = cu.format_metrics_table(rows, ("circuit", "qubits", "quantum_cost"))
    lines = table.splitlines()
    assert lines[0].split()[0] == "circuit" and len(lines) == 4
    assert "baseline_fulladder" in table and "peres_fulladder" in table


def test_circuit_builder_uses_one_classical_register_per_qubit():
    spec = baseline_fulladder.build_baseline_fulladder()
    qc = spec.build(measure=True)
    assert len(qc.cregs) == 1 and qc.cregs[0].name == "ro"
    assert qc.cregs[0].size == spec.n_qubits
    assert sum(1 for inst in qc if inst.operation.name == "measure") == spec.n_qubits

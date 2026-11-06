"""Phase 2 tests: reversibility of every published design.

Three independent arguments are required by the module under test: the op list
must be one-to-one, the design composed with its exact inverse must restore
every state, and the Qiskit operator must be a permutation matrix. These tests
run the real verifier and then check the same properties directly on small
designs, so a regression in the shared helper cannot hide behind the verifier.
"""

import numpy as np
import pytest

from circuits import circuit_utils as cu
from circuits import peres_fulladder, uncomputation
from verification import garbage_designs, one_bit_designs
from verification import verify_reversibility as vr


@pytest.fixture(scope="module")
def verification_rows():
    return vr.verify(write=False)


def test_the_verifier_reports_no_failure(verification_rows):
    failed = [row for row in verification_rows if row["result"] == "fail"]
    assert not failed, failed


def test_every_design_is_proved_bijective_and_reversible(verification_rows):
    """Only the unitary check may be skipped, and only for a documented reason."""
    by_design: dict[str, set] = {}
    for row in verification_rows:
        by_design.setdefault(row["circuit"], set()).add(row["result"])
        if row["check"] in ("bijection", "inverse_roundtrip"):
            assert row["result"] == "pass", row
        elif row["result"] == "skipped":
            assert "budget" in row["detail"] or "measurement" in row["detail"], row
    for check in ("bijection", "inverse_roundtrip", "unitary_permutation"):
        assert sum(1 for r in verification_rows if r["check"] == check and r["result"] == "pass")


def test_states_are_reported_for_every_row_that_ran(verification_rows):
    ran = [row for row in verification_rows if row["result"] == "pass"]
    assert ran and all(row["states_tested"] > 0 for row in ran)


@pytest.mark.parametrize("label", sorted(one_bit_designs()))
def test_inverse_roundtrip_restores_the_whole_space(label):
    spec = one_bit_designs()[label]
    all_restored, restored, tested = cu.roundtrip_is_identity(spec)
    assert all_restored and restored == tested == 1 << spec.n_qubits


@pytest.mark.parametrize("label", sorted(one_bit_designs()))
def test_the_truth_permutation_is_one_to_one(label):
    spec = one_bit_designs()[label]
    active = sorted(set(spec.flat(*spec.inputs)) | set(spec.flat(*spec.outputs)))
    one_to_one, distinct = cu.is_bijective(spec, active)
    assert one_to_one and distinct == 1 << len(active)


def test_permutation_map_pairs_inputs_with_outputs():
    spec = peres_fulladder.build_peres_fulladder()
    lines = spec.registers["A"] + spec.registers["B"] + spec.registers["Cin"]
    inputs, outputs = cu.permutation_map(spec, lines)
    assert list(inputs) == list(range(8))
    assert sorted(outputs) == list(range(8))


def test_sampling_is_used_above_the_exhaustive_budget():
    """The wide design is not silently dropped: it is sampled, and says so."""
    wide = vr.all_designs(width=8)["baseline_shared_control"]
    assert (1 << wide.n_qubits) > vr.MAX_EXHAUSTIVE_STATES
    values = np.random.default_rng(0).choice(1 << wide.n_qubits, size=64, replace=False)
    one_to_one, _ = cu.is_bijective(wide, list(range(wide.n_qubits)), values)
    assert one_to_one


def test_measurement_designs_have_no_unitary_inverse():
    spec = garbage_designs()["baseline_shared_4bit"]
    measured = uncomputation.measurement_based_uncompute(spec, "reset")
    with pytest.raises(ValueError, match="no unitary inverse"):
        cu.inverse_ops(measured.all_ops())
    ok, detail = vr.unitary_is_permutation(measured)
    assert ok is None and "measurement" in detail


def test_coherent_small_designs_are_permutation_matrices():
    for label in sorted(one_bit_designs()):
        spec = one_bit_designs()[label]
        if any(op[0] in ("measure", "cond_x", "reset") for op in spec.all_ops()):
            continue
        ok, detail = vr.unitary_is_permutation(spec)
        assert ok is True, (label, detail)

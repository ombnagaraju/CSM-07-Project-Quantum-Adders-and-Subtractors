"""Phase 2 tests: garbage reduction by structure and by measurement.

Two routes to the same resource goal, measured against each other:

* structural uncomputation re-applies the recomputation, so it costs reversible
  gates but keeps the circuit coherent;
* measurement-based uncomputation costs no reversible gates, but it collapses
  the garbage line.

The tests assert the gate/cost numbers of both routes, that the answers never
change, and - the honest price - that the measured variants stop being undoable
under a superposition of inputs while the coherent ones stay perfectly undoable.
"""

import pytest

from circuits import circuit_utils as cu
from circuits import optimized_fulladder, peres_fulladder, uncomputation
from verification import garbage_designs, one_bit_designs
from verification import verify_garbage as vg


@pytest.fixture(scope="module")
def rows():
    return vg.verify(write=False, confirm_coherence=True)


def by(rows, design, method):
    return next(r for r in rows if r["design"] == design and r["method"] == method)


def test_the_declared_garbage_is_the_measured_dirty_set():
    for label, spec in garbage_designs().items():
        output_lines = set(spec.flat(*spec.outputs))
        declared = set(spec.flat(*spec.garbage)) - output_lines
        assert set(vg.garbage_lines(spec)) == declared, label


def test_measurement_based_uncompute_removes_every_garbage_line(rows):
    measured = [row for row in rows if row["method"] != "none"]
    assert measured
    for row in measured:
        assert row["garbage_qubits"] == 0 and row["garbage_removed"], row


def test_measurement_based_uncompute_costs_no_reversible_gates(rows):
    """Clearing a line by measurement adds no X/CNOT/Toffoli/Peres gate at all;
    the price is in the measurement columns and in coherence, not in gates."""
    for row in rows:
        if row["method"] == "none":
            continue
        cleared = len(row["garbage_lines_before"])
        assert row["total_gates_delta"] == 0, row
        assert row["quantum_cost_delta"] == 0, row
        if row["method"] == "measurement_based_conditional":
            assert row["measure_ops"] == row["cond_x_ops"] == cleared, row
            assert row["reset_ops"] == 0, row
        else:
            assert row["reset_ops"] == cleared, row
            assert row["measure_ops"] == row["cond_x_ops"] == 0, row


def test_structural_uncomputation_costs_gates_and_no_coherence(rows):
    """The Peres garbage lines are restored by CX + CCX: real cost, real gain."""
    base = by(rows, "peres_fulladder", "none")
    clean = by(rows, "peres_structural_uncompute", "none")
    assert base["garbage_qubits"] == 2 and clean["garbage_qubits"] == 0
    assert clean["total_gates"] == base["total_gates"] + 2
    assert clean["quantum_cost"] == base["quantum_cost"] + 6
    assert clean["undoable"] and base["undoable"]
    assert clean["measure_ops"] == clean["reset_ops"] == 0


def test_the_answers_never_change(rows):
    for row in rows:
        if row["method"] == "none":
            continue
        assert row["answer_mismatches_vs_before"] == 0, row
        assert row["answer_pass"] and row["pass"], row


def test_the_price_of_measuring_is_paid_in_coherence_not_in_statistics(rows):
    """Answer statistics are untouched (a local channel on a line that is traced
    out cannot change them); what is lost is the ability to undo."""
    for label, row in [(r["design"], r) for r in rows if r["method"] != "none"]:
        if row["roundtrip_probability"] == "":
            continue
        coherent = by(rows, label, "none")
        assert row["answer_statistics_difference"] == pytest.approx(0.0, abs=1e-12), row
        assert coherent["roundtrip_probability"] == pytest.approx(1.0), coherent
        assert row["roundtrip_probability"] < 1.0, (label, row)
        assert not row["undoable"], row


def test_the_wide_design_reports_why_its_coherence_columns_are_blank(rows):
    wide = [r for r in rows if r["probe_note"] and "probe limit" in r["probe_note"]]
    assert wide, "the 4-bit shared design exceeds the density-matrix probe budget"
    for row in wide:
        assert row["purity"] == "" and row["roundtrip_probability"] == ""


def test_clearing_is_the_only_difference_from_the_original_design():
    spec = peres_fulladder.build_peres_fulladder()
    dirty = vg.garbage_lines(spec)
    for method, kinds in (("conditional", ["measure", "cond_x"]), ("reset", ["reset"])):
        variant = uncomputation.measurement_based_uncompute(spec, method)
        assert variant.ops[:len(spec.ops)] == spec.ops
        assert [op[0] for op in vg.clearing_ops(variant, spec)] == kinds * len(dirty)
        assert variant.garbage == ()
        assert variant.registers["Uncomputed"] == dirty


def test_bad_requests_are_rejected():
    spec = optimized_fulladder.build_optimized_fulladder()
    with pytest.raises(ValueError, match="no garbage lines"):
        uncomputation.measurement_based_uncompute(spec, "reset")
    with pytest.raises(ValueError, match="method must be"):
        uncomputation.measurement_based_uncompute(
            peres_fulladder.build_peres_fulladder(), "unitary")


def test_the_op_list_clears_a_measured_line_exactly_like_reset():
    """The fast simulator must agree with the documented feed-forward semantics."""
    spec = one_bit_designs()["peres_fulladder"]
    cases = vg.cases_for(spec)
    dirty = vg.garbage_lines(spec)
    variant = uncomputation.measurement_based_uncompute(spec, "reset")
    lines = cu.op_list_lines(variant, cases)
    for q in dirty:
        assert set(lines[:, q]) == {0}
    reference = cu.op_list_lines(spec, cases)
    untouched = [q for q in range(spec.n_qubits) if q not in dirty]
    assert (lines[:, untouched] == reference[:, untouched]).all()

"""Phase 2 tests: ancilla bookkeeping.

An ancilla is only acceptable when the design says what happens to it: a helper
line that is not declared as garbage must return to the value it was prepared
with on *every* case, and a line that is declared as garbage must be measured as
actually carrying input information. Both statements are checked here on the
rows the verifier produces, plus directly against the register declarations.
"""

import pytest

from circuits import circuit_utils as cu
from circuits import parametrized_nbit_adder as pna
from verification import one_bit_designs
from verification import verify_ancilla as va


@pytest.fixture(scope="module")
def rows():
    return va.verify(width=3, confirm_aer=True, write=False)


@pytest.fixture(scope="module")
def one_bit_rows():
    return va.verify(width=1, confirm_aer=False, write=False)


def find(rows, circuit, register):
    return next(r for r in rows if r["circuit"] == circuit and r["register"] == register)


def test_every_ancilla_row_passes(rows):
    failed = [r for r in rows if not r["pass"]]
    assert not failed, failed


def test_helper_lines_that_are_not_garbage_are_always_restored(rows):
    dirty = [r for r in rows if r["require_cleanup"] and r["restored_percent"] != 100.0]
    assert not dirty, dirty


def test_declared_garbage_is_reported_as_such(rows):
    """A garbage line is published as not requiring cleanup, never silently."""
    garbage = [r for r in rows if r["declared_garbage"]]
    assert garbage and all(not r["require_cleanup"] for r in garbage)
    assert any(r["carries_input_information"] for r in garbage), \
        "no declared garbage line ever differs from its initial value"


def test_aer_confirms_the_op_list_ancilla_bits(rows):
    checked = [r for r in rows if r["aer_cases"]]
    assert checked, "the Aer confirmation path never ran"
    assert all(r["aer_matches_op_list"] for r in checked)
    for row in checked:
        assert row["aer_cases_restored"] <= row["aer_cases"]


def test_the_line_list_is_exactly_the_non_output_helper_lines():
    spec = pna.build_nbit_design(3, "baseline", "shared")
    lines = va.ancilla_lines(spec)
    assert [name for name, _, _ in lines] == ["Carry_internal"] * 3
    assert {q for _, q, _ in lines} == set(spec.registers["Carry_internal"])
    # the mode line is an input, and the carry-out is an output: neither is a
    # cleanup target even though both are listed as ancillas
    assert not {q for _, q, _ in lines} & set(spec.registers["M"])
    assert not {q for _, q, _ in lines} & set(spec.registers["Cout"])


def test_a_design_without_helper_lines_says_so_in_a_row(one_bit_rows):
    """The optimized adder reuses its carry chain as the sum, so nothing needs
    cleaning up - and the CSV must state that instead of being empty."""
    spec = one_bit_designs()["optimized_fulladder"]
    assert va.ancilla_lines(spec) == []
    assert cu.spec_metrics(spec)["garbage_qubits"] == 0
    row = find(one_bit_rows, "optimized_fulladder", "(none)")
    assert row["pass"] and row["cases"] == 8


def test_structural_uncomputation_cleans_the_peres_ancilla(one_bit_rows):
    peres = find(one_bit_rows, "peres_fulladder", "AB")
    cleaned = find(one_bit_rows, "peres_structural_uncompute", "AB")
    assert peres["declared_garbage"] and peres["restored_percent"] < 100.0
    assert not cleaned["declared_garbage"] and cleaned["restored_percent"] == 100.0

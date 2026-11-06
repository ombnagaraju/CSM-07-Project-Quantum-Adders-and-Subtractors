"""Phase 2 tests: one shared control qubit instead of two separate units.

Contribution 1 claims that a single mode qubit turns one reversible ripple into
both an adder and a subtractor. The claim has two halves and both are measured
here: the shared unit must reproduce the separate adder and subtractor on every
input (equivalence), and it must cost less than a machine that contains both
units at once (savings). Where the shared design is *not* better - the
per-operation depth - the test asserts the honest negative number rather than
hiding the column.
"""

import pytest

from circuits import circuit_utils as cu
from circuits import parametrized_nbit_adder as pna
from circuits import shared_addsub_control as sac
from verification import verify_control_savings as vs

WIDTH = 4
CHEAP = ("qubits", "ancilla_qubits", "total_gates", "quantum_cost")


@pytest.fixture(scope="module")
def table():
    return {(row["style"], row["approach"]): row for row in sac.savings_table(WIDTH)}


@pytest.fixture(scope="module")
def rows():
    return vs.verify(WIDTH, confirm_aer=True, write=False)


def test_the_shared_unit_reproduces_both_standalone_units():
    """All 512 (A, B, mode) cases against the pair, through the exact simulator."""
    for style in ("baseline", "optimized"):
        result = sac.shared_matches_pair(WIDTH, style)
        assert result["cases"] == 512, result
        assert result["mismatches"] == 0, result["examples"]


def test_the_shared_control_is_smaller_than_the_pair(table):
    for style in ("baseline", "optimized"):
        row = table[(style, "shared_control")]
        assert row["reference"] == "separate_pair"
        for metric in CHEAP:
            assert row[f"{metric}_saving_percent"] > 0, (style, metric, row)
            assert row[f"{metric}_shared"] < row[f"{metric}_reference"]


def test_the_serial_depth_saving_is_positive_and_the_per_op_one_is_reported(table):
    """A chip with one unit runs both operations back-to-back on the same
    hardware, so serial depth is the fair comparison; the single-operation depth
    is published too, including the case where it is worse."""
    for style in ("baseline", "optimized"):
        row = table[(style, "shared_control")]
        assert row["logical_depth_serial_saving_percent"] > 0, (style, row)
        assert row["logical_depth_saving_percent"] < 0, (style, row)


def test_the_garbage_saving_is_measured_not_assumed(table):
    row = table[("baseline", "shared_control")]
    assert row["garbage_qubits_shared"] == WIDTH
    assert row["garbage_qubits_reference"] == 2 * WIDTH
    assert row["garbage_qubits_saving_percent"] == pytest.approx(50.0)


def test_the_two_select_qubit_mux_is_more_expensive(table):
    mux = table[("baseline", "dual_control_mux")]
    shared = table[("baseline", "shared_control")]
    for metric in CHEAP:
        assert mux[f"{metric}_saving_percent"] < shared[f"{metric}_saving_percent"]
    assert mux["quantum_cost_saving_percent"] < 0, "gating every Toffoli must cost Toffolis"


def test_saving_percent_sign_convention():
    assert sac.saving_percent(10, 4) == 60.0
    assert sac.saving_percent(10, 15) == -50.0
    assert sac.saving_percent(0, 5) == 0.0


def test_the_verifier_proves_equivalence_on_both_engines(rows):
    """Equivalence is required of every architecture; a resource win is not.
    The two-select-qubit mux is published with pass=False precisely because the
    measured footprint is worse than the separate pair."""
    measured = [row for row in rows if row["approach"] != "separate_pair"]
    assert measured
    for row in measured:
        assert row["op_list_mismatches"] == 0, row
        assert row["aer_mismatches"] in (0, ""), row
        assert row["equivalence_pass"] and row["cases"] == 512, row
    for row in measured:
        won = row["approach"] == "shared_control"
        assert row["resources_pass"] is won, row
        assert row["pass"] is won, row


def test_the_reference_architecture_is_published_with_absolute_numbers(rows):
    """Every percentage must be traceable to a counted footprint in the same file."""
    reference = [row for row in rows if row["approach"] == "separate_pair"]
    assert len(reference) == 2
    for row in reference:
        assert row["units"] == 2
        assert row["qubits_raw_reference"] > row["qubits_reference"], \
            "the shared operand qubits must be visible in the footprint"
        assert row["quantum_cost_shared"] == row["quantum_cost_reference"]
        assert row["quantum_cost_saving_percent"] == 0.0


def test_one_mode_line_selects_both_operations():
    """The functional core of the contribution: M=0 adds, M=1 subtracts."""
    spec = sac.build_shared_control_addsub(WIDTH, "baseline")
    m = spec.registers["M"]
    assert len(m) == 1, "contribution 1 is a single control qubit"
    operands_and_carry = set(spec.registers["A"]) | set(spec.registers["B"])
    operands_and_carry |= set(spec.registers["R"]) | set(spec.registers["Cout"])
    assert not set(m) & operands_and_carry
    for a, b in ((5, 3), (2, 9), (0, 0), (15, 1)):
        for mode in (0, 1):
            measured = cu.op_list_results(spec, [{"A": a, "B": b, "M": mode}])[0]
            want = (a + b) if mode == 0 else (a - b) & 0b1111
            assert int(measured["R"]) == want & 0b1111, (a, b, mode)
            assert int(measured["A"]) == a and int(measured["B"]) == b


def test_the_dual_mux_select_lines_are_gated_not_wired():
    """With two select qubits only the matching block may act on the result."""
    spec = pna.build_nbit_design(WIDTH, "baseline", "dual_mux")
    for mode in (0, 1):
        for a, b in ((6, 2), (1, 13)):
            values = {"A": a, "B": b, "S_add": 1 - mode, "S_sub": mode}
            measured = cu.op_list_results(spec, [values])[0]
            want = (a + b) if mode == 0 else (a - b) & 0b1111
            assert int(measured["R"]) == want & 0b1111, mode

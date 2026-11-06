"""Phase 2 tests: the two-bit ALU slice (contribution 10).

The slice puts a one-hot decoded select channel around the adder-subtractor, so
two things have to hold at once: all 64 (A, B, code) cases must give the right
arithmetic or logic result, and the arithmetic channel must still be the same
circuit that passed the standalone adder/subtractor study - a slice may not
quietly reimplement addition. The decode uncomputation is measured both ways:
with it the one-hot select lines are returned to their initial value, without it
they are published as garbage.
"""

import pytest

from circuits import alu_slice_2bit as alu
from circuits import circuit_utils as cu
from verification import verify_alu as va

VARIANTS = {"alu_slice_2bit_uncomputed": True, "alu_slice_2bit_dirty_decode": False}


@pytest.fixture(scope="module")
def rows():
    return va.verify(write=False, confirm_aer=True)


@pytest.mark.parametrize("variant", sorted(VARIANTS.values(), reverse=True))
def test_all_64_cases_match_the_closed_form(variant):
    """The op-list comparison the verifier performs, on both variants."""
    assert alu.run_expected_check(alu.build_alu_slice_2bit(variant)) == []


def test_the_select_code_decodes_as_documented():
    """k = 2*S1 + S0 maps onto add, subtract, AND, OR."""
    assert alu.OPERATIONS == {0: "add", 1: "subtract", 2: "and", 3: "or"}
    spec = alu.build_alu_slice_2bit()
    measured = cu.op_list_results(spec, [{"A": 0b11, "B": 0b01, "S": code}
                                         for code in alu.OPERATIONS])
    want = {0: 0b00, 1: 0b10, 2: 0b01, 3: 0b11}
    for code, result in zip(sorted(want), measured):
        assert int(result["R"]) == want[code], (code, alu.OPERATIONS[code])


def test_the_logic_operations_are_bitwise(rows):
    logic = [row for row in rows if row["select_code"] in (2, 3)
             and row["engine"] == "op_list"]
    assert len(logic) == 2 * 2 * 16
    for row in logic:
        a, b = row["A"], row["B"]
        want = a & b if row["select_code"] == 2 else a | b
        assert row["expected_result"] == want, row
        assert row["measured_result"] == want, row


def test_the_arithmetic_channel_reuses_the_standalone_unit(rows):
    """The slice's carry must equal the standalone 2-bit unit's carry."""
    references = va.arithmetic_reference(2)
    checked = [row for row in rows if row["select_code"] in (0, 1)]
    assert checked and all(row["matches_adder_subtractor"] is True for row in checked)
    spec = alu.build_alu_slice_2bit()
    for a, b in ((1, 2), (3, 1), (2, 3)):
        for code, mode in ((0, "add"), (1, "subtract")):
            unit = cu.op_list_results(references[mode], [{"A": a, "B": b}])[0]
            slice_result = cu.op_list_results(
                spec, [{"A": a, "B": b, "S": code}])[0]
            assert int(slice_result["Cout"]) == int(unit["Cout"]), (a, b, code)
            assert int(slice_result["R"]) == int(unit["R"]), (a, b, code)


def test_the_select_lines_and_operands_survive_every_case():
    """A gated block must act as the identity, never as a partial write."""
    for variant in VARIANTS.values():
        spec = alu.build_alu_slice_2bit(variant)
        for values, measured in zip(alu.cases_values(),
                                    cu.op_list_results(spec, alu.cases_values())):
            for name in ("A", "B", "S"):
                assert int(measured[name]) == values[name], (variant, values, name)


def test_the_verifier_passes_on_every_row_and_engine(rows):
    assert len(rows) == 2 * 64 * 2, "both variants, 64 cases, op list and Aer"
    assert {r["engine"] for r in rows} == {"op_list", "aer"}
    assert {r["circuit"] for r in rows} == set(VARIANTS)
    failed = [row for row in rows if not row["pass"]]
    assert not failed, failed[:5]


def test_the_decode_uncomputation_is_a_measured_trade(rows):
    """Clearing the one-hot lines costs gates and buys back garbage - both
    numbers are published, neither is presented as a free win."""
    cost = {row["circuit"]: row for row in va.cost_rows()}
    clean, dirty = cost["alu_slice_2bit_uncomputed"], cost["alu_slice_2bit_dirty_decode"]
    assert clean["uncompute_decode"] and not dirty["uncompute_decode"]
    assert dirty["garbage_qubits"] == 10
    assert "Op_decode" in dirty["garbage_lines"] and "Op_decode" not in clean["garbage_lines"]
    assert clean["total_gates"] > dirty["total_gates"]
    assert clean["quantum_cost"] > dirty["quantum_cost"]
    for label in VARIANTS:
        assert all(row["pass"] for row in rows if row["circuit"] == label), label

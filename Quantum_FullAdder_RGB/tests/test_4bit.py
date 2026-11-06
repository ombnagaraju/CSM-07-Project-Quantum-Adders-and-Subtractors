"""Phase 2 tests: n-bit ripple adder and subtractor designs.

The arithmetic is checked exhaustively on the exact reversible op list (all 512
(A, B, mode) combinations at width 4) and on a sampled subset through the Qiskit
Aer simulator, because a design only counts as verified when both engines and
the closed-form expectation agree. The standalone adder/subtractor builders are
tested too: they are the "separate circuits" reference of contribution 1, so if
they drift the headline savings are meaningless.
"""

import pytest

from circuits import baseline_4bit_adder as b4
from circuits import circuit_utils as cu
from circuits import parametrized_nbit_adder as pna
from verification import check_case, expected_arithmetic, nbit_designs, run_both
from verification import verify_4bit

WIDTH = 4
CASES = b4.all_cases(WIDTH)
DESIGNS = nbit_designs(WIDTH)
LABELS = sorted(DESIGNS)
# A deterministic subset that spans both no-carry and carry-out cases as well as
# both modes; the Aer path is expensive, the op-list path is exhaustive.
PAIRS = [(0, 0), (1, 2), (5, 11), (8, 8), (12, 3), (15, 15), (7, 9), (2, 14)]


def cases_for_modes(*modes):
    return [(a, b, mode) for (a, b) in PAIRS for mode in modes]


def modes_of(label):
    """Which operation a standalone unit is supposed to perform."""
    if label.endswith("adder"):
        return (0,)
    if label.endswith("subtractor"):
        return (1,)
    return (0, 1)


def values_for(spec, cases):
    return verify_4bit.build_cases_values(spec, cases)


@pytest.mark.parametrize("label", LABELS)
def test_every_case_matches_the_two_complement_expectation(label):
    spec = DESIGNS[label]
    cases = [c for c in CASES if c[2] in modes_of(label)]
    measured = cu.op_list_results(spec, values_for(spec, cases))
    for (a, b, mode), result in zip(cases, measured):
        want, carry = expected_arithmetic(a, b, mode, WIDTH)
        assert int(result["R"]) == want, (label, a, b, mode)
        assert int(result["Cout"]) == carry, (label, a, b, mode)


@pytest.mark.parametrize("label", LABELS)
def test_operands_survive(label):
    spec = DESIGNS[label]
    case_values = values_for(spec, cases_for_modes(*modes_of(label)))
    for values_row, measured in zip(case_values, cu.op_list_results(spec, case_values)):
        checks = check_case(spec, values_row, measured)
        assert checks["inputs_preserved"], (label, values_row, checks["preserved_detail"])


@pytest.mark.parametrize("label", LABELS)
def test_only_declared_garbage_may_stay_dirty(label):
    """A line that the design does not publish as garbage must return to |0>."""
    spec = DESIGNS[label]
    case_values = values_for(spec, cases_for_modes(*modes_of(label)))
    for values_row, measured in zip(case_values, cu.op_list_results(spec, case_values)):
        detail = check_case(spec, values_row, measured)["restored_detail"]
        dirty = {name for name, restored in detail.items() if not restored}
        assert dirty <= set(spec.garbage), (label, values_row, sorted(dirty))


def test_the_baseline_carry_chain_really_is_garbage():
    """The garbage claim is measured, not assumed: the Toffoli-CNOT chain keeps
    information about the inputs, while the Peres chain never does."""
    baseline = DESIGNS["baseline_adder"]
    optimized = DESIGNS["optimized_adder"]
    cases = [c for c in CASES if c[2] == 0]
    dirty = [values for values, measured in zip(
        values_for(baseline, cases), cu.op_list_results(baseline, values_for(baseline, cases)))
        if int(measured["Carry_internal"]) != 0]
    assert dirty, "baseline declares Carry_internal as garbage but never leaves it set"
    assert all(check_case(optimized, values, measured)["ancilla_restored"]
               for values, measured in zip(
                   values_for(optimized, cases),
                   cu.op_list_results(optimized, values_for(optimized, cases))))


@pytest.mark.parametrize("label", LABELS)
def test_aer_agrees_with_the_op_list(label):
    spec = DESIGNS[label]
    case_values = values_for(spec, cases_for_modes(*modes_of(label)))
    _, aer, agree = run_both(spec, case_values, confirm_aer=True, chunk=len(case_values))
    assert agree, label
    assert len(aer) == len(case_values)


def test_the_borrow_convention_is_the_documented_one():
    """Cout=1 during subtraction means A >= B, so borrow = NOT Cout."""
    spec = DESIGNS["baseline_subtractor"]
    for a, b in ((0, 1), (3, 5), (15, 15), (9, 2)):
        measured = cu.op_list_results(spec, [{"A": a, "B": b}])[0]
        borrow = 1 - int(measured["Cout"])
        assert int(measured["R"]) == (a - b) & 0b1111
        assert borrow == int(a < b), (a, b)


def test_standalone_builders_are_the_pair_reference():
    """build_baseline_4bit_* must be the same circuits the pair comparison uses."""
    units = b4.build_baseline_4bit_units()
    assert set(units) == {"adder", "subtractor"}
    for key, spec in units.items():
        reference = getattr(b4, f"build_baseline_4bit_{key}")()
        assert spec.ops == reference.ops
        assert spec.n_qubits == reference.n_qubits
        assert spec.registers == reference.registers


def test_shared_control_unit_replaces_the_pair():
    """One M line turns the same ripple into a subtractor: the two's-complement
    complement-and-increment pass is present in both directions."""
    shared = pna.build_nbit_design(WIDTH, "baseline", "shared")
    add = pna.build_nbit_design(WIDTH, "baseline", "add")
    assert len(shared.ops) == len(add.ops) + 2 * WIDTH + 1
    assert shared.n_qubits == add.n_qubits + 1
    m = shared.registers["M"][0]
    conditioned = [op for op in shared.ops if op[0] == "cx" and op[1] == m]
    assert len(conditioned) == 2 * WIDTH + 1


@pytest.mark.parametrize("style", pna.STYLES)
def test_garbage_follows_the_documented_style(style):
    """The Toffoli-CNOT ripple leaves its carry chain dirty; the Peres ripple
    writes each sum onto its carry line and therefore declares no garbage."""
    spec = pna.build_nbit_design(2, style, "add")
    assert spec.garbage == (("Carry_internal",) if style == "baseline" else ())


def test_the_dual_mux_rejects_the_style_it_cannot_build():
    """The Peres style has no separate result register for two gated blocks to
    share, so the combination is refused with a reason instead of faked."""
    with pytest.raises(NotImplementedError, match="result register"):
        pna.build_nbit_design(4, "optimized", "dual_mux")


def test_combined_metrics_share_the_operand_qubits():
    """The separate-pair footprint counts A and B once, not once per unit."""
    pair = list(pna.build_adder_pair(WIDTH, "baseline").values())
    combined = pna.combined_metrics(pair)
    assert combined["qubits_raw"] == sum(s.n_qubits for s in pair)
    assert combined["qubits"] == combined["qubits_raw"] - 2 * WIDTH
    assert combined["logical_depth_serial"] == sum(
        cu.logical_depth(s) for s in pair)

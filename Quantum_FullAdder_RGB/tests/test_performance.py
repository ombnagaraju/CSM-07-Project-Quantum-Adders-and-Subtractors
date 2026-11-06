"""Phase 5 tests: resource metrics, optimization acceptance and the cost model.

Every expectation here is a number the project publishes. The NCV decomposition
test rebuilds the Toffoli and Peres sequences from their elementary
controlled-V gates and checks the resulting 8x8 unitary, so the cost model is
executable documentation rather than a comment.
"""

import os

import numpy as np
import pytest

import config
from circuits import (
    baseline_fulladder,
    circuit_utils as cu,
    peres_fulladder,
    uncomputation,
)
from performance import (
    comparison,
    energy_model,
    fault_tolerant_cost,
    quantum_cost,
    visualization,
)

PAIR = {pair["family"]: pair for pair in comparison.PAIRS}


@pytest.fixture(scope="module")
def outcome():
    return comparison.verify(write=False)


# ---------------------------------------------------------------------------
# The NCV-L model itself
# ---------------------------------------------------------------------------
X = np.array([[0, 1], [1, 0]], dtype=complex)


def _sqrt_x() -> np.ndarray:
    values, vectors = np.linalg.eig(X)
    return vectors @ np.diag(np.sqrt(values)) @ np.linalg.inv(vectors)


SQRT_X = _sqrt_x()
I2 = np.eye(2, dtype=complex)


def _cnot(control: int, target: int, n: int = 3) -> np.ndarray:
    matrix = np.zeros((2 ** n, 2 ** n), dtype=complex)
    for state in range(2 ** n):
        flipped = state ^ ((1 << target) if (state >> control) & 1 else 0)
        matrix[flipped, state] = 1
    return matrix


def _controlled_v(control: int, target: int, dagger: bool = False,
                  n: int = 3) -> np.ndarray:
    base = SQRT_X.conj().T if dagger else SQRT_X
    matrix = np.zeros((2 ** n, 2 ** n), dtype=complex)
    for state in range(2 ** n):
        if (state >> control) & 1:
            target_bit = (state >> target) & 1
            for output_bit in (0, 1):
                if abs(base[output_bit, target_bit]) > 1e-12:
                    out = (state & ~(1 << target)) | (output_bit << target)
                    matrix[out, state] += base[output_bit, target_bit]
        else:
            matrix[state, state] = 1
    return matrix


def _sequence(names) -> np.ndarray:
    matrix = np.eye(8, dtype=complex)
    builders = {"cx": _cnot, "cv": _controlled_v,
                "cvdg": lambda c, t: _controlled_v(c, t, dagger=True)}
    for name, control, target in names:
        matrix = builders[name](control, target) @ matrix
    return matrix


def _same_up_to_phase(left: np.ndarray, right: np.ndarray) -> bool:
    index = np.unravel_index(np.argmax(np.abs(right)), right.shape)
    if abs(left[index]) < 1e-9:
        return False
    phase = left[index] / right[index]
    return abs(abs(phase) - 1) < 1e-9 and np.allclose(left, phase * right, atol=1e-9)


def _toffoli_permutation() -> np.ndarray:
    matrix = np.zeros((8, 8), dtype=complex)
    for state in range(8):
        a, b, c = ((state >> q) & 1 for q in range(3))
        matrix[state ^ ((a & b) << 2), state] = 1
    return matrix


def _peres_permutation() -> np.ndarray:
    matrix = np.zeros((8, 8), dtype=complex)
    for state in range(8):
        a, b, c = ((state >> q) & 1 for q in range(3))
        out = a | ((a ^ b) << 1) | (((a & b) ^ c) << 2)
        matrix[out, state] = 1
    return matrix


def test_ncv_toffoli_decomposition_is_an_exact_toffoli():
    sequence = (("cx", 0, 1), ("cv", 0, 2), ("cvdg", 1, 2),
                ("cx", 0, 1), ("cv", 1, 2))
    assert list(config.NCV_COSTS["ccx"].decomposition) == [
        "cx", "cv", "cvdg", "cx", "cv"]
    assert len(sequence) == config.NCV_COSTS["ccx"].cost
    assert _same_up_to_phase(_sequence(sequence), _toffoli_permutation())


def test_ncv_peres_decomposition_is_an_exact_peres():
    sequence = (("cv", 0, 2), ("cv", 1, 2), ("cx", 0, 1), ("cvdg", 1, 2))
    assert list(config.NCV_COSTS["peres"].decomposition) == [
        "cv", "cv", "cx", "cvdg"]
    assert len(sequence) == config.NCV_COSTS["peres"].cost
    assert _same_up_to_phase(_sequence(sequence), _peres_permutation())


def test_elementary_costs_follow_the_ncv_convention():
    for name in ("x", "cx", "cv", "cvdg"):
        assert config.gate_quantum_cost(name) == 1
    assert config.gate_quantum_cost("ccx") == 5
    assert config.gate_quantum_cost("peres") == 4
    assert config.gate_quantum_cost("id") == 0
    with pytest.raises(KeyError):
        config.gate_quantum_cost("swap")


# ---------------------------------------------------------------------------
# Measured resource rows
# ---------------------------------------------------------------------------
def test_baseline_and_optimized_rows_hold_the_measured_numbers(outcome):
    baseline = {row["family"]: row for row in outcome["baseline"]}
    optimized = {row["family"]: row for row in outcome["optimized"]}
    expected = {
        "fulladder": ((6, 14, 6, 1), (5, 13, 5, 0)),
        "adder4_add": ((24, 56, 17, 4), (12, 36, 13, 0)),
        "adder4_shared": ((33, 65, 18, 4), (21, 45, 14, 0)),
    }
    for family, (base, opt) in expected.items():
        assert (baseline[family]["total_gates"], baseline[family]["quantum_cost"],
                baseline[family]["qubits"], baseline[family]["garbage_qubits"]) == base
        assert (optimized[family]["total_gates"], optimized[family]["quantum_cost"],
                optimized[family]["qubits"], optimized[family]["garbage_qubits"]) == opt


def test_decomposition_columns_are_clifford_t_counts(outcome):
    baseline = {row["family"]: row for row in outcome["baseline"]}
    optimized = {row["family"]: row for row in outcome["optimized"]}
    assert baseline["fulladder"]["decomposed_gates"] == 34      # 2 Toffoli + 4 CNOT
    assert optimized["fulladder"]["decomposed_gates"] == 33     # 2 Toffoli + 3 CNOT
    assert baseline["fulladder"]["decomposed_t_gates"] == 14
    assert optimized["fulladder"]["decomposed_t_gates"] == 14
    assert baseline["fulladder"]["decomposed_cx_gates"] == 16
    assert optimized["fulladder"]["decomposed_cx_gates"] == 15
    for family in expected_families():
        # Both styles use two Toffoli-equivalent blocks per bit, so the T count
        # must be identical; the saving is in CNOTs, qubits and garbage.
        assert (optimized[family]["decomposed_t_gates"]
                == baseline[family]["decomposed_t_gates"])
    assert baseline["adder4_add"]["decomposed_t_gates"] == 56


def expected_families():
    return ("fulladder", "adder4_add", "adder4_shared")


def test_gate_comparison_reductions_and_acceptance(outcome):
    costs = {row["pair"]: row for row in outcome["costs"]}
    assert costs["fulladder"]["baseline_cost"] == 14
    assert costs["fulladder"]["optimized_cost"] == 13
    assert costs["fulladder"]["reduction_percent"] == pytest.approx(7.14, abs=0.01)
    assert costs["adder4_add"]["reduction_percent"] == pytest.approx(35.71, abs=0.01)
    assert costs["adder4_shared"]["reduction_percent"] == pytest.approx(30.77, abs=0.01)
    assert all(row["acceptance_pass"] for row in outcome["costs"])

    gates = {(row["pair"], row["metric"]): row for row in outcome["gates"]}
    for family in expected_families():
        total = gates[(family, "total_gates")]
        assert total["optimized"] < total["baseline"]
        assert total["reduction_percent"] > 0
        assert total["lower_or_equal"] is True
    assert gates[("adder4_add", "total_gates")]["reduction_percent"] == 50.0
    assert gates[("adder4_shared", "garbage_qubits")]["reduction_percent"] == 100.0
    assert len(outcome["gates"]) == len(comparison.GATE_METRICS) * len(comparison.PAIRS)


def test_depth_is_reported_at_three_levels_without_mixing_them(outcome):
    depths = {(row["pair"], row["depth_kind"]): row for row in outcome["depths"]}
    assert depths[("fulladder", "logical")]["baseline_depth"] == 6
    assert depths[("fulladder", "logical")]["optimized_depth"] == 5
    assert depths[("fulladder", "decomposed_clifford_t")]["baseline_depth"] == 24
    assert depths[("fulladder", "decomposed_clifford_t")]["optimized_depth"] == 23
    transpiled = depths[("adder4_shared", "transpiled")]
    assert transpiled["topology"] == "line_18"
    assert transpiled["optimized_depth"] < transpiled["baseline_depth"]
    for row in outcome["depths"]:
        assert row["baseline_depth"] >= 1 and row["optimized_depth"] >= 1


def test_quantum_cost_breakdown_is_additive():
    base = quantum_cost.cost_breakdown(baseline_fulladder.build_baseline_fulladder())
    assert base == {"x_cost": 0, "cx_cost": 4, "ccx_cost": 10,
                    "peres_cost": 0, "quantum_cost": 14}
    peres = quantum_cost.cost_breakdown(peres_fulladder.build_peres_fulladder())
    assert peres["peres_cost"] == 8 and peres["cx_cost"] == 1
    assert peres["quantum_cost"] == 9
    assert quantum_cost.reduction_percent(10, 4) == 60.0
    assert quantum_cost.reduction_percent(10, 15) == -50.0
    assert quantum_cost.reduction_percent(0, 5) == 0.0


def test_comparison_csvs_are_written_with_the_same_rows():
    comparison.verify(write=True, charts=False)
    for key in ("baseline_metrics", "optimized_metrics", "gate_comparison",
                "quantum_cost_comparison", "circuit_depth_comparison"):
        assert config.read_rows(key)
    stored = config.read_rows("quantum_cost_comparison")
    assert {row["pair"] for row in stored} == set(PAIR)
    assert all(row["acceptance_pass"] == "True" for row in stored)


def test_charts_are_rendered_from_the_csvs():
    paths = visualization.render_comparison_charts()
    names = {os.path.basename(path) for path in paths}
    for expected in ("gate_count_comparison.png", "quantum_cost_comparison.png",
                     "circuit_depth_comparison.png", "qubit_usage.png",
                     "reduction_summary.png"):
        assert expected in names
    assert all(os.path.getsize(path) > 1000 for path in paths)


# ---------------------------------------------------------------------------
# Fault-tolerant and energy estimates
# ---------------------------------------------------------------------------
def test_fault_tolerant_estimate_uses_measured_blocks_and_t_counts():
    blocks, depth = fault_tolerant_cost.toffoli_layout(
        baseline_fulladder.build_baseline_fulladder())
    assert (blocks, depth) == (2, 4)
    add_blocks, add_depth = fault_tolerant_cost.toffoli_layout(
        PAIR["adder4_add"]["optimized"])
    assert (add_blocks, add_depth) == (8, 5)
    assert fault_tolerant_cost.code_distance() == 3
    assert fault_tolerant_cost.code_distance(3e-3) == 7

    rows = fault_tolerant_cost.verify(write=True)
    by_key = {(row["pair"], row["role"], row["style"]): row for row in rows}
    for pair in comparison.PAIRS:
        for style in config.DECOMPOSITION_STYLES:
            base = by_key[(pair["family"], "baseline", style)]
            opt = by_key[(pair["family"], "optimized", style)]
            assert base["t_count"] == base["toffoli_blocks"] * config.TOFFOLI_T_COUNT[style]
            assert opt["physical_qubits_estimate"] < base["physical_qubits_estimate"]
            assert opt["logical_qubits"] < base["logical_qubits"]


def test_energy_model_reports_zero_landauer_bound_for_reversible_designs():
    rows = energy_model.verify(write=True)
    assert all(int(row["irreversible_erasures"]) == 0 for row in rows)
    assert all(float(row["landauer_bound_joules"]) == 0.0 for row in rows)
    by_circuit = {row["circuit"]: row for row in rows}
    assert (float(by_circuit["optimized_fulladder"]["estimated_switching_joules"])
            < float(by_circuit["baseline_fulladder"]["estimated_switching_joules"]))
    assert config.ENERGY_MODEL_NOTE in rows[0]["model_note"]

    reset_variant = uncomputation.measurement_based_uncompute(
        baseline_fulladder.build_baseline_fulladder(), method="reset")
    priced = energy_model.estimate(reset_variant, "fulladder", "variant")
    assert priced["irreversible_erasures"] == cu.logical_counts(
        reset_variant)["reset"] > 0
    assert priced["landauer_bound_joules"] > 0.0

"""Phase 3 tests: the measured Toffoli decomposition and the selector rule.

Both styles must implement an exact Toffoli, and the T-equivalent count stored
in ``config`` must be the measured one. The selector is only allowed to pick a
style that wins on the documented error model; in this toolchain that is
``low_depth`` on every backend, and the tests pin that measured conclusion
instead of assuming it.
"""

import math

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import CCXGate
from qiskit.quantum_info import Operator

import config
from transpilation import decomposition_selector as ds


@pytest.fixture(scope="module")
def measured():
    return {style: ds.measure(style) for style in config.DECOMPOSITION_STYLES}


def test_both_styles_build_an_exact_toffoli(measured):
    ideal = Operator(CCXGate())
    for style, row in measured.items():
        circuit = ds.toffoli_circuit(style)
        assert Operator(circuit).equiv(ideal)
        assert row["unitary_fidelity"] == 1.0
        assert row["unitary_equivalent"] is True


def test_config_t_counts_are_the_measured_values(measured):
    for style, row in measured.items():
        assert row["t_equivalent_gates"] == config.TOFFOLI_T_COUNT[style]
        assert row["t_depth"] == config.TOFFOLI_T_DEPTH[style]
    # The phase-polynomial route is not a T-count win in this toolchain: its
    # seven +/-45-degree phase gates are T gates. No 4-T claim is recorded.
    assert measured["low_depth"]["t_equivalent_gates"] == 7
    assert measured["low_t_count"]["phase_gates"] == 7
    assert measured["low_t_count"]["t_equivalent_gates"] == 7


def test_low_depth_is_smaller_on_every_other_axis(measured):
    shallow = measured["low_depth"]
    phase = measured["low_t_count"]
    assert shallow["total_gates"] < phase["total_gates"]
    assert shallow["cx_gates"] < phase["cx_gates"]
    assert shallow["depth"] < phase["depth"]
    assert shallow["t_depth"] < phase["t_depth"]


def test_a_45_degree_phase_gate_is_counted_as_a_t_gate():
    circuit = QuantumCircuit(1)
    circuit.p(math.pi / 4, 0)
    circuit.p(-math.pi / 4, 0)
    circuit.p(math.pi / 2, 0)          # S is Clifford, not T-equivalent
    assert ds.t_equivalent_count(circuit) == 2


def test_t_depth_groups_only_t_layers():
    circuit = QuantumCircuit(2)
    circuit.t(0)
    circuit.t(1)
    circuit.h(0)                       # Clifford, does not advance the T clock
    circuit.t(0)
    assert ds.t_depth(circuit) == 2


def test_selector_picks_the_style_with_the_highest_modelled_success():
    rows = ds.selector_table()
    assert {row["backend"] for row in rows} == {
        profile.name for profile in config.BACKEND_PROFILES}
    for backend in {row["backend"] for row in rows}:
        subset = [row for row in rows if row["backend"] == backend]
        chosen = [row for row in subset if row["selected_for_backend"]]
        assert len(chosen) == 1
        best = max(subset, key=lambda row: row["modelled_success_probability"])
        assert chosen[0]["style"] == best["style"]
        assert chosen[0]["style"] == "low_depth"


def test_modelled_success_uses_the_profile_error_rates():
    row = ds.measure("low_depth")
    profile = config.get_backend_profile("ibm_fake_linen")
    expected = ((1 - profile.cx_error) ** row["cx_gates"]
                * (1 - profile.u2_error) ** row["single_qubit_gates"])
    assert ds.modelled_success(row, profile) == pytest.approx(expected)
    assert ds.chosen_style("ibm_fake_linen") == "low_depth"
    with pytest.raises(KeyError):
        ds.toffoli_circuit("not_a_style")


def test_verify_writes_one_row_per_style_and_backend():
    rows = ds.verify(write=True)
    stored = config.read_rows("decomposition_fidelity")
    assert len(stored) == len(rows) == (len(config.DECOMPOSITION_STYLES)
                                        * len(config.BACKEND_PROFILES))
    assert all(row["unitary_fidelity"] == "1.0" for row in stored)
    assert sum(row["selected_for_backend"] == "True" for row in stored) == len(
        config.BACKEND_PROFILES)

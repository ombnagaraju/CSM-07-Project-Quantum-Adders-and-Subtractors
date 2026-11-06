"""Phase 3 tests: coupling maps, the fixed transpilation recipe and its report.

These tests pin the parts of the benchmark that make comparisons fair: every
topology really has the advertised size, infeasible designs are refused instead
of padded, all circuits land in the same target basis, and the post-transpile
row is internally consistent. The control-qubit claim is re-checked after
routing, which is the whole point of contribution 2.
"""

import config
import pytest

from circuits import baseline_fulladder
from circuits.parametrized_nbit_adder import build_nbit_design
from transpilation import cost_report, topologies


def test_every_declared_topology_builds_a_map_of_the_declared_size():
    assert len(config.TOPOLOGIES) >= 6
    kinds = {spec.kind for spec in config.TOPOLOGIES}
    assert kinds == {"line", "grid", "heavy_hex", "all_to_all"}
    for spec in config.TOPOLOGIES:
        cmap = topologies.coupling_map(spec)
        assert cmap.size() == spec.n_qubits
        assert len(topologies.coupling_edges(spec)) >= spec.n_qubits - 1


def test_line_and_grid_edge_counts_match_the_graph_definition():
    assert len(topologies.coupling_edges("line_12")) == 22          # 11 undirected x 2
    grid = topologies.get_topology("grid_3x4")
    undirected = (grid.grid_rows * (grid.grid_cols - 1)
                  + grid.grid_cols * (grid.grid_rows - 1))
    assert len(topologies.coupling_edges("grid_3x4")) == 2 * undirected
    heavy = topologies.get_topology("heavy_hex_3")
    assert heavy.n_qubits == 19
    assert len(topologies.coupling_edges("heavy_hex_3")) == 40


def test_an_infeasible_design_is_refused_not_padded():
    baseline = baseline_fulladder.build_baseline_fulladder()
    assert baseline.n_qubits == 6
    assert not topologies.fits(baseline, "line_5")
    with pytest.raises(topologies.CircuitTooWide):
        topologies.transpile_spec(baseline, "line_5")


def test_transpiled_circuits_contain_only_the_shared_target_basis():
    design = build_nbit_design(4, "optimized", "shared")
    for name in ("line_18", "grid_4x5", "heavy_hex_3", "all_to_all_18"):
        circuit = topologies.transpile_spec(design, name)
        assert set(topologies.basis_counts(circuit)) <= set(config.TARGET_BASIS_GATES)


def test_post_transpile_metrics_are_self_consistent():
    design = baseline_fulladder.build_baseline_fulladder()
    circuit = topologies.transpile_spec(design, "line_12")
    row = topologies.post_transpile_metrics(circuit)
    counts = topologies.basis_counts(circuit)
    assert row["total_gates"] == sum(counts.values())
    assert row["other_gates"] == 0
    assert row["quantum_cost"] == (
        row["cx_gates"] + row["x_gates"] + row["rz_gates"] + row["sx_gates"])
    assert row["id_gates"] == 0                  # identities are free, not counted in cost
    assert row["used_physical_qubits"] <= row["physical_qubits"] == circuit.num_qubits
    assert row["depth"] >= 1


def test_transpilation_is_deterministic_for_the_shared_seed():
    design = build_nbit_design(4, "baseline", "shared")
    first = topologies.post_transpile_metrics(
        topologies.transpile_spec(design, "grid_4x5"))
    second = topologies.post_transpile_metrics(
        topologies.transpile_spec(design, "grid_4x5"))
    assert first == second


def test_routing_preserves_the_optimization_gap_on_the_same_graph():
    baseline = build_nbit_design(4, "baseline", "shared")
    optimized = build_nbit_design(4, "optimized", "shared")
    base = topologies.post_transpile_metrics(
        topologies.transpile_spec(baseline, "line_18"))
    opt = topologies.post_transpile_metrics(
        topologies.transpile_spec(optimized, "line_18"))
    assert (opt["cx_gates"] < base["cx_gates"]
            and opt["total_gates"] < base["total_gates"]
            and opt["depth"] < base["depth"]
            and opt["quantum_cost"] < base["quantum_cost"])


def test_topology_table_skips_the_graphs_that_cannot_hold_the_design():
    rows = cost_report.topology_table(topology_names=("line_12", "line_18"))
    keys = {(row["circuit"], row["topology"]) for row in rows}
    assert all(row["logical_qubits"] <= row["topology_qubits"] for row in rows)
    assert ("fulladder_baseline", "line_12") in keys
    assert ("adder4_baseline_shared", "line_12") not in keys
    assert ("adder4_baseline_shared", "line_18") in keys
    # 1-bit designs fit both graphs; only the 4-bit designs need line_18.
    assert len(rows) == 8


def test_topology_csv_round_trips_the_measured_rows():
    rows = cost_report.verify(write=True, update_control=False)
    stored = config.read_rows("topology_metrics")
    assert len(stored) == len(rows)
    for written, read in zip(rows, stored):
        assert read["circuit"] == written["circuit"]
        assert int(read["total_gates"]) == written["total_gates"]
        assert int(read["quantum_cost"]) == written["quantum_cost"]


def test_control_savings_survive_routing():
    rows = cost_report.update_control_savings()
    by_key = {(row["style"], row["approach"]): row for row in rows}
    for row in rows:
        assert row["transpiled_topology"] == cost_report.CONTROL_TOPOLOGY
        for metric in cost_report.CONTROL_METRICS:
            assert f"{metric}_transpiled_saving_percent" in row

    reference = by_key[("optimized", "separate_pair")]
    shared = by_key[("optimized", "shared_control")]
    mux = by_key[("baseline", "dual_control_mux")]
    assert float(reference["total_gates_transpiled_saving_percent"]) == 0.0
    assert shared["total_gates_transpiled_saving_percent"] > 0
    assert shared["quantum_cost_transpiled_saving_percent"] > 0
    assert shared["cx_gates_transpiled_saving_percent"] > 0
    # The mux is the negative control: gating both blocks costs far more than it saves.
    assert mux["total_gates_transpiled_saving_percent"] < -100

    stored = {(row["style"], row["approach"]): row for row in
              config.read_rows("control_savings")}
    assert stored[("optimized", "shared_control")][
        "total_gates_transpiled_shared"] == str(
            shared["total_gates_transpiled_shared"])

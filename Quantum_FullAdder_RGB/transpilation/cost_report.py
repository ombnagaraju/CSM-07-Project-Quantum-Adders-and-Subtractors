"""Post-transpilation cost report for every benchmarked topology (contribution 2).

The logical columns in :mod:`performance` answer "how big is the arithmetic
block"; this module answers "what does it cost after routing and translation on
a concrete device graph". Both are written with the same NCV-L pricing, so the
two views stay comparable (contribution 5).

``topology_metrics.csv`` holds one row per feasible (design, topology) pair.
``control_qubit_savings.csv`` is extended in place with the transpiled columns
for the one-control-qubit comparison, because that claim must survive routing.
"""

from __future__ import annotations

from circuits import baseline_fulladder, optimized_fulladder, peres_fulladder
from circuits.parametrized_nbit_adder import (
    build_adder_pair,
    build_nbit_design,
)
from circuits.shared_addsub_control import build_shared_control_addsub
from transpilation import topologies

CONTROL_TOPOLOGY = "line_24"
CONTROL_METRICS = ("cx_gates", "total_gates", "depth", "quantum_cost")


def benchmark_designs() -> dict:
    """Named designs used for the topology sweep, with their family and role."""
    return {
        "fulladder_baseline": {
            "family": "fulladder", "role": "baseline",
            "spec": baseline_fulladder.build_baseline_fulladder()},
        "fulladder_peres": {
            "family": "fulladder", "role": "reference",
            "spec": peres_fulladder.build_peres_fulladder()},
        "fulladder_optimized": {
            "family": "fulladder", "role": "optimized",
            "spec": optimized_fulladder.build_optimized_fulladder()},
        "adder4_baseline_shared": {
            "family": "adder4_shared", "role": "baseline",
            "spec": build_nbit_design(4, "baseline", "shared")},
        "adder4_optimized_shared": {
            "family": "adder4_shared", "role": "optimized",
            "spec": build_nbit_design(4, "optimized", "shared")},
    }


def topology_table(topology_names=None) -> list[dict]:
    """One row per design/topology combination whose graph is wide enough."""
    designs = benchmark_designs()
    names = list(topology_names or [spec.name for spec in topologies.config.TOPOLOGIES])
    rows: list[dict] = []
    for circuit, entry in designs.items():
        spec = entry["spec"]
        for name in names:
            topo = topologies.get_topology(name)
            if not topologies.fits(spec, topo):
                continue
            transpiled = topologies.transpile_spec(spec, topo)
            metrics = topologies.post_transpile_metrics(transpiled)
            rows.append({
                "circuit": circuit,
                "family": entry["family"],
                "role": entry["role"],
                "logical_qubits": spec.n_qubits,
                "topology": topo.name,
                "topology_kind": topo.kind,
                "topology_qubits": topo.n_qubits,
                **metrics,
                "routing_overhead_qubits": (metrics["used_physical_qubits"]
                                            - spec.n_qubits),
            })
    return rows


def _transpiled_footprint(specs, topology_name: str) -> dict:
    """Sum gate counts over units, keep the parallel depth (max), price together."""
    metrics = [topologies.post_transpile_metrics(
        topologies.transpile_spec(spec, topology_name)) for spec in specs]
    combined = {"cx_gates": 0, "total_gates": 0, "quantum_cost": 0, "depth": 0}
    for row in metrics:
        for key in ("cx_gates", "total_gates", "quantum_cost"):
            combined[key] += row[key]
        combined["depth"] = max(combined["depth"], row["depth"])
    return combined


def _control_designs(width: int, style: str, approach: str) -> list:
    if approach == "separate_pair":
        return list(build_adder_pair(width, style).values())
    if approach == "shared_control":
        return [build_shared_control_addsub(width, style)]
    if approach == "dual_control_mux":
        return [build_nbit_design(width, style, "dual_mux",
                                  name=f"{style}_dual_mux_{width}bit")]
    raise ValueError(f"Unknown control approach '{approach}'")


def update_control_savings(topology_name: str = CONTROL_TOPOLOGY) -> list[dict]:
    """Append transpiled columns to control_qubit_savings.csv and rewrite it.

    The reference is the separate adder/subtractor pair. For that pair the
    circuit count is the sum of its two units and the depth is their parallel
    maximum, which is the honest footprint of a chip that offers both
    operations; the shared design is measured as the single unit it is.
    """
    rows = topologies.config.read_rows("control_savings")
    if not rows:
        from verification import verify_control_savings

        rows = verify_control_savings.verify(write=False)

    cache: dict[tuple, dict] = {}
    references: dict[tuple, dict] = {}
    for row in rows:
        key = (int(row["width"]), row["style"], row["approach"])
        cache[key] = _transpiled_footprint(
            _control_designs(key[0], key[1], key[2]), topology_name)
        if row["approach"] == "separate_pair":
            references[(key[0], key[1])] = cache[key]

    for row in rows:
        key = (int(row["width"]), row["style"], row["approach"])
        reference = references[(key[0], key[1])]
        measured = cache[key]
        row["transpiled_topology"] = topology_name
        for metric in CONTROL_METRICS:
            row[f"{metric}_transpiled_shared"] = measured[metric]
            row[f"{metric}_transpiled_reference"] = reference[metric]
            row[f"{metric}_transpiled_saving_percent"] = (
                round((reference[metric] - measured[metric]) / reference[metric] * 100.0, 2)
                if reference[metric] else 0.0)
    topologies.config.write_rows(rows, "control_savings")
    return rows


def verify(write: bool = True, update_control: bool = True) -> list[dict]:
    rows = topology_table()
    if write and rows:
        topologies.config.write_rows(rows, "topology_metrics")
    if update_control:
        update_control_savings()
    return rows


def summary(rows: list[dict]) -> str:
    lines = []
    for row in rows:
        lines.append(
            f"{row['circuit']:26s} {row['topology']:14s} "
            f"qubits={row['used_physical_qubits']:3d}/{row['physical_qubits']:<3d} "
            f"cx={row['cx_gates']:4d} gates={row['total_gates']:4d} "
            f"depth={row['depth']:4d} cost={row['quantum_cost']:5d}")
    return "\n".join(lines)


if __name__ == "__main__":
    topologies.config.ensure_directories()
    table = verify()
    print(summary(table))
    print(f"\nwrote {len(table)} rows to {topologies.config.csv_path('topology_metrics')} "
          "and extended control_qubit_savings.csv")

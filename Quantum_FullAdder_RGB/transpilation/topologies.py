"""Hardware topologies and one fixed transpilation recipe (contribution 2).

Every post-transpilation number in the project comes from :func:`transpile_spec`
with the settings stored in :mod:`config`, so a baseline and an optimised design
are always measured on the same graph with the same basis, layout method,
optimisation level and transpiler seed.

The graph sizes are calibrated to the designs that must fit on them. Infeasible
combinations raise :class:`CircuitTooWide` instead of silently padding the
circuit onto idle qubits, because an idle-qubit count is not a resource saving.
"""

from __future__ import annotations

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap

import config
from circuits import circuit_utils as cu


class CircuitTooWide(ValueError):
    """Raised when a design needs more qubits than the chosen graph provides."""


TOPOLOGIES_BY_NAME = {spec.name: spec for spec in config.TOPOLOGIES}


def get_topology(name: str) -> config.TopologySpec:
    try:
        return TOPOLOGIES_BY_NAME[name]
    except KeyError:
        raise KeyError(f"Unknown topology '{name}'. Options: "
                       f"{sorted(TOPOLOGIES_BY_NAME)}") from None


def coupling_map(topology: config.TopologySpec | str) -> CouplingMap:
    """Build the coupling map for one topology description."""
    spec = get_topology(topology) if isinstance(topology, str) else topology
    if spec.kind == "line":
        cmap = CouplingMap.from_line(spec.n_qubits)
    elif spec.kind == "grid":
        cmap = CouplingMap.from_grid(spec.grid_rows, spec.grid_cols,
                                     bidirectional=True)
    elif spec.kind == "heavy_hex":
        cmap = CouplingMap.from_heavy_hex(spec.heavy_hex_d, bidirectional=True)
    elif spec.kind == "all_to_all":
        cmap = CouplingMap.from_full(spec.n_qubits)
    else:
        raise ValueError(f"Unknown topology kind '{spec.kind}'")
    if cmap.size() != spec.n_qubits:
        raise ValueError(f"Topology '{spec.name}' declares {spec.n_qubits} qubits "
                         f"but its coupling map has {cmap.size()}")
    return cmap


def coupling_edges(topology: config.TopologySpec | str) -> list[list[int]]:
    return [list(edge) for edge in coupling_map(topology).get_edges()]


def fits(spec: cu.CircuitSpec | int, topology: config.TopologySpec | str) -> bool:
    needed = spec if isinstance(spec, int) else spec.n_qubits
    topo = get_topology(topology) if isinstance(topology, str) else topology
    return needed <= topo.n_qubits


def transpile_spec(spec: cu.CircuitSpec, topology: config.TopologySpec | str,
                   optimization_level: int | None = None,
                   layout_method: str | None = None,
                   seed: int | None = None) -> QuantumCircuit:
    """Transpile the unitary body of `spec` onto `topology` with fixed settings.

    Measurements are deliberately left out: gate counts and depth describe the
    arithmetic circuit, and read-out is counted separately by the image and
    verification layers. The returned circuit is routed and translated to
    ``config.TARGET_BASIS_GATES``; no further optimisation is applied by any
    caller, so all comparisons share this exact recipe.
    """
    topo = get_topology(topology) if isinstance(topology, str) else topology
    if spec.n_qubits > topo.n_qubits:
        raise CircuitTooWide(
            f"'{spec.name}' needs {spec.n_qubits} qubits but topology "
            f"'{topo.name}' provides {topo.n_qubits}")
    return transpile(
        spec.build(measure=False),
        coupling_map=coupling_map(topo),
        basis_gates=list(config.TARGET_BASIS_GATES),
        optimization_level=(config.OPTIMIZATION_LEVEL if optimization_level is None
                            else optimization_level),
        layout_method=config.LAYOUT_METHOD if layout_method is None else layout_method,
        seed_transpiler=config.GLOBAL_SEED if seed is None else seed,
    )


def basis_counts(circuit: QuantumCircuit) -> dict:
    """Count gates in the target basis, never mixing in measurement or barriers."""
    return {name: int(count) for name, count in circuit.count_ops().items()
            if name not in ("measure", "barrier")}


def target_quantum_cost(counts: dict) -> int:
    """NCV-L cost of a circuit already expressed in the target basis.

    Every basis gate is one elementary operation except `id`, which performs no
    operation and is free. Unknown names raise, so a change of target basis can
    never be priced with a stale model.
    """
    return sum(config.gate_quantum_cost(name) * count
               for name, count in counts.items())


def used_physical_qubits(circuit: QuantumCircuit) -> int:
    """Physical qubits touched by at least one gate (idle wiring is not a saving)."""
    touched = set()
    for instruction in circuit.data:
        for qubit in instruction.qubits:
            touched.add(circuit.find_bit(qubit).index)
    return len(touched)


def post_transpile_metrics(circuit: QuantumCircuit) -> dict:
    counts = basis_counts(circuit)
    known = {"cx", "x", "rz", "sx", "id"}
    return {
        "physical_qubits": circuit.num_qubits,
        "used_physical_qubits": used_physical_qubits(circuit),
        "cx_gates": counts.get("cx", 0),
        "x_gates": counts.get("x", 0),
        "rz_gates": counts.get("rz", 0),
        "sx_gates": counts.get("sx", 0),
        "id_gates": counts.get("id", 0),
        "other_gates": sum(count for name, count in counts.items()
                           if name not in known),
        "total_gates": sum(counts.values()),
        "depth": circuit.depth(),
        "quantum_cost": target_quantum_cost(counts),
    }

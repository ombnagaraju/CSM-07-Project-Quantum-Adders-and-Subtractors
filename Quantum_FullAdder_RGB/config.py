"""Central configuration for the Quantum Full Adder RGB project.

Every module imports its settings from here so that the whole comparison uses one
gate library, one metric implementation, one topology set and one RNG seed.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
CSV_DIR = os.path.join(RESULTS_DIR, "csv")
CHARTS_DIR = os.path.join(RESULTS_DIR, "charts")
CIRCUITS_DIR = os.path.join(RESULTS_DIR, "circuits")
PROCESSED_IMAGES_DIR = os.path.join(RESULTS_DIR, "processed_images")
REPORTS_DIR = os.path.join(RESULTS_DIR, "reports")
LOGS_DIR = os.path.join(RESULTS_DIR, "logs")
BENCHMARK_DIR = os.path.join(PROJECT_ROOT, "benchmark", "open_circuits")
SAMPLE_IMAGES_DIR = os.path.join(PROJECT_ROOT, "sample_images")

ALL_DIRS = [
    RESULTS_DIR,
    CSV_DIR,
    CHARTS_DIR,
    CIRCUITS_DIR,
    PROCESSED_IMAGES_DIR,
    REPORTS_DIR,
    LOGS_DIR,
    BENCHMARK_DIR,
]


def ensure_directories() -> None:
    """Create every output folder if it does not exist yet."""
    for path in ALL_DIRS:
        os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# Reproducibility (contribution 12)
# ---------------------------------------------------------------------------
GLOBAL_SEED = 20261106
SHOTS = 4096
SIMULATOR_METHOD = "automatic"
QISKIT_PIN = "qiskit==2.5.2"
AER_PIN = "qiskit-aer==0.17.2"


# ---------------------------------------------------------------------------
# Qubit ordering convention
# ---------------------------------------------------------------------------
# Qiskit prints bitstrings as q[n-1]...q[1]q[0]. We store the least significant
# bit at qubit index 0, so a printed string must be reversed to read an integer.
LSB_QUBIT_INDEX = 0


# ---------------------------------------------------------------------------
# Circuit sizing
# ---------------------------------------------------------------------------
FULL_ADDER_WIDTH = 1
RIPPLE_WIDTHS = [1, 2, 3, 4, 5, 6, 7, 8]
IMAGE_BIT_DEPTH = 4          # quantised pixel value, 0..15
PIXEL_SCALE = 17             # 4-bit value * 17 maps 0..15 -> 0..255
QUANTIZER_DIVISOR = 16       # floor(pixel / 16)


# ---------------------------------------------------------------------------
# Topologies (contribution 2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TopologySpec:
    name: str
    kind: str            # 'line', 'grid', 'heavy_hex', 'all_to_all'
    n_qubits: int
    grid_rows: int = 0
    grid_cols: int = 0
    heavy_hex_d: int = 0


TOPOLOGIES: tuple[TopologySpec, ...] = (
    TopologySpec("line_5", "line", 5),
    TopologySpec("line_12", "line", 12),
    TopologySpec("grid_3x4", "grid", 12, grid_rows=3, grid_cols=4),
    TopologySpec("grid_4x4", "grid", 16, grid_rows=4, grid_cols=4),
    TopologySpec("heavy_hex_3", "heavy_hex", 20, heavy_hex_d=3),
    TopologySpec("all_to_all", "all_to_all", 12),
)

# Standard-cell basis used for every post-transpilation metric, so all designs
# are measured in the same gate library (contribution 5).
TARGET_BASIS_GATES = ["cx", "id", "rz", "sx", "x"]
# Basis used when a design must keep its reversible block structure, i.e. for
# exhaustive verification and lookup-table generation. Blocks are decomposed to
# Toffoli/CNOT/X but never re-synthesised, so truth tables stay comparable.
LOGICAL_BASIS_GATES = ["ccx", "cx", "x", "id", "measure", "reset"]
OPTIMIZATION_LEVEL = 1
LAYOUT_METHOD = "dense"


# ---------------------------------------------------------------------------
# Hardware noise model (contributions 4 and 9)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BackendProfile:
    name: str
    cx_error: float
    u2_error: float      # single-qubit gate error
    readout_error: float
    t2_relaxation_us: float
    topology: str


BACKEND_PROFILES: tuple[BackendProfile, ...] = (
    BackendProfile("ibm_fake_linen", 0.0030, 0.0002, 0.0100, 80.0, "line_12"),
    BackendProfile("ibm_fake_gridm", 0.0075, 0.0005, 0.0200, 45.0, "grid_3x4"),
    BackendProfile("ibm_fake_heavyhex", 0.0045, 0.0003, 0.0150, 60.0, "heavy_hex_3"),
    BackendProfile("noisy_ideal_1e3", 0.0010, 0.0001, 0.0050, 100.0, "all_to_all"),
)

DEFAULT_BACKEND = BACKEND_PROFILES[0].name


def get_backend_profile(name: str) -> BackendProfile:
    for profile in BACKEND_PROFILES:
        if profile.name == name:
            return profile
    raise KeyError(f"Unknown backend profile '{name}'. Options: "
                   f"{[p.name for p in BACKEND_PROFILES]}")


# Decomposition choices for the adder carry chain (contribution 4).
DECOMPOSITION_STYLES = ("low_depth", "low_t_count")
# T-count of one Toffoli in each style, from standard magic-state constructions.
TOFFOLI_T_COUNT = {"low_depth": 7, "low_t_count": 4}
# Relative error weight of a non-Clifford T gate versus a Clifford two-qubit gate.
NON_CLIFFORD_PENALTY = 500.0
# Logical error rate target for the post-selected fault-tolerant estimate.
FT_TARGET_LOGICAL_ERROR = 1e-3


# ---------------------------------------------------------------------------
# Zero-noise extrapolation (contribution 9)
# ---------------------------------------------------------------------------
ZNE_SCALE_FACTORS = [1, 2, 3, 4]
ZNE_FOLD_METHOD = "global"
ZNE_EXTRAPOLATIONS = ("linear", "polynomial", "exponential")


# ---------------------------------------------------------------------------
# Energy model (contribution 11) - theoretical, simulation only
# ---------------------------------------------------------------------------
OPERATING_TEMPERATURE_K = 300.0
K_BOLTZMANN_J_PER_K = 1.380649e-23
LANDAUER_LIMIT_KT = K_BOLTZMANN_J_PER_K * OPERATING_TEMPERATURE_K * math.log(2)
# Switching energy of one reversible gate, expressed in units of kT ln 2.
# Adiabatic reversible logic experiments report 1e-3 - 1e-1 kT ln2 per switched bit.
REVERSIBLE_GATE_ENERGY_KT_LN2 = 1e-2
ENERGY_MODEL_NOTE = (
    "Landauer-bound numbers are analytic estimates from the measured bit-flip "
    "count. No hardware energy measurement was performed and none is claimed."
)


# ---------------------------------------------------------------------------
# NCV-L quantum cost model (phase 5 of the original spec)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GateCost:
    name: str
    cost: int
    decomposition: tuple[str, ...] = field(default=())


NCV_COSTS: dict[str, GateCost] = {
    "x": GateCost("x", 1),
    "cx": GateCost("cx", 1),
    "cv": GateCost("cv", 1),
    "cvdg": GateCost("cvdg", 1),
    "ccx": GateCost("ccx", 5, ("cv", "cv", "cx", "cvdg", "cx")),
    "peres": GateCost("peres", 4, ("ccx", "cx")),
    "rzz": GateCost("rzz", 4, ("cx", "rz", "cx")),
}
QUANTUM_COST_MODEL_NAME = "NCV-L"


def gate_quantum_cost(name: str) -> int:
    """Return the NCV-L cost of one composite gate name."""
    if name in NCV_COSTS:
        return NCV_COSTS[name].cost
    raise KeyError(f"No quantum cost defined for gate '{name}'. "
                   f"Known: {sorted(NCV_COSTS)}")


CSV_NAMES = {
    "fulladder_verification": "fulladder_verification.csv",
    "four_bit_verification": "four_bit_verification.csv",
    "ancilla_verification": "ancilla_verification.csv",
    "reversibility_verification": "reversibility_verification.csv",
    "control_savings": "control_qubit_savings.csv",
    "topology_metrics": "topology_metrics.csv",
    "scaling_vs_n": "scaling_vs_n.csv",
    "scaling_fit": "scaling_fit.csv",
    "decomposition_fidelity": "decomposition_fidelity.csv",
    "fault_tolerant_cost": "fault_tolerant_cost.csv",
    "garbage_uncompute": "garbage_uncompute.csv",
    "alu_slice_cost": "alu_slice_cost.csv",
    "zne_results": "zne_results.csv",
    "energy_estimate": "energy_estimate.csv",
    "benchmark_leaderboard": "benchmark_leaderboard.csv",
    "baseline_metrics": "baseline_metrics.csv",
    "optimized_metrics": "optimized_metrics.csv",
    "gate_comparison": "gate_comparison.csv",
    "quantum_cost_comparison": "quantum_cost_comparison.csv",
    "circuit_depth_comparison": "circuit_depth_comparison.csv",
    "image_metrics": "image_metrics.csv",
    "image_recovery": "image_recovery.csv",
    "quantum_lookup": "quantum_lookup_table.csv",
    "alu_verification": "alu_verification.csv",
    "zne_failure": "zne_failure_cases.csv",
    "reproducibility": "reproducibility_manifest.csv",
}


def csv_path(key: str) -> str:
    return os.path.join(CSV_DIR, CSV_NAMES[key])


# ---------------------------------------------------------------------------
# Result file helpers - one writer and one reader for the whole project, so the
# Streamlit pages and the tests all consume exactly the numbers the simulation
# produced (contribution 5 and 12).
# ---------------------------------------------------------------------------
def write_rows(rows: list[dict], key: str, fieldnames: list | None = None) -> str:
    """Write a list of dicts to results/csv/<key>, union-ordered columns."""
    import csv

    if not rows:
        raise ValueError(f"refusing to write empty CSV for '{key}'")
    if fieldnames is None:
        seen: list[str] = []
        for row in rows:
            for column in row:
                if column not in seen:
                    seen.append(column)
        fieldnames = seen
    path = csv_path(key)
    os.makedirs(CSV_DIR, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
    return path


def read_rows(key: str) -> list[dict]:
    """Read results/csv/<key> back as a list of dicts, or [] when missing."""
    import csv

    path = csv_path(key)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_report(text: str, filename: str) -> str:
    path = os.path.join(REPORTS_DIR, filename)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path

"""Fault-tolerant cost estimate: T-count, Toffoli depth and code size.

The estimate is deliberately coarse and every column is labelled as an estimate:

* Toffoli blocks are counted on the reversible op list (a Peres block contains
  exactly one Toffoli).
* ``t_count`` = Toffoli blocks x measured T-equivalent count of the chosen
  decomposition (``config.TOFFOLI_T_COUNT``, re-measured by
  :mod:`transpilation.decomposition_selector`).
* ``t_depth_estimate`` = Toffoli layers x per-Toffoli T-depth, i.e. it assumes
  the T layers of two Toffolis in the same Clifford layer do not overlap.
* The code distance is the smallest odd ``d`` with
  ``0.1 * (p / p_th)^((d+1)/2) <= target`` for the modelling assumption
  ``p = config.FT_PHYSICAL_ERROR``, ``p_th = config.FT_THRESHOLD_ERROR`` and
  ``target = config.FT_TARGET_LOGICAL_ERROR``.
* ``physical_qubits_estimate`` = logical qubits x 2 d^2 (rotated surface-code
  data qubits). Magic-state factories and routing qubits are not included.

No hardware result is claimed; the numbers are an architecture comparison.
"""

from __future__ import annotations

import config
from circuits import circuit_utils as cu

from performance.comparison import PAIRS

TOFFOLI_OPS = ("ccx", "peres", "peres_dg")


def toffoli_layout(spec: cu.CircuitSpec) -> tuple[int, int]:
    """(Toffoli blocks, number of time layers that contain at least one block)."""
    layers = [0] * spec.n_qubits
    count = 0
    last_toffoli_layer = -1
    for op in spec.all_ops():
        qubits = op[1:]
        start = max(layers[q] for q in qubits)
        if op[0] in TOFFOLI_OPS:
            count += 1
            last_toffoli_layer = max(last_toffoli_layer, start)
        for qubit in qubits:
            layers[qubit] = start + 1
    return count, last_toffoli_layer + 1


def code_distance(physical_error: float = None, target: float = None) -> int:
    physical_error = config.FT_PHYSICAL_ERROR if physical_error is None else physical_error
    target = config.FT_TARGET_LOGICAL_ERROR if target is None else target
    ratio = physical_error / config.FT_THRESHOLD_ERROR
    for distance in range(3, 41, 2):
        estimate = config.FT_ERROR_PREFACTOR * ratio ** ((distance + 1) / 2)
        if estimate <= target * (1.0 + 1e-9):
            return distance
    raise ValueError(
        f"no distance up to 39 reaches {target:g} at p={physical_error:g}; "
        "the modelling assumption is below the code threshold")


def cost_rows(pairs=PAIRS, styles=None) -> list[dict]:
    styles = list(styles or config.DECOMPOSITION_STYLES)
    distance = code_distance()
    rows: list[dict] = []
    for pair in pairs:
        for role in ("baseline", "optimized"):
            spec = pair[role]
            toffoli_blocks, toffoli_depth = toffoli_layout(spec)
            for style in styles:
                t_count = toffoli_blocks * config.TOFFOLI_T_COUNT[style]
                rows.append({
                    "pair": pair["family"],
                    "role": role,
                    "circuit": spec.name,
                    "style": style,
                    "logical_qubits": spec.n_qubits,
                    "toffoli_blocks": toffoli_blocks,
                    "toffoli_depth": toffoli_depth,
                    "t_per_toffoli": config.TOFFOLI_T_COUNT[style],
                    "t_count": t_count,
                    "t_depth_estimate": toffoli_depth * config.TOFFOLI_T_DEPTH[style],
                    "clifford_blocks": cu.logical_counts(spec)["total_gates"] - toffoli_blocks,
                    "code_distance": distance,
                    "physical_qubits_estimate": spec.n_qubits * 2 * distance ** 2,
                    "magic_states": t_count,
                    "estimate_note": (f"p={config.FT_PHYSICAL_ERROR:g}, "
                                      f"p_th={config.FT_THRESHOLD_ERROR:g}, "
                                      f"target={config.FT_TARGET_LOGICAL_ERROR:g}; "
                                      "surface-code data qubits only"),
                })
    return rows


def verify(write: bool = True) -> list[dict]:
    rows = cost_rows()
    for row in rows:
        if row["code_distance"] < 3:
            raise AssertionError("surface-code distance fell below 3")
        if row["t_count"] != row["toffoli_blocks"] * config.TOFFOLI_T_COUNT[row["style"]]:
            raise AssertionError("T-count does not match the measured decomposition")
    by_key = {(row["pair"], row["role"], row["style"]): row for row in rows}
    for pair in PAIRS:
        for style in config.DECOMPOSITION_STYLES:
            base = by_key[(pair["family"], "baseline", style)]
            opt = by_key[(pair["family"], "optimized", style)]
            if opt["physical_qubits_estimate"] > base["physical_qubits_estimate"]:
                raise AssertionError(
                    f"{pair['family']}/{style}: optimised design needs more "
                    "physical qubits in the estimate")
    if write:
        config.write_rows(rows, "fault_tolerant_cost")
    return rows


def summary(rows: list[dict]) -> str:
    lines = []
    for row in rows:
        if row["style"] != config.DECOMPOSITION_STYLES[0]:
            continue
        lines.append(
            f"{row['pair']:14s} {row['role']:9s} blocks={row['toffoli_blocks']:2d} "
            f"T={row['t_count']:3d} T-depth~{row['t_depth_estimate']:3d} "
            f"d={row['code_distance']} physical~{row['physical_qubits_estimate']:5d}")
    return "\n".join(lines)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    print(f"\nwrote {len(result)} rows to {config.csv_path('fault_tolerant_cost')}")

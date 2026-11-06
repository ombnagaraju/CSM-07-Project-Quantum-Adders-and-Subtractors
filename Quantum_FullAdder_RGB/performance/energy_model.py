"""Analytic energy figures under an explicitly stated Landauer model.

Two numbers are reported per design and neither is a measurement:

``landauer_bound_joules``
    ``kT ln 2`` times the number of irreversible bit erasures performed by the
    circuit (mid-circuit measurements that are consumed, conditional flips and
    resets). A fully unitary reversible design erases nothing and therefore has
    a zero Landauer bound; that is the point of reversible logic.

``estimated_switching_joules``
    ``total_gates x REVERSIBLE_GATE_ENERGY_KT_LN2 x kT ln 2``. This is the
    adiabatic-switching estimate declared in config, not a hardware number.

The note from config is copied into every row so the CSV cannot be read without
its assumptions.
"""

from __future__ import annotations

import config
from circuits import circuit_utils as cu, peres_fulladder
from performance.comparison import PAIRS


def estimate(spec: cu.CircuitSpec, family: str, role: str) -> dict:
    counts = cu.logical_counts(spec)
    erasures = counts["measure"] + counts["cond_x"] + counts["reset"]
    return {
        "circuit": spec.name,
        "family": family,
        "role": role,
        "total_gates": counts["total_gates"],
        "measure_ops": counts["measure"],
        "cond_x_ops": counts["cond_x"],
        "reset_ops": counts["reset"],
        "irreversible_erasures": erasures,
        "landauer_bound_joules": erasures * config.LANDAUER_LIMIT_KT,
        "estimated_switching_joules": (counts["total_gates"]
                                       * config.REVERSIBLE_GATE_ENERGY_KT_LN2
                                       * config.LANDAUER_LIMIT_KT),
        "model_note": config.ENERGY_MODEL_NOTE,
    }


def rows(pairs=PAIRS) -> list[dict]:
    out: list[dict] = []
    for pair in pairs:
        out.append(estimate(pair["baseline"], pair["family"], "baseline"))
        out.append(estimate(pair["optimized"], pair["family"], "optimized"))
    # The Peres adder is the reversible reference that trades qubits and
    # garbage for gates, so its zero-erasure figure belongs in the table too.
    out.append(estimate(peres_fulladder.build_peres_fulladder(),
                        "fulladder", "reference"))
    return out


def verify(write: bool = True) -> list[dict]:
    result = rows()
    for row in result:
        if row["irreversible_erasures"] != 0:
            raise AssertionError(
                f"{row['circuit']} is not fully reversible but is priced here")
        if row["landauer_bound_joules"] != 0.0:
            raise AssertionError("a zero-erasure circuit must have a zero bound")
    if write:
        config.write_rows(result, "energy_estimate")
    return result


def summary(result: list[dict]) -> str:
    return "\n".join(
        f"{row['circuit']:34s} gates={row['total_gates']:3d} "
        f"erasures={row['irreversible_erasures']} "
        f"switching~{row['estimated_switching_joules']:.3e} J"
        for row in result)


if __name__ == "__main__":
    config.ensure_directories()
    data = verify()
    print(summary(data))
    print(f"\nwrote {len(data)} rows to {config.csv_path('energy_estimate')}")

"""Measured scaling law for gate count, cost and depth versus bit-width.

For every width in ``config.RIPPLE_WIDTHS`` both styles are built in plain
addition mode, measured logically, and transpiled onto a line of exactly the
design's width with the shared settings. A line is used because it is the
standard nearest-neighbour cost model and because it is the only topology that
can be sized per width without changing the comparison.

Each metric is fitted with an ordinary least-squares line ``y = slope*n +
intercept``. The fit reports R^2, the standard error of the slope and its 95%
confidence interval (Student t, n-2 degrees of freedom); with eight widths the
interval is narrow and the exact-linear metrics reach R^2 = 1.
"""

from __future__ import annotations

import math

import numpy as np

import config
from circuits.parametrized_nbit_adder import build_nbit_design
from performance import gate_analysis
from transpilation import topologies

STYLES = ("baseline", "optimized")
FIT_METRICS = ("qubits", "total_gates", "quantum_cost", "logical_depth",
               "transpiled_cx_gates", "transpiled_total_gates", "transpiled_depth")


def measure_width(width: int, style: str) -> dict:
    spec = build_nbit_design(width, style, "add")
    row = gate_analysis.design_row(spec, f"scaling_{style}", style)
    topology = config.TopologySpec(f"line_{spec.n_qubits}", "line", spec.n_qubits)
    metrics = topologies.post_transpile_metrics(
        topologies.transpile_spec(spec, topology))
    row.update({
        "width": width,
        "style": style,
        "transpiled_topology": topology.name,
        "transpiled_cx_gates": metrics["cx_gates"],
        "transpiled_total_gates": metrics["total_gates"],
        "transpiled_depth": metrics["depth"],
        "transpiled_quantum_cost": metrics["quantum_cost"],
    })
    return row


def measure(widths=None, styles=STYLES) -> list[dict]:
    return [measure_width(width, style)
            for style in styles for width in (widths or config.RIPPLE_WIDTHS)]


def linear_fit(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        raise ValueError("a line needs at least two widths")
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 1.0
    dof = len(x) - 2
    sxx = float(np.sum((x - x.mean()) ** 2))
    stderr = math.sqrt(ss_res / dof / sxx) if dof > 0 and sxx > 0 else 0.0
    if dof > 0:
        from scipy.stats import t as student_t

        margin = float(student_t.ppf(0.975, dof)) * stderr
    else:
        margin = 0.0
    return {
        "slope": round(float(slope), 6),
        "intercept": round(float(intercept), 6),
        "r_squared": round(float(r2), 6),
        "slope_stderr": round(stderr, 6),
        "slope_ci_low": round(float(slope) - margin, 6),
        "slope_ci_high": round(float(slope) + margin, 6),
        "n_points": len(x),
    }


def fit_rows(rows: list[dict]) -> list[dict]:
    fits: list[dict] = []
    for style in STYLES:
        subset = sorted((row for row in rows if row["style"] == style),
                        key=lambda row: row["width"])
        x = [row["width"] for row in subset]
        for metric in FIT_METRICS:
            fits.append({"style": style, "metric": metric,
                         **linear_fit(x, [row[metric] for row in subset])})
    return fits


def verify(write: bool = True, widths=None) -> tuple[list[dict], list[dict]]:
    rows = measure(widths)
    fits = fit_rows(rows)
    by_key = {(fit["style"], fit["metric"]): fit for fit in fits}
    for style in STYLES:
        for metric in ("qubits", "total_gates", "quantum_cost"):
            if by_key[(style, metric)]["r_squared"] < 0.999:
                raise AssertionError(
                    f"{style}/{metric} is not linear in the bit-width: "
                    f"R^2={by_key[(style, metric)]['r_squared']}")
    if by_key[("optimized", "total_gates")]["slope"] >= by_key[("baseline", "total_gates")]["slope"]:
        raise AssertionError("optimised gate-count slope is not lower than baseline")
    if by_key[("optimized", "quantum_cost")]["slope"] >= by_key[("baseline", "quantum_cost")]["slope"]:
        raise AssertionError("optimised cost slope is not lower than baseline")
    if write:
        config.write_rows(rows, "scaling_vs_n")
        config.write_rows(fits, "scaling_fit")
    return rows, fits


def summary(fits: list[dict]) -> str:
    lines = []
    for fit in fits:
        lines.append(f"{fit['style']:9s} {fit['metric']:24s} "
                     f"{fit['slope']:8.3f}*n + {fit['intercept']:8.3f} "
                     f"[{fit['slope_ci_low']:.3f}, {fit['slope_ci_high']:.3f}] "
                     f"R^2={fit['r_squared']:.4f}")
    return "\n".join(lines)


if __name__ == "__main__":
    config.ensure_directories()
    measured, fitted = verify()
    print(summary(fitted))
    print(f"\nwrote {len(measured)} rows to {config.csv_path('scaling_vs_n')} "
          f"and {len(fitted)} fits to {config.csv_path('scaling_fit')}")

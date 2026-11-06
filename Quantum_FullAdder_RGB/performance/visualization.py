"""Matplotlib charts for the resource comparison, all read from the CSVs.

No number is hardcoded here: every chart loads ``results/csv/*.csv`` through
:func:`config.read_rows`, so a chart can only show what the simulation wrote.
Charts whose source CSV has not been generated yet are skipped.
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402

BASELINE_COLOUR = "#4c72b0"
OPTIMIZED_COLOUR = "#dd8452"
ACCENT = "#55a868"


def _save(fig, name: str) -> str:
    os.makedirs(config.CHARTS_DIR, exist_ok=True)
    path = os.path.join(config.CHARTS_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _metric_rows(rows: list[dict], metric: str) -> list[dict]:
    return [row for row in rows if row["metric"] == metric]


def _pair_chart(rows: list[dict], metric: str, ylabel: str, title: str,
                name: str) -> str | None:
    data = _metric_rows(rows, metric)
    if not data:
        return None
    pairs = [row["pair"] for row in data]
    x = np.arange(len(pairs))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(x - width / 2, [float(row["baseline"]) for row in data], width,
           label="baseline", color=BASELINE_COLOUR)
    ax.bar(x + width / 2, [float(row["optimized"]) for row in data], width,
           label="optimized", color=OPTIMIZED_COLOUR)
    for index, row in enumerate(data):
        ax.text(index, max(float(row["baseline"]), float(row["optimized"])) * 1.01,
                f"{float(row['reduction_percent']):.1f}% lower",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, pairs)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    return _save(fig, name)


def render_comparison_charts() -> list[str]:
    gates = config.read_rows("gate_comparison")
    costs = config.read_rows("quantum_cost_comparison")
    depths = config.read_rows("circuit_depth_comparison")
    baseline = config.read_rows("baseline_metrics")
    optimized = config.read_rows("optimized_metrics")
    written: list[str] = []

    chart = _pair_chart(gates, "total_gates", "logical gate blocks",
                        "Total gate count: baseline vs optimized",
                        "gate_count_comparison.png")
    if chart:
        written.append(chart)
    chart = _pair_chart(gates, "decomposed_gates", "Clifford+T gates",
                        "Decomposed gate count", "decomposed_gate_comparison.png")
    if chart:
        written.append(chart)

    if costs:
        x = np.arange(len(costs))
        width = 0.36
        fig, ax = plt.subplots(figsize=(7.5, 4.2))
        ax.bar(x - width / 2, [float(row["baseline_cost"]) for row in costs], width,
               label="baseline", color=BASELINE_COLOUR)
        ax.bar(x + width / 2, [float(row["optimized_cost"]) for row in costs], width,
               label="optimized", color=OPTIMIZED_COLOUR)
        for index, row in enumerate(costs):
            ax.text(index, float(row["baseline_cost"]) * 1.01,
                    f"-{float(row['reduction_percent']):.1f}%",
                    ha="center", va="bottom", fontsize=8)
        ax.set_xticks(x, [row["pair"] for row in costs])
        ax.set_ylabel(f"quantum cost ({costs[0]['model']})")
        ax.set_title("Quantum cost: baseline vs optimized")
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
        written.append(_save(fig, "quantum_cost_comparison.png"))

    if depths:
        pairs = sorted({row["pair"] for row in depths})
        kinds = sorted({row["depth_kind"] for row in depths})
        x = np.arange(len(pairs))
        width = 0.8 / max(1, 2 * len(kinds))
        fig, ax = plt.subplots(figsize=(9.0, 4.6))
        for index, kind in enumerate(kinds):
            base = [float(row["baseline_depth"]) for row in depths
                    if row["pair"] in pairs and row["depth_kind"] == kind]
            opt = [float(row["optimized_depth"]) for row in depths
                   if row["pair"] in pairs and row["depth_kind"] == kind]
            offset = (index - (len(kinds) - 1) / 2) * 2 * width
            ax.bar(x + offset - width / 2, base, width,
                   label=f"baseline / {kind}", color=BASELINE_COLOUR,
                   alpha=1.0 - 0.18 * index)
            ax.bar(x + offset + width / 2, opt, width,
                   label=f"optimized / {kind}", color=OPTIMIZED_COLOUR,
                   alpha=1.0 - 0.18 * index)
        ax.set_xticks(x, pairs)
        ax.set_ylabel("depth")
        ax.set_title("Depth at logical, decomposed and transpiled level")
        ax.legend(fontsize=7, ncols=2)
        ax.grid(axis="y", alpha=0.25)
        written.append(_save(fig, "circuit_depth_comparison.png"))

    if baseline and optimized:
        labels = [row["circuit"] for row in baseline] + [row["circuit"] for row in optimized]
        inputs = ([int(row["input_qubits"]) for row in baseline]
                  + [int(row["input_qubits"]) for row in optimized])
        ancillas = ([int(row["ancilla_qubits"]) for row in baseline]
                    + [int(row["ancilla_qubits"]) for row in optimized])
        garbage = ([int(row["garbage_qubits"]) for row in baseline]
                   + [int(row["garbage_qubits"]) for row in optimized])
        x = np.arange(len(labels))
        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        ax.bar(x, inputs, 0.55, label="input qubits", color=BASELINE_COLOUR)
        ax.bar(x, ancillas, 0.55, bottom=inputs, label="ancilla qubits", color=ACCENT)
        ax.bar(x, garbage, 0.55, bottom=np.array(inputs) + np.array(ancillas),
               label="garbage lines", color="#c44e52")
        ax.set_xticks(x, labels, rotation=15, ha="right")
        ax.set_ylabel("qubits")
        ax.set_title("Qubit usage and garbage")
        ax.legend()
        ax.grid(axis="y", alpha=0.25)
        written.append(_save(fig, "qubit_usage.png"))

        fig, ax = plt.subplots(figsize=(8.5, 4.4))
        x_base = np.arange(len(baseline))
        x_opt = np.arange(len(baseline), len(baseline) + len(optimized))
        for metric, hatch in (("x_gates", "//"), ("cx_gates", "")):
            ax.bar(x_base, [int(row[metric]) for row in baseline], 0.4,
                   color=BASELINE_COLOUR, hatch=hatch, alpha=0.85,
                   label=f"baseline {metric}")
            ax.bar(x_opt, [int(row[metric]) for row in optimized], 0.4,
                   color=OPTIMIZED_COLOUR, hatch=hatch, alpha=0.85,
                   label=f"optimized {metric}")
        ax.set_xticks(x, labels, rotation=15, ha="right")
        ax.set_ylabel("logical gates")
        ax.set_title("Gate mix (X and CNOT; Toffoli blocks are in the total-gate chart)")
        ax.legend(fontsize=7)
        ax.grid(axis="y", alpha=0.25)
        written.append(_save(fig, "gate_breakdown.png"))

    if gates:
        metrics = ("qubits", "total_gates", "decomposed_gates")
        pairs = sorted({row["pair"] for row in gates})
        data = {(row["pair"], row["metric"]): row for row in gates}
        y = np.arange(len(pairs))
        height = 0.24
        fig, ax = plt.subplots(figsize=(7.8, 4.2))
        for index, metric in enumerate(metrics):
            values = [float(data[(pair, metric)]["reduction_percent"]) for pair in pairs
                      if (pair, metric) in data]
            ax.barh(y + (index - 1) * height, values, height, label=metric)
        ax.set_yticks(y, pairs)
        ax.set_xlabel("reduction (%)  =  (baseline - optimized) / baseline x 100")
        ax.set_title("Percentage improvement of the optimized design")
        ax.legend()
        ax.grid(axis="x", alpha=0.25)
        written.append(_save(fig, "reduction_summary.png"))
    return written


def render_topology_charts() -> list[str]:
    rows = config.read_rows("topology_metrics")
    if not rows:
        return []
    written: list[str] = []
    families = sorted({row["family"] for row in rows})
    for family in families:
        subset = [row for row in rows if row["family"] == family]
        circuits = sorted({row["circuit"] for row in subset})
        topologies = sorted({row["topology"] for row in subset})
        if len(circuits) < 2:
            continue
        x = np.arange(len(topologies))
        width = 0.8 / len(circuits)
        fig, ax = plt.subplots(figsize=(9.0, 4.4))
        for index, circuit in enumerate(circuits):
            by_topology = {row["topology"]: row for row in subset
                           if row["circuit"] == circuit}
            values = [int(by_topology[topo]["cx_gates"]) if topo in by_topology else 0
                      for topo in topologies]
            ax.bar(x + (index - (len(circuits) - 1) / 2) * width, values, width,
                   label=circuit)
        ax.set_xticks(x, topologies, rotation=15, ha="right")
        ax.set_ylabel("CNOT gates after transpilation")
        ax.set_title(f"Routing cost by topology: {family}")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.25)
        written.append(_save(fig, f"topology_cx_{family}.png"))
    return written


def render_scaling_charts() -> list[str]:
    rows = config.read_rows("scaling_vs_n")
    fits = config.read_rows("scaling_fit")
    if not rows:
        return []
    written: list[str] = []
    fit_by = {(row["style"], row["metric"]): row for row in fits}
    for metric, ylabel, name in (("total_gates", "logical gate blocks",
                                  "scaling_gates.png"),
                                 ("quantum_cost", "NCV-L quantum cost",
                                  "scaling_cost.png"),
                                 ("transpiled_depth", "transpiled depth",
                                  "scaling_transpiled_depth.png")):
        fig, ax = plt.subplots(figsize=(7.5, 4.3))
        for style, colour in (("baseline", BASELINE_COLOUR),
                              ("optimized", OPTIMIZED_COLOUR)):
            points = sorted((row for row in rows if row["style"] == style),
                            key=lambda row: int(row["width"]))
            x = [int(row["width"]) for row in points]
            y = [float(row[metric]) for row in points]
            ax.plot(x, y, "o", color=colour, label=f"{style} measured")
            fit = fit_by.get((style, metric))
            if fit:
                grid = np.linspace(min(x), max(x), 50)
                ax.plot(grid, float(fit["slope"]) * grid + float(fit["intercept"]),
                        "-", color=colour, alpha=0.7,
                        label=(f"{style} fit: {float(fit['slope']):.2f}n + "
                               f"{float(fit['intercept']):.2f}, "
                               f"R²={float(fit['r_squared']):.4f}"))
        ax.set_xlabel("bit width n")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Scaling law: {metric}")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
        written.append(_save(fig, name))
    return written


def render_decomposition_chart() -> list[str]:
    rows = config.read_rows("decomposition_fidelity")
    if not rows:
        return []
    backends = sorted({row["backend"] for row in rows})
    styles = sorted({row["style"] for row in rows})
    x = np.arange(len(backends))
    width = 0.8 / len(styles)
    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    for index, style in enumerate(styles):
        by_backend = {row["backend"]: row for row in rows if row["style"] == style}
        values = [float(by_backend[backend]["modelled_error_probability"])
                  for backend in backends]
        ax.bar(x + (index - (len(styles) - 1) / 2) * width, values, width, label=style)
        for position, value in zip(x, values):
            ax.text(position + (index - (len(styles) - 1) / 2) * width, value,
                    f"{value:.4f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x, backends, rotation=10)
    ax.set_ylabel("modelled error probability (1 - product of gate success)")
    ax.set_title("Toffoli decomposition choice from backend error rates")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    return [_save(fig, "decomposition_choice.png")]


def render_all() -> list[str]:
    written = render_comparison_charts()
    written += render_topology_charts()
    written += render_scaling_charts()
    written += render_decomposition_chart()
    return written


if __name__ == "__main__":
    config.ensure_directories()
    paths = render_all()
    print("\n".join(paths))

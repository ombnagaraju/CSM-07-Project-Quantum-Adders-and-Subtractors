"""
Visualization and Chart Generation Module
=========================================

Renders publication-quality comparative performance figures and circuit diagrams:
  1. Gate Count Comparison (Bar Chart)
  2. Quantum Cost Comparison (Bar Chart)
  3. Circuit Depth Comparison (Bar Chart)
  4. Comprehensive Resource Summary (Multi-panel figure)
  5. Quantum Circuit Diagrams (Saved in results/circuits/)
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import numpy as np

from config import (
    CHARTS_DIR,
    CIRCUITS_RESULTS_DIR,
    CHART_GATE_COMPARISON,
    CHART_QUANTUM_COST,
    CHART_CIRCUIT_DEPTH,
    CHART_RESOURCE_SUMMARY
)
from circuits.circuit_utils import export_circuit_diagram
from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit


def setup_matplotlib_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelweight": "semibold",
        "axes.grid": True,
        "grid.alpha": 0.4,
        "grid.linestyle": "--",
        "figure.autolayout": True
    })


def generate_gate_comparison_chart() -> Path:
    """Generate bar chart comparing gate counts."""
    setup_matplotlib_style()
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    categories = ["1-Bit Full Adder", "4-Bit Adder-Subtractor"]
    baseline_gates = [6, 50]
    optimized_gates = [5, 40]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax.bar(x - width/2, baseline_gates, width, label="Baseline Architecture", color="#4A90E2", edgecolor="#2B5B94")
    rects2 = ax.bar(x + width/2, optimized_gates, width, label="Optimized Architecture", color="#50E3C2", edgecolor="#2E9E82")

    ax.set_ylabel("Total Gate Count")
    ax.set_title("Reversible Gate Count Comparison (Baseline vs Optimized)")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(frameon=True)

    # Bar value labels
    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h}", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{h} (-{round((rects1[list(rects2).index(rect)].get_height()-h)/rects1[list(rects2).index(rect)].get_height()*100, 1)}%)",
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(CHART_GATE_COMPARISON))
    plt.close(fig)
    return CHART_GATE_COMPARISON


def generate_quantum_cost_chart() -> Path:
    """Generate bar chart comparing quantum costs."""
    setup_matplotlib_style()
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    categories = ["1-Bit Full Adder", "4-Bit Adder-Subtractor"]
    baseline_costs = [14, 106]
    optimized_costs = [13, 96]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax.bar(x - width/2, baseline_costs, width, label="Baseline Cost (NCV)", color="#E94A48", edgecolor="#9B2321")
    rects2 = ax.bar(x + width/2, optimized_costs, width, label="Optimized Cost (NCV)", color="#F5A623", edgecolor="#AB6F11")

    ax.set_ylabel("Quantum Cost (NCV Model)")
    ax.set_title("Quantum Cost Comparison (Baseline vs Optimized)")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(frameon=True)

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h}", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    for rect in rects2:
        h = rect.get_height()
        base_h = rects1[list(rects2).index(rect)].get_height()
        ax.annotate(f"{h} (-{round((base_h-h)/base_h*100, 1)}%)",
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

    fig.savefig(str(CHART_QUANTUM_COST))
    plt.close(fig)
    return CHART_QUANTUM_COST


def generate_circuit_depth_chart() -> Path:
    """Generate bar chart comparing circuit depth."""
    setup_matplotlib_style()
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    categories = ["1-Bit Full Adder", "4-Bit Adder-Subtractor"]
    baseline_depth = [build_baseline_fulladder().depth(), build_baseline_4bit_adder_circuit().depth()]
    optimized_depth = [build_optimized_fulladder(restore_b=True).depth(), build_optimized_4bit_adder_circuit().depth()]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax.bar(x - width/2, baseline_depth, width, label="Baseline Critical Depth", color="#9013FE", edgecolor="#5906A3")
    rects2 = ax.bar(x + width/2, optimized_depth, width, label="Optimized Critical Depth", color="#BD10E0", edgecolor="#76078E")

    ax.set_ylabel("Circuit Critical Path Depth")
    ax.set_title("Circuit Execution Depth Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(frameon=True)

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h}", xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")
    for rect in rects2:
        h = rect.get_height()
        base_h = rects1[list(rects2).index(rect)].get_height()
        reduc = round((base_h-h)/base_h*100, 1) if base_h > 0 else 0
        ax.annotate(f"{h} ({'-' if reduc > 0 else ''}{reduc}%)",
                    xy=(rect.get_x() + rect.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold")

    fig.savefig(str(CHART_CIRCUIT_DEPTH))
    plt.close(fig)
    return CHART_CIRCUIT_DEPTH


def generate_resource_summary_chart() -> Path:
    """Generate a comprehensive multi-panel summary figure."""
    setup_matplotlib_style()
    fig, axs = plt.subplots(1, 3, figsize=(15, 5), dpi=300)

    # 1. Total Gates
    categories = ["1-Bit Adder", "4-Bit Subtractor"]
    axs[0].bar(np.arange(2) - 0.175, [6, 50], 0.35, label="Baseline", color="#4A90E2")
    axs[0].bar(np.arange(2) + 0.175, [5, 40], 0.35, label="Optimized", color="#50E3C2")
    axs[0].set_title("Total Gates")
    axs[0].set_xticks(np.arange(2))
    axs[0].set_xticklabels(categories)
    axs[0].legend()

    # 2. Quantum Cost
    axs[1].bar(np.arange(2) - 0.175, [14, 106], 0.35, label="Baseline", color="#E94A48")
    axs[1].bar(np.arange(2) + 0.175, [13, 96], 0.35, label="Optimized", color="#F5A623")
    axs[1].set_title("Quantum Cost (NCV)")
    axs[1].set_xticks(np.arange(2))
    axs[1].set_xticklabels(categories)
    axs[1].legend()

    # 3. Circuit Depth
    b_depth = [build_baseline_fulladder().depth(), build_baseline_4bit_adder_circuit().depth()]
    o_depth = [build_optimized_fulladder(restore_b=True).depth(), build_optimized_4bit_adder_circuit().depth()]
    axs[2].bar(np.arange(2) - 0.175, b_depth, 0.35, label="Baseline", color="#9013FE")
    axs[2].bar(np.arange(2) + 0.175, o_depth, 0.35, label="Optimized", color="#BD10E0")
    axs[2].set_title("Circuit Depth")
    axs[2].set_xticks(np.arange(2))
    axs[2].set_xticklabels(categories)
    axs[2].legend()

    fig.suptitle("Quantum Full Adder Optimization Benchmark Summary", fontsize=15, fontweight="bold")
    fig.savefig(str(CHART_RESOURCE_SUMMARY))
    plt.close(fig)
    return CHART_RESOURCE_SUMMARY


def generate_all_circuit_diagrams():
    """Export all circuit diagrams to results/circuits/."""
    CIRCUITS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    circuits = [
        ("baseline_fulladder.png", build_baseline_fulladder()),
        ("peres_fulladder.png", build_peres_fulladder()),
        ("optimized_fulladder.png", build_optimized_fulladder(restore_b=True)),
        ("baseline_4bit_adder.png", build_baseline_4bit_adder_circuit()),
        ("optimized_4bit_adder.png", build_optimized_4bit_adder_circuit()),
    ]
    for filename, qc in circuits:
        p = CIRCUITS_RESULTS_DIR / filename
        export_circuit_diagram(qc, p)
        print(f"  Exported: {p}")


def generate_all_visualizations():
    """Trigger all chart and diagram generation."""
    print("[Visualization] Generating comparative analysis charts...")
    g_path = generate_gate_comparison_chart()
    q_path = generate_quantum_cost_chart()
    d_path = generate_circuit_depth_chart()
    s_path = generate_resource_summary_chart()
    print(f"  Saved: {g_path}")
    print(f"  Saved: {q_path}")
    print(f"  Saved: {d_path}")
    print(f"  Saved: {s_path}")

    print("[Visualization] Exporting quantum circuit schematics...")
    generate_all_circuit_diagrams()


if __name__ == "__main__":
    generate_all_visualizations()

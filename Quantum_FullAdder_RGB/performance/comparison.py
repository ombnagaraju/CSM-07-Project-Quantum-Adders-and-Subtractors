"""
Architecture Performance Comparison Module
===========================================

Computes relative percentage improvements between Baseline and Optimized
architectures across:
  - Total Qubits
  - Ancilla Qubits
  - Garbage Outputs
  - Total Gate Count
  - CNOT Count
  - Quantum Cost (NCV model)
  - Circuit Depth

Reduction Formula:
  Reduction (%) = ((Baseline - Optimized) / Baseline) * 100

Generates:
  results/csv/baseline_metrics.csv
  results/csv/optimized_metrics.csv
  results/csv/gate_comparison.csv
"""

import sys
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import (
    CSV_BASELINE_METRICS,
    CSV_OPTIMIZED_METRICS,
    CSV_GATE_COMPARISON
)
from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit
from circuits.circuit_utils import get_circuit_resources


def generate_comparison_metrics() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate baseline metrics, optimized metrics, and differential comparison tables.
    """
    # 1. 1-Bit Circuits
    fa_base = build_baseline_fulladder()
    fa_peres = build_peres_fulladder()
    fa_opt = build_optimized_fulladder(restore_b=True)

    # 2. 4-Bit Circuits
    four_base = build_baseline_4bit_adder_circuit()
    four_opt = build_optimized_4bit_adder_circuit()

    # Extract metrics
    m_fa_base = get_circuit_resources(fa_base)
    m_fa_peres = get_circuit_resources(fa_peres)
    m_fa_opt = get_circuit_resources(fa_opt)

    m_4_base = get_circuit_resources(four_base)
    m_4_opt = get_circuit_resources(four_opt)

    # Baseline Table
    base_rows = [
        {
            "Circuit": "1-Bit Full Adder",
            "Architecture": "Baseline (Toffoli-CNOT)",
            "Total_Qubits": fa_base.num_qubits,
            "Input_Qubits": 3,
            "Output_Qubits": 2,
            "Ancilla_Qubits": 2,
            "Garbage_Outputs": 0,
            "CNOT_Count": m_fa_base["cnot_count"],
            "Toffoli_Count": m_fa_base["toffoli_count"],
            "Total_Gates": m_fa_base["total_gates"],
            "Circuit_Depth": m_fa_base["circuit_depth"],
            "Quantum_Cost": m_fa_base["quantum_cost"]
        },
        {
            "Circuit": "4-Bit Adder-Subtractor",
            "Architecture": "Baseline (Ripple-Carry)",
            "Total_Qubits": four_base.num_qubits,
            "Input_Qubits": 9,
            "Output_Qubits": 5,
            "Ancilla_Qubits": 4,
            "Garbage_Outputs": 0,
            "CNOT_Count": m_4_base["cnot_count"],
            "Toffoli_Count": m_4_base["toffoli_count"],
            "Total_Gates": m_4_base["total_gates"],
            "Circuit_Depth": m_4_base["circuit_depth"],
            "Quantum_Cost": m_4_base["quantum_cost"]
        }
    ]
    df_base = pd.DataFrame(base_rows)
    CSV_BASELINE_METRICS.parent.mkdir(parents=True, exist_ok=True)
    df_base.to_csv(CSV_BASELINE_METRICS, index=False)

    # Optimized Table
    opt_rows = [
        {
            "Circuit": "1-Bit Full Adder",
            "Architecture": "Optimized (Restored Peres)",
            "Total_Qubits": fa_opt.num_qubits,
            "Input_Qubits": 3,
            "Output_Qubits": 2,
            "Ancilla_Qubits": 1,
            "Garbage_Outputs": 0,
            "CNOT_Count": m_fa_opt["cnot_count"],
            "Toffoli_Count": m_fa_opt["toffoli_count"],
            "Total_Gates": m_fa_opt["total_gates"],
            "Circuit_Depth": m_fa_opt["circuit_depth"],
            "Quantum_Cost": m_fa_opt["quantum_cost"]
        },
        {
            "Circuit": "4-Bit Adder-Subtractor",
            "Architecture": "Optimized (Peres Carry-Pipeline)",
            "Total_Qubits": four_opt.num_qubits,
            "Input_Qubits": 9,
            "Output_Qubits": 5,
            "Ancilla_Qubits": 4,
            "Garbage_Outputs": 0,
            "CNOT_Count": m_4_opt["cnot_count"],
            "Toffoli_Count": m_4_opt["toffoli_count"],
            "Total_Gates": m_4_opt["total_gates"],
            "Circuit_Depth": m_4_opt["circuit_depth"],
            "Quantum_Cost": m_4_opt["quantum_cost"]
        }
    ]
    df_opt = pd.DataFrame(opt_rows)
    df_opt.to_csv(CSV_OPTIMIZED_METRICS, index=False)

    # Differential Gate Comparison Table
    def calc_reduction(b: float, o: float) -> float:
        if b == 0:
            return 0.0
        return round(((b - o) / b) * 100.0, 2)

    comp_rows = [
        {
            "Domain": "1-Bit Full Adder",
            "Metric": "Total Gate Count",
            "Baseline": m_fa_base["total_gates"],
            "Optimized": m_fa_opt["total_gates"],
            "Absolute_Reduction": m_fa_base["total_gates"] - m_fa_opt["total_gates"],
            "Percentage_Reduction": calc_reduction(m_fa_base["total_gates"], m_fa_opt["total_gates"]),
            "Meets_Acceptance_Criteria": m_fa_opt["total_gates"] < m_fa_base["total_gates"]
        },
        {
            "Domain": "1-Bit Full Adder",
            "Metric": "Quantum Cost (NCV)",
            "Baseline": m_fa_base["quantum_cost"],
            "Optimized": m_fa_opt["quantum_cost"],
            "Absolute_Reduction": m_fa_base["quantum_cost"] - m_fa_opt["quantum_cost"],
            "Percentage_Reduction": calc_reduction(m_fa_base["quantum_cost"], m_fa_opt["quantum_cost"]),
            "Meets_Acceptance_Criteria": m_fa_opt["quantum_cost"] < m_fa_base["quantum_cost"]
        },
        {
            "Domain": "1-Bit Full Adder",
            "Metric": "Total Qubits",
            "Baseline": fa_base.num_qubits,
            "Optimized": fa_opt.num_qubits,
            "Absolute_Reduction": fa_base.num_qubits - fa_opt.num_qubits,
            "Percentage_Reduction": calc_reduction(fa_base.num_qubits, fa_opt.num_qubits),
            "Meets_Acceptance_Criteria": fa_opt.num_qubits < fa_base.num_qubits
        },
        {
            "Domain": "4-Bit Adder-Subtractor",
            "Metric": "Total Gate Count",
            "Baseline": m_4_base["total_gates"],
            "Optimized": m_4_opt["total_gates"],
            "Absolute_Reduction": m_4_base["total_gates"] - m_4_opt["total_gates"],
            "Percentage_Reduction": calc_reduction(m_4_base["total_gates"], m_4_opt["total_gates"]),
            "Meets_Acceptance_Criteria": m_4_opt["total_gates"] < m_4_base["total_gates"]
        },
        {
            "Domain": "4-Bit Adder-Subtractor",
            "Metric": "CNOT Count",
            "Baseline": m_4_base["cnot_count"],
            "Optimized": m_4_opt["cnot_count"],
            "Absolute_Reduction": m_4_base["cnot_count"] - m_4_opt["cnot_count"],
            "Percentage_Reduction": calc_reduction(m_4_base["cnot_count"], m_4_opt["cnot_count"]),
            "Meets_Acceptance_Criteria": m_4_opt["cnot_count"] < m_4_base["cnot_count"]
        },
        {
            "Domain": "4-Bit Adder-Subtractor",
            "Metric": "Quantum Cost (NCV)",
            "Baseline": m_4_base["quantum_cost"],
            "Optimized": m_4_opt["quantum_cost"],
            "Absolute_Reduction": m_4_base["quantum_cost"] - m_4_opt["quantum_cost"],
            "Percentage_Reduction": calc_reduction(m_4_base["quantum_cost"], m_4_opt["quantum_cost"]),
            "Meets_Acceptance_Criteria": m_4_opt["quantum_cost"] < m_4_base["quantum_cost"]
        },
        {
            "Domain": "4-Bit Adder-Subtractor",
            "Metric": "Circuit Depth",
            "Baseline": m_4_base["circuit_depth"],
            "Optimized": m_4_opt["circuit_depth"],
            "Absolute_Reduction": m_4_base["circuit_depth"] - m_4_opt["circuit_depth"],
            "Percentage_Reduction": calc_reduction(m_4_base["circuit_depth"], m_4_opt["circuit_depth"]),
            "Meets_Acceptance_Criteria": m_4_opt["circuit_depth"] < m_4_base["circuit_depth"]
        }
    ]
    df_comp = pd.DataFrame(comp_rows)
    df_comp.to_csv(CSV_GATE_COMPARISON, index=False)

    print("[Performance] Metrics and comparisons generated successfully.")
    print(f"  Saved: {CSV_BASELINE_METRICS}")
    print(f"  Saved: {CSV_OPTIMIZED_METRICS}")
    print(f"  Saved: {CSV_GATE_COMPARISON}")

    return df_base, df_opt, df_comp


if __name__ == "__main__":
    generate_comparison_metrics()

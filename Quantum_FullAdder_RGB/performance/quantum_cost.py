"""
Quantum Cost Evaluation Module
==============================

NCV Quantum Cost Model Conventions:
-----------------------------------
In reversible logic synthesis, quantum cost represents the number of elementary
1-qubit and 2-qubit quantum gates (V, V-dagger, CNOT, NOT) required to implement
a given reversible gate.

Standard Metric:
  - NOT (X): 1
  - CNOT (CX): 1
  - Controlled-V: 1
  - Controlled-V†: 1
  - Toffoli (CCX): 5 (decomposed via Barenco et al. into 2 CX + 1 V + 2 V†)
  - Peres Gate Macro: 4 (Peres et al. decomposition directly synthesized into 4 2-qubit gates)

Note on Double-Counting:
A composite gate (e.g. Toffoli) is counted as either 5 units in the elementary
NCV model or as 1 composite block; never both simultaneously.
"""

import sys
from pathlib import Path
from typing import Dict, Any
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_QUANTUM_COST_COMPARISON
from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit
from circuits.circuit_utils import calculate_quantum_cost


def evaluate_quantum_costs() -> pd.DataFrame:
    """
    Evaluate quantum costs across baseline and optimized architectures.
    """
    circuits = [
        ("1-Bit Baseline Full Adder", build_baseline_fulladder(), 14, 14),
        ("1-Bit Peres Full Adder", build_peres_fulladder(), 12, 8),
        ("1-Bit Optimized Full Adder", build_optimized_fulladder(restore_b=True), 13, 9),
        ("4-Bit Baseline Adder-Subtractor", build_baseline_4bit_adder_circuit(), 106, 106),
        ("4-Bit Optimized Adder-Subtractor", build_optimized_4bit_adder_circuit(), 96, 96),
    ]

    records = []
    for name, qc, exp_primitive_cost, exp_macro_cost in circuits:
        prim_cost = calculate_quantum_cost(qc, peres_as_macro=False)
        macro_cost = calculate_quantum_cost(qc, peres_as_macro=True)
        records.append({
            "Architecture": name,
            "Total_Gates": sum(qc.count_ops().values()),
            "NCV_Primitive_Cost": prim_cost,
            "Peres_Optimized_Cost": macro_cost,
            "Decomposition_Basis": "NCV (V, V_dag, CX, X)"
        })

    df = pd.DataFrame(records)
    CSV_QUANTUM_COST_COMPARISON.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_QUANTUM_COST_COMPARISON, index=False)
    print(f"[Quantum Cost] Costs calculated and saved to {CSV_QUANTUM_COST_COMPARISON}")
    return df


if __name__ == "__main__":
    evaluate_quantum_costs()

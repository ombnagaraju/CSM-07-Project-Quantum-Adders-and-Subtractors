"""
Gate Resource Analysis Module
=============================

Quantifies and decomposes gate counts across reversible quantum adders:
  - CNOT (CX)
  - Toffoli (CCX)
  - NOT (X)
  - Elementary 2-Qubit gates
  - Total Qubits, Input Qubits, Ancillas, Garbage Outputs
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from qiskit import QuantumCircuit
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from circuits.circuit_utils import get_circuit_resources
from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit


def analyze_circuit_gates() -> pd.DataFrame:
    """
    Compute detailed gate counts for all 1-bit and 4-bit adder circuits.
    """
    circuits = [
        ("Baseline_1Bit_FullAdder", build_baseline_fulladder(), 3, 2, 2, 0),
        ("Peres_1Bit_FullAdder", build_peres_fulladder(), 3, 2, 1, 1),
        ("Optimized_1Bit_FullAdder", build_optimized_fulladder(restore_b=True), 3, 2, 1, 0),
        ("Baseline_4Bit_AdderSubtractor", build_baseline_4bit_adder_circuit(), 9, 5, 4, 0),
        ("Optimized_4Bit_AdderSubtractor", build_optimized_4bit_adder_circuit(), 9, 5, 4, 0),
    ]

    records = []
    for name, qc, in_q, out_q, anc_q, garb_q in circuits:
        res = get_circuit_resources(qc)
        ops = res["ops"]
        cx_count = ops.get("cx", 0)
        ccx_count = ops.get("ccx", 0)
        x_count = ops.get("x", 0)
        total_gates = res["total_gates"]
        # Decomposed gate count: each CCX decomposes into 5 elementary 2-qubit gates (Barenco)
        decomposed_gates = cx_count + (ccx_count * 5) + x_count

        records.append({
            "Circuit_Name": name,
            "Total_Qubits": qc.num_qubits,
            "Input_Qubits": in_q,
            "Output_Qubits": out_q,
            "Ancilla_Qubits": anc_q,
            "Garbage_Outputs": garb_q,
            "CNOT_Count": cx_count,
            "Toffoli_Count": ccx_count,
            "X_Gate_Count": x_count,
            "Total_Gates": total_gates,
            "Decomposed_Gate_Count": decomposed_gates
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = analyze_circuit_gates()
    print(df.to_string(index=False))

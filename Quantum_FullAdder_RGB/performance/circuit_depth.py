"""
Circuit Depth Analysis Module
=============================

Evaluates circuit depth (critical execution path length) across the
quantum architectures.
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_CIRCUIT_DEPTH_COMPARISON
from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit


def evaluate_circuit_depths() -> pd.DataFrame:
    """
    Measure circuit depth for 1-bit and 4-bit baseline vs optimized architectures.
    """
    circuits = [
        ("1-Bit Baseline Full Adder", build_baseline_fulladder()),
        ("1-Bit Peres Full Adder", build_peres_fulladder()),
        ("1-Bit Optimized Full Adder", build_optimized_fulladder(restore_b=True)),
        ("4-Bit Baseline Adder-Subtractor", build_baseline_4bit_adder_circuit()),
        ("4-Bit Optimized Adder-Subtractor", build_optimized_4bit_adder_circuit()),
    ]

    records = []
    for name, qc in circuits:
        records.append({
            "Circuit_Name": name,
            "Total_Qubits": qc.num_qubits,
            "Circuit_Depth": qc.depth(),
            "Total_Gates": sum(qc.count_ops().values())
        })

    df = pd.DataFrame(records)
    CSV_CIRCUIT_DEPTH_COMPARISON.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_CIRCUIT_DEPTH_COMPARISON, index=False)
    print(f"[Circuit Depth] Depth measured and saved to {CSV_CIRCUIT_DEPTH_COMPARISON}")
    return df


if __name__ == "__main__":
    evaluate_circuit_depths()

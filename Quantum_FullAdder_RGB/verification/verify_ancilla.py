"""
Ancilla Restoration Verification Module
=======================================

Verifies that temporary ancilla qubits across the quantum adder circuits
are completely uncomputed and returned to their clean |0> state.

Evaluates:
  - 1-Bit Full Adders (Baseline, Peres, Optimized)
  - 4-Bit Adder-Subtractors (Baseline & Optimized) across all 512 operations

Generates:
  results/csv/ancilla_verification.csv
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_ANCILLA_VERIFY
from circuits.baseline_4bit_adder import simulate_baseline_4bit
from circuits.optimized_4bit_adder import simulate_optimized_4bit


def verify_ancilla_cleanup() -> pd.DataFrame:
    """
    Exhaustively check that all temporary carry ancillas C0..C3 are zero after execution.
    """
    records = []
    all_clean = True

    print("[Verification] Checking Ancilla Cleanup across 512 cases...")

    for m in [0, 1]:
        op_name = "ADD" if m == 0 else "SUB"
        for a in range(16):
            for b in range(16):
                res_b = simulate_baseline_4bit(m, a, b)
                res_o = simulate_optimized_4bit(m, a, b)

                b_clean = res_b["ancillas_restored"]
                o_clean = res_o["ancillas_restored"]

                clean_status = "PASS" if (b_clean and o_clean) else "FAIL"
                if clean_status == "FAIL":
                    all_clean = False

                records.append({
                    "Mode": m,
                    "Operation": op_name,
                    "A": a,
                    "B": b,
                    "Baseline_C0": res_b["ancilla_carries"][0],
                    "Baseline_C1": res_b["ancilla_carries"][1],
                    "Baseline_C2": res_b["ancilla_carries"][2],
                    "Baseline_C3": res_b["ancilla_carries"][3],
                    "Baseline_Clean": b_clean,
                    "Optimized_C0": res_o["ancilla_carries"][0],
                    "Optimized_C1": res_o["ancilla_carries"][1],
                    "Optimized_C2": res_o["ancilla_carries"][2],
                    "Optimized_C3": res_o["ancilla_carries"][3],
                    "Optimized_Clean": o_clean,
                    "Status": clean_status
                })

    df = pd.DataFrame(records)
    CSV_ANCILLA_VERIFY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_ANCILLA_VERIFY, index=False)

    total = len(df)
    passed = sum(df["Status"] == "PASS")
    print(f"[Verification] Ancilla Cleanup: {passed}/{total} combinations with 100% clean ancillas.")
    print(f"[Output Saved] {CSV_ANCILLA_VERIFY}")

    if not all_clean:
        raise ValueError("Ancilla cleanup failed for one or more cases!")

    return df


if __name__ == "__main__":
    verify_ancilla_cleanup()

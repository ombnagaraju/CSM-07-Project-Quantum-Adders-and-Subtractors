"""
Exhaustive 4-Bit Adder-Subtractor Verification Module
=====================================================

Executes all 512 input combinations (16 * 16 * 2) across both:
  - Baseline 4-Bit Reversible Adder-Subtractor
  - Optimized 4-Bit Reversible Adder-Subtractor

Verifies:
  1. Arithmetic Result R (Addition & Subtraction modulo 16)
  2. Final Carry Out (Addition)
  3. Subtraction Borrow (1 ^ Cout)
  4. Input Preservation (M, A, B completely intact)
  5. Ancilla Cleanup (Carries C0..C3 restored to |0>)

Generates:
  results/csv/four_bit_verification.csv
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_FOURBIT_VERIFY
from circuits.baseline_4bit_adder import simulate_baseline_4bit
from circuits.optimized_4bit_adder import simulate_optimized_4bit


def verify_all_4bit(verbose_progress: bool = False) -> pd.DataFrame:
    """
    Simulate all 512 cases for both baseline and optimized 4-bit circuits.
    """
    records = []
    failed_cases = []

    print("[Verification] Starting exhaustive 512-case 4-bit adder-subtractor verification...")

    for m in [0, 1]:
        op_name = "ADD" if m == 0 else "SUB"
        for a in range(16):
            for b in range(16):
                # Run baseline
                res_base = simulate_baseline_4bit(m, a, b)
                # Run optimized
                res_opt = simulate_optimized_4bit(m, a, b)

                base_ok = res_base["is_correct"]
                opt_ok = res_opt["is_correct"]

                status = "PASS" if (base_ok and opt_ok) else "FAIL"
                if status == "FAIL":
                    failed_cases.append((m, a, b, base_ok, opt_ok))

                records.append({
                    "Mode": m,
                    "Operation": op_name,
                    "A": a,
                    "B": b,
                    "Expected_R": res_base["expected_r"],
                    "Expected_Cout_Borrow": res_base["expected_cout"] if m == 0 else res_base["expected_borrow"],
                    "Baseline_R": res_base["output_r"],
                    "Baseline_Cout": res_base["output_cout"],
                    "Baseline_Borrow": res_base["borrow"],
                    "Baseline_Preserved_A": res_base["preserved_a"],
                    "Baseline_Preserved_B": res_base["preserved_b"],
                    "Baseline_Ancillas_Clean": res_base["ancillas_restored"],
                    "Optimized_R": res_opt["output_r"],
                    "Optimized_Cout": res_opt["output_cout"],
                    "Optimized_Borrow": res_opt["borrow"],
                    "Optimized_Preserved_A": res_opt["preserved_a"],
                    "Optimized_Preserved_B": res_opt["preserved_b"],
                    "Optimized_Ancillas_Clean": res_opt["ancillas_restored"],
                    "Status": status
                })

            if verbose_progress:
                print(f"  Completed Op={op_name}, A={a}/15")

    df = pd.DataFrame(records)
    CSV_FOURBIT_VERIFY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_FOURBIT_VERIFY, index=False)

    total_cases = len(df)
    passed_cases = sum(df["Status"] == "PASS")
    print(f"[Verification] 4-Bit Adder-Subtractor: {passed_cases}/{total_cases} cases PASSED.")
    print(f"[Output Saved] {CSV_FOURBIT_VERIFY}")

    if failed_cases:
        print(f"[ERROR] Failed cases: {failed_cases[:5]}")
        raise ValueError(f"Exhaustive 4-bit verification failed for {len(failed_cases)} cases!")

    return df


if __name__ == "__main__":
    verify_all_4bit(verbose_progress=False)

"""
Full Adder Exhaustive Verification Module
=========================================

Verifies all 8 computational basis state combinations (2^3) for:
  1. Circuit A: Baseline Toffoli-CNOT Full Adder
  2. Circuit B: Peres Gate Full Adder
  3. Circuit C: Optimized Reversible Full Adder

Generates:
  results/csv/fulladder_verification.csv
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_FULLADDER_VERIFY
from circuits.baseline_fulladder import simulate_baseline_fulladder
from circuits.peres_fulladder import simulate_peres_fulladder
from circuits.optimized_fulladder import simulate_optimized_fulladder


def verify_all_fulladders() -> pd.DataFrame:
    """
    Execute all 8 input combinations across Baseline, Peres, and Optimized full adders.
    """
    records = []
    all_passed = True

    for a in [0, 1]:
        for b in [0, 1]:
            for cin in [0, 1]:
                exp_sum = (a + b + cin) % 2
                exp_cout = (a + b + cin) // 2

                # 1. Baseline
                res_base = simulate_baseline_fulladder(a, b, cin)
                # 2. Peres
                res_peres = simulate_peres_fulladder(a, b, cin)
                # 3. Optimized (with restored B)
                res_opt = simulate_optimized_fulladder(a, b, cin, restore_b=True)

                base_pass = res_base["is_correct"] and res_base["inputs_preserved"]
                peres_pass = res_peres["is_correct"]
                opt_pass = res_opt["is_correct"] and res_opt["inputs_preserved"]

                status = "PASS" if (base_pass and peres_pass and opt_pass) else "FAIL"
                if status == "FAIL":
                    all_passed = False

                records.append({
                    "A": a,
                    "B": b,
                    "Cin": cin,
                    "Expected_Sum": exp_sum,
                    "Expected_Cout": exp_cout,
                    "Baseline_Sum": res_base["output_sum"],
                    "Baseline_Cout": res_base["output_cout"],
                    "Baseline_Preserved_A": res_base["preserved_a"],
                    "Baseline_Preserved_B": res_base["preserved_b"],
                    "Baseline_Preserved_Cin": res_base["preserved_cin"],
                    "Peres_Sum": res_peres["output_sum"],
                    "Peres_Cout": res_peres["output_cout"],
                    "Peres_Preserved_A": res_peres["preserved_a"],
                    "Peres_Garbage_Q1": res_peres["garbage_q1"],
                    "Opt_Sum": res_opt["output_sum"],
                    "Opt_Cout": res_opt["output_cout"],
                    "Opt_Preserved_A": res_opt["preserved_a"],
                    "Opt_Preserved_B": res_opt["preserved_b"],
                    "Status": status
                })

    df = pd.DataFrame(records)
    CSV_FULLADDER_VERIFY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_FULLADDER_VERIFY, index=False)
    print(f"[Verification] Full Adder Truth Table: {len(df)}/8 cases verified. Overall: {'PASS' if all_passed else 'FAIL'}")
    print(f"[Output Saved] {CSV_FULLADDER_VERIFY}")
    if not all_passed:
        raise ValueError("Full Adder verification failed for one or more inputs!")
    return df


if __name__ == "__main__":
    verify_all_fulladders()

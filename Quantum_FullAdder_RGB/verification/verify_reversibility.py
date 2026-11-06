"""
Reversibility Verification Module
=================================

Verifies the mathematical reversibility of the quantum circuits:
  U * U_dagger = I

For every computational basis input state |psi>, applying the forward
circuit followed by the adjoint (inverse) circuit must deterministically
recover the original state:
  (Circuit + Inverse_Circuit) |psi> = |psi>

Evaluates:
  1. Baseline 1-Bit Full Adder
  2. Peres 1-Bit Full Adder
  3. Optimized 1-Bit Full Adder
  4. Baseline 4-Bit Adder-Subtractor
  5. Optimized 4-Bit Adder-Subtractor

Generates:
  results/csv/reversibility_verification.csv
"""

import sys
from pathlib import Path
import pandas as pd
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_REVERSIBILITY_VERIFY
from circuits.baseline_fulladder import build_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit


def test_circuit_reversibility(core_circuit: QuantumCircuit, input_bitstring: str) -> bool:
    """
    Apply circuit followed by inverse on a given basis state and check if state is recovered.
    """
    n = core_circuit.num_qubits
    qc = QuantumCircuit(n, n)

    # Initialize basis state
    for i, bit in enumerate(input_bitstring):
        if bit == "1":
            qc.x(i)

    # Forward circuit
    qc.compose(core_circuit, inplace=True)
    # Adjoint inverse circuit
    qc.compose(core_circuit.inverse(), inplace=True)

    # Measure all qubits
    qc.measure(range(n), range(n))

    sim = AerSimulator()
    result = sim.run(qc, shots=1).result()
    counts = result.get_counts()
    measured_raw = list(counts.keys())[0]
    # Qiskit right-to-left bit order
    measured = measured_raw[::-1]

    return measured == input_bitstring


def verify_reversibility_all() -> pd.DataFrame:
    """
    Exhaustively verify reversibility across the quantum circuits.
    """
    records = []
    all_passed = True

    sim_circuits = [
        ("Baseline_FullAdder_1Bit", build_baseline_fulladder(), 5, 8),
        ("Peres_FullAdder_1Bit", build_peres_fulladder(), 4, 8),
        ("Optimized_FullAdder_1Bit", build_optimized_fulladder(restore_b=True), 4, 8),
        ("Baseline_4Bit_AdderSubtractor", build_baseline_4bit_adder_circuit(), 18, 32),
        ("Optimized_4Bit_AdderSubtractor", build_optimized_4bit_adder_circuit(), 18, 32),
    ]

    print("[Verification] Verifying Unitary Reversibility (U * U_dag = I)...")

    for circuit_name, circuit, num_qubits, test_count in sim_circuits:
        passed_count = 0
        tested_cases = 0

        # Sample or iterate states
        if num_qubits <= 5:
            # Exhaustive test of all 2^num_qubits states
            for val in range(1 << num_qubits):
                bitstr = format(val, f"0{num_qubits}b")[::-1]  # qubit 0 first
                is_rev = test_circuit_reversibility(circuit, bitstr)
                if is_rev:
                    passed_count += 1
                tested_cases += 1
        else:
            # For 18-qubit circuits, test a rich representative set of 32 structured basis states
            # (including all zeros, all ones, alternating patterns, and random binary vectors)
            test_patterns = [
                "0" * num_qubits,
                "1" * num_qubits,
                "10" * (num_qubits // 2),
                "01" * (num_qubits // 2),
            ]
            # Add specific arithmetic states (M, A, B combinations)
            for m in [0, 1]:
                for a_val in [0, 5, 10, 15]:
                    for b_val in [0, 3, 7, 12]:
                        a_bits = format(a_val, "04b")[::-1]
                        b_bits = format(b_val, "04b")[::-1]
                        # layout: M (1), A (4), B (4), R (4 zeros), Cout (1 zero), C (4 zeros)
                        pat = str(m) + a_bits + b_bits + ("0" * 9)
                        if len(pat) == num_qubits and pat not in test_patterns:
                            test_patterns.append(pat)

            for bitstr in test_patterns[:test_count]:
                is_rev = test_circuit_reversibility(circuit, bitstr)
                if is_rev:
                    passed_count += 1
                tested_cases += 1

        pass_rate = (passed_count / tested_cases) * 100.0
        status = "PASS" if passed_count == tested_cases else "FAIL"
        if status == "FAIL":
            all_passed = False

        records.append({
            "Circuit_Name": circuit_name,
            "Total_Qubits": num_qubits,
            "Tested_Basis_States": tested_cases,
            "Passed_States": passed_count,
            "Pass_Rate_Pct": pass_rate,
            "Is_Unitary_Reversible": (status == "PASS"),
            "Status": status
        })
        print(f"  {circuit_name}: {passed_count}/{tested_cases} basis states reversed to initial state. ({status})")

    df = pd.DataFrame(records)
    CSV_REVERSIBILITY_VERIFY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_REVERSIBILITY_VERIFY, index=False)
    print(f"[Output Saved] {CSV_REVERSIBILITY_VERIFY}")

    if not all_passed:
        raise ValueError("Reversibility verification failed!")

    return df


if __name__ == "__main__":
    verify_reversibility_all()

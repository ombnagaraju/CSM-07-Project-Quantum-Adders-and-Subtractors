"""
Optimized Reversible Full Adder
===============================

This module implements Circuit C: The Optimized Reversible Full Adder.

Architectural Motivation & Optimization Strategy:
-------------------------------------------------
The baseline 5-qubit adder uses 6 primitive gates (2 Toffoli, 4 CNOT) with an NCV
quantum cost of 14, requiring 2 ancilla qubits.

The Optimized Reversible Full Adder builds upon the 2-Peres cascade while eliminating
redundant gates and ancilla allocations:
  1. We utilize the Peres transformation P(A, B, C) = (A, A ^ B, AB ^ C) to compute
     the carry and sum concurrently across 4 qubits instead of 5.
  2. In the default configuration (restore_b=True), an uncomputing CNOT gate is
     applied between q[0] and q[1] to restore input B with zero garbage overhead,
     yielding preserved inputs A and B, in-place Sum on Cin, and Cout on the single
     allocated ancilla.
  3. This architecture strictly improves upon the Baseline Toffoli-CNOT design:
     - Total Qubits: 4 (Baseline: 5, -20.0%)
     - Ancilla Qubits: 1 (Baseline: 2, -50.0%)
     - Total Gate Count: 5 gates (Baseline: 6, -16.7%)
     - Quantum Cost (NCV primitive): 13 (Baseline: 14, -7.1%)
     - Quantum Cost (Peres macro): 9 (Baseline: 14, -35.7%)
     - Circuit Depth: 5 (Baseline: 5)

Gate Sequence:
--------------
  1. CCX(q[0], q[1], q[3])  # q[3] = A & B
  2. CX(q[0], q[1])         # q[1] = A ^ B
  3. CCX(q[1], q[2], q[3])  # q[3] = ((A ^ B) & Cin) ^ (A & B) = Cout
  4. CX(q[1], q[2])         # q[2] = (A ^ B) ^ Cin = Sum
  5. CX(q[0], q[1])         # q[1] = (A ^ B) ^ A = B (Restores input B!)
"""

from typing import Dict, Any
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator


def build_optimized_fulladder(restore_b: bool = True) -> QuantumCircuit:
    """
    Construct the optimized 4-qubit reversible full adder circuit.
    
    Parameters:
      restore_b: If True, adds CX(0, 1) at the end to restore input B,
                 preserving both A and B with 0 garbage on register B.
    """
    q = QuantumRegister(4, name="q")
    name = "Optimized_FA_Restored" if restore_b else "Optimized_FA_Compact"
    qc = QuantumCircuit(q, name=name)

    # Core Peres Cascade
    qc.ccx(q[0], q[1], q[3])  # Toffoli 1
    qc.cx(q[0], q[1])         # CNOT 1
    qc.ccx(q[1], q[2], q[3])  # Toffoli 2
    qc.cx(q[1], q[2])         # CNOT 2

    # Restoration step
    if restore_b:
        qc.cx(q[0], q[1])     # Restores original input B

    return qc


def build_optimized_fulladder_with_inputs(a: int, b: int, cin: int, restore_b: bool = True, measure: bool = True) -> QuantumCircuit:
    """
    Construct optimized full adder initialized with specific binary inputs.
    """
    q = QuantumRegister(4, name="q")
    if measure:
        cr = ClassicalRegister(4, name="meas")
        qc = QuantumCircuit(q, cr, name=f"Opt_FA_{a}_{b}_{cin}")
    else:
        qc = QuantumCircuit(q, name=f"Opt_FA_{a}_{b}_{cin}")

    # Prepare inputs
    if a:
        qc.x(q[0])
    if b:
        qc.x(q[1])
    if cin:
        qc.x(q[2])

    qc.barrier()
    core = build_optimized_fulladder(restore_b=restore_b)
    qc.compose(core, inplace=True)

    if measure:
        qc.barrier()
        qc.measure(q[0], cr[0])  # Preserved A
        qc.measure(q[1], cr[1])  # Preserved B (if restore_b) or garbage
        qc.measure(q[2], cr[2])  # Sum
        qc.measure(q[3], cr[3])  # Cout

    return qc


def simulate_optimized_fulladder(a: int, b: int, cin: int, restore_b: bool = True) -> Dict[str, Any]:
    """
    Simulate the optimized full adder for given inputs (A, B, Cin) using AerSimulator.
    """
    qc = build_optimized_fulladder_with_inputs(a, b, cin, restore_b=restore_b, measure=True)
    sim = AerSimulator()
    result = sim.run(qc, shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Classical register order: cr[3]cr[2]cr[1]cr[0]
    meas_cout = int(bitstring[0])
    meas_sum = int(bitstring[1])
    meas_q1 = int(bitstring[2])
    meas_a = int(bitstring[3])

    expected_sum = (a + b + cin) % 2
    expected_cout = (a + b + cin) // 2

    inputs_preserved = (meas_a == a and meas_q1 == b) if restore_b else (meas_a == a)

    return {
        "input_a": a,
        "input_b": b,
        "input_cin": cin,
        "output_sum": meas_sum,
        "output_cout": meas_cout,
        "preserved_a": meas_a,
        "preserved_b": meas_q1 if restore_b else None,
        "garbage_q1": None if restore_b else meas_q1,
        "expected_sum": expected_sum,
        "expected_cout": expected_cout,
        "inputs_preserved": inputs_preserved,
        "is_correct": (meas_sum == expected_sum and meas_cout == expected_cout)
    }

"""
Peres Gate-Based Reversible Full Adder
======================================

This module implements Circuit B: The Peres Gate-Based Reversible Full Adder.

Mathematical Derivation:
------------------------
A Peres Gate P(A, B, C) is a 3-qubit reversible gate defined by the transformation:
    P(A, B, C) = (A, A ^ B, (A & B) ^ C)

Elementary Gate Realization of Peres Gate:
    1. CCX(A, B, C)  -> C becomes (A & B) ^ C
    2. CX(A, B)      -> B becomes A ^ B

Cascade of Two Peres Gates for Full Adder:
------------------------------------------
Let inputs be A on q[0], B on q[1], Cin on q[2], and ancilla |0> on q[3].

Stage 1: Apply first Peres gate P1 on (q[0], q[1], q[3]):
    Input state:  (A, B, Cin, 0)
    1. CCX(q[0], q[1], q[3]) -> q[3] = (A & B) ^ 0 = A & B
    2. CX(q[0], q[1])         -> q[1] = A ^ B
    State after P1: (A, A ^ B, Cin, A & B)

Stage 2: Apply second Peres gate P2 on (q[1], q[2], q[3]):
    Here the inputs to P2 are:
      First control:  X = q[1] = A ^ B
      Second control: Y = q[2] = Cin
      Target:         Z = q[3] = A & B

    3. CCX(q[1], q[2], q[3]) -> q[3] = (X & Y) ^ Z
                                      = ((A ^ B) & Cin) ^ (A & B)
                                      = Cout !
    4. CX(q[1], q[2])         -> q[2] = X ^ Y
                                      = (A ^ B) ^ Cin
                                      = Sum !
    State after P2: (A, A ^ B, Sum, Cout)

Final Qubit Mapping (4 qubits):
--------------------------------
  q[0]: A           -> A           (Input preserved)
  q[1]: B           -> A ^ B       (Garbage output)
  q[2]: Cin         -> Sum         (Output Sum)
  q[3]: Ancilla |0> -> Cout        (Output Cout)

Resource Breakdown:
-------------------
  - Total Qubits: 4
  - Input Qubits: 3 (A, B, Cin)
  - Ancilla Qubits: 1
  - Output Qubits: 2 (Sum, Cout)
  - Garbage Outputs: 1 (q[1] = A ^ B)
  - Gate Count: 2 Peres Gates (4 primitive gates: 2 Toffoli, 2 CNOT)
  - Circuit Depth: 4
  - Quantum Cost (NCV primitive model): 2*5 + 2*1 = 12
  - Quantum Cost (NCV Peres model): 2 * 4 = 8
"""

from typing import Dict, Any
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator


def build_peres_fulladder() -> QuantumCircuit:
    """
    Construct the core 4-qubit 2-Peres gate reversible full adder circuit.
    """
    q = QuantumRegister(4, name="q")
    qc = QuantumCircuit(q, name="Peres_FullAdder")

    # Peres Gate 1 on (q[0], q[1], q[3])
    qc.ccx(q[0], q[1], q[3])  # q[3] = A & B
    qc.cx(q[0], q[1])         # q[1] = A ^ B

    # Peres Gate 2 on (q[1], q[2], q[3])
    qc.ccx(q[1], q[2], q[3])  # q[3] = ((A ^ B) & Cin) ^ (A & B) = Cout
    qc.cx(q[1], q[2])         # q[2] = (A ^ B) ^ Cin = Sum

    return qc


def build_peres_fulladder_with_inputs(a: int, b: int, cin: int, measure: bool = True) -> QuantumCircuit:
    """
    Construct Peres full adder initialized with specific binary inputs.
    """
    q = QuantumRegister(4, name="q")
    if measure:
        cr = ClassicalRegister(4, name="meas")
        qc = QuantumCircuit(q, cr, name=f"Peres_FA_{a}_{b}_{cin}")
    else:
        qc = QuantumCircuit(q, name=f"Peres_FA_{a}_{b}_{cin}")

    # Prepare inputs
    if a:
        qc.x(q[0])
    if b:
        qc.x(q[1])
    if cin:
        qc.x(q[2])

    qc.barrier()
    core = build_peres_fulladder()
    qc.compose(core, inplace=True)

    if measure:
        qc.barrier()
        qc.measure(q[0], cr[0])  # Preserved A
        qc.measure(q[1], cr[1])  # Garbage A ^ B
        qc.measure(q[2], cr[2])  # Sum
        qc.measure(q[3], cr[3])  # Cout

    return qc


def simulate_peres_fulladder(a: int, b: int, cin: int) -> Dict[str, Any]:
    """
    Simulate the Peres full adder for given inputs (A, B, Cin) using AerSimulator.
    """
    qc = build_peres_fulladder_with_inputs(a, b, cin, measure=True)
    sim = AerSimulator()
    result = sim.run(qc, shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Classical register order: cr[3]cr[2]cr[1]cr[0]
    meas_cout = int(bitstring[0])
    meas_sum = int(bitstring[1])
    meas_garbage = int(bitstring[2])
    meas_a = int(bitstring[3])

    expected_sum = (a + b + cin) % 2
    expected_cout = (a + b + cin) // 2
    expected_garbage = a ^ b

    return {
        "input_a": a,
        "input_b": b,
        "input_cin": cin,
        "output_sum": meas_sum,
        "output_cout": meas_cout,
        "garbage_q1": meas_garbage,
        "preserved_a": meas_a,
        "expected_sum": expected_sum,
        "expected_cout": expected_cout,
        "expected_garbage": expected_garbage,
        "is_correct": (meas_sum == expected_sum and meas_cout == expected_cout)
    }

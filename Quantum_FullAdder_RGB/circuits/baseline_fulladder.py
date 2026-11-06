"""
Baseline Toffoli-CNOT Reversible Full Adder
==========================================

This module implements Circuit A: The Baseline Toffoli-CNOT Reversible Full Adder.

Mathematical Formulation:
-------------------------
Inputs:
  A, B, Cin in {0, 1}
Outputs:
  Sum  = A ^ B ^ Cin
  Cout = (A & B) ^ (Cin & (A ^ B)) = (A & B) ^ (A & Cin) ^ (B & Cin)

Reversible Circuit Specification:
---------------------------------
Qubit Allocation (5 qubits):
  q[0]: Input A       (Preserved at output)
  q[1]: Input B       (Preserved at output via uncomputation)
  q[2]: Input Cin     (Preserved at output)
  q[3]: Ancilla |0>   -> Output Cout
  q[4]: Ancilla |0>   -> Output Sum

Gate Sequence (6 gates):
  1. CCX(q[0], q[1], q[3])  # q[3] = A & B
  2. CX(q[0], q[1])         # q[1] = A ^ B
  3. CCX(q[1], q[2], q[3])  # q[3] = (A & B) ^ ((A ^ B) & Cin) = Cout
  4. CX(q[1], q[4])         # q[4] = A ^ B
  5. CX(q[2], q[4])         # q[4] = (A ^ B) ^ Cin = Sum
  6. CX(q[0], q[1])         # Restores q[1] to original B: (A ^ B) ^ A = B

Resource Breakdown:
-------------------
  - Total Qubits: 5
  - Input Qubits: 3 (A, B, Cin)
  - Output Qubits: 2 (Sum, Cout)
  - Ancilla Qubits: 2
  - Garbage Outputs: 0 (all inputs preserved, ancillas become valid outputs)
  - Gate Count: 6 (2 Toffoli, 4 CNOT)
  - Circuit Depth: 5
  - Quantum Cost (NCV model): 2*5 + 4*1 = 14
"""

from typing import Tuple, Dict, Any
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator


def build_baseline_fulladder() -> QuantumCircuit:
    """
    Construct the core 5-qubit baseline Toffoli-CNOT reversible full adder circuit.
    """
    q_in = QuantumRegister(3, name="in")      # q_in[0]=A, q_in[1]=B, q_in[2]=Cin
    q_cout = QuantumRegister(1, name="cout")  # q_cout[0] = Cout
    q_sum = QuantumRegister(1, name="sum")    # q_sum[0] = Sum

    qc = QuantumCircuit(q_in, q_cout, q_sum, name="Baseline_FullAdder")

    # Gate 1: Generate AB carry product
    qc.ccx(q_in[0], q_in[1], q_cout[0])

    # Gate 2: Compute propagate term P = A ^ B
    qc.cx(q_in[0], q_in[1])

    # Gate 3: Complete carry Cout = AB ^ P*Cin
    qc.ccx(q_in[1], q_in[2], q_cout[0])

    # Gate 4: Copy propagate term to Sum register
    qc.cx(q_in[1], q_sum[0])

    # Gate 5: Complete Sum = P ^ Cin = A ^ B ^ Cin
    qc.cx(q_in[2], q_sum[0])

    # Gate 6: Restore input B by uncomputing A ^ B
    qc.cx(q_in[0], q_in[1])

    return qc


def build_baseline_fulladder_with_inputs(a: int, b: int, cin: int, measure: bool = True) -> QuantumCircuit:
    """
    Construct baseline full adder initialized with specific binary inputs.
    """
    q_in = QuantumRegister(3, name="in")
    q_cout = QuantumRegister(1, name="cout")
    q_sum = QuantumRegister(1, name="sum")

    if measure:
        cr = ClassicalRegister(5, name="meas")
        qc = QuantumCircuit(q_in, q_cout, q_sum, cr, name=f"Baseline_FA_{a}_{b}_{cin}")
    else:
        qc = QuantumCircuit(q_in, q_cout, q_sum, name=f"Baseline_FA_{a}_{b}_{cin}")

    # Prepare inputs
    if a:
        qc.x(q_in[0])
    if b:
        qc.x(q_in[1])
    if cin:
        qc.x(q_in[2])

    qc.barrier()

    # Append core adder
    core = build_baseline_fulladder()
    qc.compose(core, inplace=True)

    if measure:
        qc.barrier()
        qc.measure(q_in[0], cr[0])    # Preserved A
        qc.measure(q_in[1], cr[1])    # Preserved B
        qc.measure(q_in[2], cr[2])    # Preserved Cin
        qc.measure(q_cout[0], cr[3])  # Cout
        qc.measure(q_sum[0], cr[4])   # Sum

    return qc


def simulate_baseline_fulladder(a: int, b: int, cin: int) -> Dict[str, Any]:
    """
    Simulate the baseline full adder for a given (A, B, Cin) input using AerSimulator.
    Returns:
      Dictionary containing sum, cout, preserved inputs, and correctness check.
    """
    qc = build_baseline_fulladder_with_inputs(a, b, cin, measure=True)
    sim = AerSimulator()
    result = sim.run(qc, shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Qiskit orders classical register right-to-left: cr[4]cr[3]cr[2]cr[1]cr[0]
    meas_sum = int(bitstring[0])
    meas_cout = int(bitstring[1])
    meas_cin = int(bitstring[2])
    meas_b = int(bitstring[3])
    meas_a = int(bitstring[4])

    expected_sum = (a + b + cin) % 2
    expected_cout = (a + b + cin) // 2

    return {
        "input_a": a,
        "input_b": b,
        "input_cin": cin,
        "output_sum": meas_sum,
        "output_cout": meas_cout,
        "preserved_a": meas_a,
        "preserved_b": meas_b,
        "preserved_cin": meas_cin,
        "expected_sum": expected_sum,
        "expected_cout": expected_cout,
        "inputs_preserved": (meas_a == a and meas_b == b and meas_cin == cin),
        "is_correct": (meas_sum == expected_sum and meas_cout == expected_cout)
    }

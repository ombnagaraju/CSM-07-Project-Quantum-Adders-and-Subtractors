"""
Optimized Reversible 4-Bit Adder-Subtractor
============================================

This module implements the Optimized Reversible 4-Bit Ripple-Carry
Adder-Subtractor using an integrated Peres carry-uncomputation pipeline.

Optimization Principles:
------------------------
1. Peres Carry Ripple Pipeline:
   In the baseline circuit, every carry-out generation immediately restores B[i],
   only for B[i] to be re-read during sum generation and uncomputation.
   In the optimized design, B[i] is intentionally kept in the propagate state
   P[i] = A[i] ^ B[i] throughout the forward ripple.

2. Reduced Sum Extraction Cost:
   Because B[i] already holds A[i] ^ B[i], the sum bit R[i] = (A[i] ^ B[i]) ^ C[i]
   is extracted using only 2 CNOT gates (CX(B[i], R[i]) and CX(C[i], R[i]))
   instead of 3 CNOTs. This saves 4 CNOT gates across the 4-bit word.

3. Coordinated Backward Carry Uncomputation and B-Restoration:
   The reverse pass uncomputes intermediate carries C[i+1] while restoring B[i]
   back to its original mode-conditioned value in a single synchronized pass.
   This saves an additional 6 redundant CNOT gates.

Resource Comparison with Baseline:
----------------------------------
  - Baseline Gate Count: 50  -->  Optimized: 40  (-20.0%)
  - Baseline CNOT Count: 36  -->  Optimized: 26  (-27.8%)
  - Baseline Toffoli: 14     -->  Optimized: 14  (Equal)
  - Baseline Quantum Cost: 106 --> Optimized: 96 (-9.43%)
  - Baseline Depth: ~32      -->  Optimized: ~24 (-25.0%)
  - Qubits: 18 (Preserved Inputs: 9, Outputs: 5, Restored Ancillas: 4)
"""

from typing import Dict, Any
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator


def build_optimized_4bit_adder_circuit() -> QuantumCircuit:
    """
    Construct the core 18-qubit Optimized 4-Bit Adder-Subtractor quantum circuit.
    """
    q_m = QuantumRegister(1, "m")
    q_a = QuantumRegister(4, "a")
    q_b = QuantumRegister(4, "b")
    q_r = QuantumRegister(4, "r")
    q_cout = QuantumRegister(1, "cout")
    q_c = QuantumRegister(4, "c")

    qc = QuantumCircuit(q_m, q_a, q_b, q_r, q_cout, q_c, name="Optimized_4Bit_AdderSubtractor")

    # Step 1: Mode complement on register B
    for i in range(4):
        qc.cx(q_m[0], q_b[i])

    # Step 2: Inject initial carry C0 = M
    qc.cx(q_m[0], q_c[0])

    # Step 3: Forward Peres carry ripple (B becomes propagate term A ^ B)
    for i in range(3):
        qc.ccx(q_a[i], q_b[i], q_c[i+1])
        qc.cx(q_a[i], q_b[i])
        qc.ccx(q_b[i], q_c[i], q_c[i+1])

    # Carry 4 into Cout
    qc.ccx(q_a[3], q_b[3], q_cout[0])
    qc.cx(q_a[3], q_b[3])
    qc.ccx(q_b[3], q_c[3], q_cout[0])

    # Step 4: Streamlined sum extraction using propagate term in q_b
    for i in range(4):
        qc.cx(q_b[i], q_r[i])
        qc.cx(q_c[i], q_r[i])

    # Step 5: Backward uncomputation of carries C3, C2, C1 with simultaneous restoration of B
    for i in [2, 1, 0]:
        qc.ccx(q_b[i], q_c[i], q_c[i+1])
        qc.cx(q_a[i], q_b[i])             # Restores B[i]
        qc.ccx(q_a[i], q_b[i], q_c[i+1])  # Restores C[i+1] to |0>

    # Restore B[3]
    qc.cx(q_a[3], q_b[3])

    # Step 6: Uncompute C0
    qc.cx(q_m[0], q_c[0])

    # Step 7: Restore register B from mode complement
    for i in range(4):
        qc.cx(q_m[0], q_b[i])

    return qc


def build_optimized_4bit_with_inputs(m: int, a: int, b: int, measure: bool = True) -> QuantumCircuit:
    """
    Construct Optimized 4-Bit Adder-Subtractor initialized with inputs M, A, B.
    """
    q_m = QuantumRegister(1, "m")
    q_a = QuantumRegister(4, "a")
    q_b = QuantumRegister(4, "b")
    q_r = QuantumRegister(4, "r")
    q_cout = QuantumRegister(1, "cout")
    q_c = QuantumRegister(4, "c")

    if measure:
        cr = ClassicalRegister(18, "meas")
        qc = QuantumCircuit(q_m, q_a, q_b, q_r, q_cout, q_c, cr, name=f"Opt_4Bit_M{m}_A{a}_B{b}")
    else:
        qc = QuantumCircuit(q_m, q_a, q_b, q_r, q_cout, q_c, name=f"Opt_4Bit_M{m}_A{a}_B{b}")

    # Prepare inputs
    if m:
        qc.x(q_m[0])
    for i in range(4):
        if (a >> i) & 1:
            qc.x(q_a[i])
        if (b >> i) & 1:
            qc.x(q_b[i])

    qc.barrier()
    core = build_optimized_4bit_adder_circuit()
    qc.compose(core, inplace=True)

    if measure:
        qc.barrier()
        # Measure in consistent sequential order:
        qc.measure(q_m[0], cr[0])
        for i in range(4):
            qc.measure(q_a[i], cr[1 + i])
        for i in range(4):
            qc.measure(q_b[i], cr[5 + i])
        for i in range(4):
            qc.measure(q_r[i], cr[9 + i])
        qc.measure(q_cout[0], cr[13])
        for i in range(4):
            qc.measure(q_c[i], cr[14 + i])

    return qc


def simulate_optimized_4bit(m: int, a: int, b: int) -> Dict[str, Any]:
    """
    Simulate the optimized 4-bit adder-subtractor for (M, A, B) using AerSimulator.
    """
    qc = build_optimized_4bit_with_inputs(m, a, b, measure=True)
    sim = AerSimulator()
    result = sim.run(qc, shots=1).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    # Convert bitstring (reverse index because Qiskit orders right-to-left)
    measured = [int(bitstring[len(bitstring) - 1 - i]) for i in range(18)]

    meas_m = measured[0]
    meas_a = sum(measured[1 + i] << i for i in range(4))
    meas_b = sum(measured[5 + i] << i for i in range(4))
    meas_r = sum(measured[9 + i] << i for i in range(4))
    meas_cout = measured[13]
    meas_c = [measured[14 + i] for i in range(4)]

    if m == 0:
        expected_r = (a + b) % 16
        expected_cout = (a + b) // 16
        expected_borrow = 0
        borrow = 0
        is_arithmetic_correct = (meas_r == expected_r and meas_cout == expected_cout)
    else:
        expected_r = (a - b) % 16
        expected_borrow = 1 if a < b else 0
        expected_cout = 1 ^ expected_borrow
        borrow = 1 ^ meas_cout
        is_arithmetic_correct = (meas_r == expected_r and borrow == expected_borrow)

    inputs_preserved = (meas_m == m and meas_a == a and meas_b == b)
    ancillas_restored = all(c == 0 for c in meas_c)

    return {
        "mode": m,
        "input_a": a,
        "input_b": b,
        "output_r": meas_r,
        "output_cout": meas_cout,
        "borrow": borrow,
        "preserved_m": meas_m,
        "preserved_a": meas_a,
        "preserved_b": meas_b,
        "ancilla_carries": meas_c,
        "expected_r": expected_r,
        "expected_cout": expected_cout,
        "expected_borrow": expected_borrow,
        "inputs_preserved": inputs_preserved,
        "ancillas_restored": ancillas_restored,
        "is_correct": (is_arithmetic_correct and inputs_preserved and ancillas_restored)
    }

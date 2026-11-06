"""
Baseline Reversible 4-Bit Adder-Subtractor
==========================================

This module implements the Baseline Reversible 4-Bit Ripple-Carry
Adder-Subtractor with Bennett carry uncomputation.

Mathematical Formulation:
-------------------------
Inputs:
  M in {0, 1}: Mode (0 = Addition, 1 = Subtraction)
  A in [0, 15]: 4-bit unsigned integer (A3 A2 A1 A0)
  B in [0, 15]: 4-bit unsigned integer (B3 B2 B1 B0)

Operations:
  Addition (M = 0):
    R = (A + B) mod 16
    Cout = (A + B) // 16
    Borrow = 0

  Subtraction (M = 1):
    In two's complement logic: A - B = A + (~B) + 1
    Bitwise: B_eff[i] = B[i] ^ M
    Initial carry: C0 = M = 1
    R = (A - B) mod 16
    Borrow = 1 ^ Cout  (Borrow = 1 if A < B else 0)

Register Layout (18 qubits):
----------------------------
  q_m (1 qubit): Mode control M
  q_a (4 qubits): Input A [A0, A1, A2, A3]
  q_b (4 qubits): Input B [B0, B1, B2, B3]
  q_r (4 qubits): Result R [R0, R1, R2, R3] (Initialized to |0>)
  q_cout (1 qubit): Output Cout (Initialized to |0>)
  q_c (4 qubits): Intermediate carries C0, C1, C2, C3 (Ancillas restored to |0>)

Resource Metrics:
-----------------
  - Total Qubits: 18
  - Input Qubits: 9 (M, A, B) - 100% preserved
  - Output Qubits: 5 (R0..R3, Cout)
  - Ancilla Qubits: 4 (C0..C3) - 100% restored to |0>
  - Gate Count: 50 (36 CNOT, 14 Toffoli)
  - Circuit Depth: ~32
  - Quantum Cost (NCV model): 36*1 + 14*5 = 106
"""

from typing import Dict, Any, Tuple
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator


def build_baseline_4bit_adder_circuit() -> QuantumCircuit:
    """
    Construct the core 18-qubit Baseline 4-Bit Adder-Subtractor quantum circuit.
    """
    q_m = QuantumRegister(1, "m")
    q_a = QuantumRegister(4, "a")
    q_b = QuantumRegister(4, "b")
    q_r = QuantumRegister(4, "r")
    q_cout = QuantumRegister(1, "cout")
    q_c = QuantumRegister(4, "c")

    qc = QuantumCircuit(q_m, q_a, q_b, q_r, q_cout, q_c, name="Baseline_4Bit_AdderSubtractor")

    # Step 1: Mode conditioning on register B (Two's complement bit flip when M=1)
    for i in range(4):
        qc.cx(q_m[0], q_b[i])

    # Step 2: Inject initial carry C0 = M
    qc.cx(q_m[0], q_c[0])

    # Step 3: Forward Carry Ripple using baseline carry blocks
    for i in range(3):
        qc.ccx(q_a[i], q_b[i], q_c[i+1])
        qc.cx(q_a[i], q_b[i])
        qc.ccx(q_b[i], q_c[i], q_c[i+1])
        qc.cx(q_a[i], q_b[i])  # Immediate restoration of B[i]

    # Final carry into Cout
    qc.ccx(q_a[3], q_b[3], q_cout[0])
    qc.cx(q_a[3], q_b[3])
    qc.ccx(q_b[3], q_c[3], q_cout[0])
    qc.cx(q_a[3], q_b[3])  # Immediate restoration of B[3]

    # Step 4: Sum generation into register R
    for i in range(4):
        qc.cx(q_a[i], q_r[i])
        qc.cx(q_b[i], q_r[i])
        qc.cx(q_c[i], q_r[i])

    # Step 5: Bennett Uncomputation of intermediate carries C3, C2, C1
    for i in [2, 1, 0]:
        qc.cx(q_a[i], q_b[i])
        qc.ccx(q_b[i], q_c[i], q_c[i+1])
        qc.cx(q_a[i], q_b[i])
        qc.ccx(q_a[i], q_b[i], q_c[i+1])

    # Step 6: Uncompute C0
    qc.cx(q_m[0], q_c[0])

    # Step 7: Restore register B
    for i in range(4):
        qc.cx(q_m[0], q_b[i])

    return qc


def build_baseline_4bit_with_inputs(m: int, a: int, b: int, measure: bool = True) -> QuantumCircuit:
    """
    Construct Baseline 4-Bit Adder-Subtractor initialized with inputs M, A, B.
    """
    q_m = QuantumRegister(1, "m")
    q_a = QuantumRegister(4, "a")
    q_b = QuantumRegister(4, "b")
    q_r = QuantumRegister(4, "r")
    q_cout = QuantumRegister(1, "cout")
    q_c = QuantumRegister(4, "c")

    if measure:
        cr = ClassicalRegister(18, "meas")
        qc = QuantumCircuit(q_m, q_a, q_b, q_r, q_cout, q_c, cr, name=f"Baseline_4Bit_M{m}_A{a}_B{b}")
    else:
        qc = QuantumCircuit(q_m, q_a, q_b, q_r, q_cout, q_c, name=f"Baseline_4Bit_M{m}_A{a}_B{b}")

    # Prepare inputs
    if m:
        qc.x(q_m[0])
    for i in range(4):
        if (a >> i) & 1:
            qc.x(q_a[i])
        if (b >> i) & 1:
            qc.x(q_b[i])

    qc.barrier()
    core = build_baseline_4bit_adder_circuit()
    qc.compose(core, inplace=True)

    if measure:
        qc.barrier()
        # Measure in consistent sequential order:
        # cr[0]: M, cr[1..4]: A, cr[5..8]: B, cr[9..12]: R, cr[13]: Cout, cr[14..17]: C0..C3
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


def simulate_baseline_4bit(m: int, a: int, b: int) -> Dict[str, Any]:
    """
    Simulate the baseline 4-bit adder-subtractor for (M, A, B) using AerSimulator.
    """
    qc = build_baseline_4bit_with_inputs(m, a, b, measure=True)
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

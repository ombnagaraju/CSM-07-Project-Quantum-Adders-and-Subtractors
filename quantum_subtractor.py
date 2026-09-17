from qiskit import QuantumCircuit

# Get inputs from user
A = int(input("Enter A (0 or 1): "))
B = int(input("Enter B (0 or 1): "))

# Validate input
if A not in [0, 1] or B not in [0, 1]:
    print("Please enter only 0 or 1.")
else:
    # 3 qubits:
    # q0 = A
    # q1 = B
    # q2 = Borrow
    # 2 classical bits:
    # c0 = Difference
    # c1 = Borrow

    qc = QuantumCircuit(3, 2)

    # Set input A
    if A == 1:
        qc.x(0)

    # Set input B
    if B == 1:
        qc.x(1)

    # -------------------------
    # Calculate Borrow
    # Borrow = NOT(A) AND B
    # -------------------------

    qc.x(0)
    qc.ccx(0, 1, 2)
    qc.x(0)

    # -------------------------
    # Calculate Difference
    # Difference = A XOR B
    # -------------------------

    qc.cx(1, 0)

    # Measure
    qc.measure(0, 0)   # Difference
    qc.measure(2, 1)   # Borrow

    print("\nQuantum Half Subtractor:")
    print(qc)
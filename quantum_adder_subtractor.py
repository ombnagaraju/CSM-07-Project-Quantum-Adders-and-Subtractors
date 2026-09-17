from qiskit import QuantumCircuit

# 6 qubits and 2 classical bits
qc = QuantumCircuit(6, 2)

# q0 = A
# q1 = B
# q2 = Mode
# q3 = Temporary
# q4 = Result
# q5 = Carry/Borrow

# Example:
# A = 1
# B = 1
# Mode = 0 → Addition

qc.x(0)
qc.x(1)

# B' = B XOR Mode
qc.cx(1, 3)
qc.cx(2, 3)

# Result = A XOR B' XOR Mode
qc.cx(0, 4)
qc.cx(3, 4)
qc.cx(2, 4)

# Carry
qc.ccx(0, 3, 5)
qc.ccx(2, 0, 5)
qc.ccx(2, 3, 5)

# Measure result and carry/borrow
qc.measure(4, 0)
qc.measure(5, 1)

print(qc)
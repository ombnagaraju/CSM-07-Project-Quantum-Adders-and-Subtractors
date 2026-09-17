from qiskit import QuantumCircuit

# Create 3 qubits and 2 classical bits
qc = QuantumCircuit(3, 2)

# Input: A = 1, B = 1
qc.x(0)
qc.x(1)

# Full adder
qc.cx(0, 2)
qc.cx(1, 2)
qc.ccx(0, 1, 2)

# Measure
qc.measure(1, 0)
qc.measure(2, 1)

print(qc)

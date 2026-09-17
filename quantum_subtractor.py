from qiskit import QuantumCircuit

# Create 2 qubits and 2 classical bits
qc = QuantumCircuit(2, 2)

# Inputs: A = 1, B = 0
qc.x(0)

# Difference = A XOR B
qc.cx(1, 0)

# Measure
qc.measure(0, 0)
qc.measure(1, 1)

print(qc)

"""
Circuit Utilities Module
========================

Provides helper functions for circuit creation, gate breakdown,
quantum cost evaluation under the NCV model, basis state simulation,
and circuit diagram rendering.
"""

from typing import Dict, List, Tuple, Any
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt
from pathlib import Path


def calculate_quantum_cost(qc: QuantumCircuit, peres_as_macro: bool = False) -> int:
    """
    Calculate the quantum cost of a circuit under the standard NCV model.

    NCV Cost Model:
    - NOT (X): 1
    - CNOT (CX): 1
    - Controlled-V / Controlled-V†: 1
    - Toffoli (CCX): 5 (decomposed into 2 CX + 1 V + 2 V†)
    - Peres gate: 4 (if recognized as a composite macro; otherwise CCX(5) + CX(1) = 6)
    """
    op_counts = qc.count_ops()
    cost = 0
    for op, count in op_counts.items():
        if op in ("x", "not"):
            cost += count * 1
        elif op in ("cx", "cnot"):
            cost += count * 1
        elif op in ("ccx", "toffoli"):
            cost += count * 5
        elif op == "peres":
            cost += count * (4 if peres_as_macro else 6)
        elif op in ("v", "v_dag", "ch", "h", "s", "sdg", "t", "tdg"):
            cost += count * 1
        elif op in ("swap",):
            cost += count * 3
        elif op in ("barrier", "measure"):
            continue
        else:
            cost += count * 1
    return cost


def get_circuit_resources(qc: QuantumCircuit) -> Dict[str, Any]:
    """
    Extract comprehensive architectural metrics from a QuantumCircuit.
    """
    ops = dict(qc.count_ops())
    # Filter out non-computational operations
    pure_ops = {k: v for k, v in ops.items() if k not in ("barrier", "measure")}
    total_gates = sum(pure_ops.values())
    depth = qc.depth()
    num_qubits = qc.num_qubits
    q_cost = calculate_quantum_cost(qc)

    return {
        "num_qubits": num_qubits,
        "total_gates": total_gates,
        "circuit_depth": depth,
        "quantum_cost": q_cost,
        "ops": pure_ops,
        "cnot_count": pure_ops.get("cx", 0),
        "toffoli_count": pure_ops.get("ccx", 0),
        "x_count": pure_ops.get("x", 0)
    }


def simulate_circuit_basis(qc: QuantumCircuit, shots: int = 1) -> str:
    """
    Execute a basis-state circuit using AerSimulator and return the resulting bitstring.
    """
    sim = AerSimulator()
    # Add measurement if missing
    if qc.num_clbits == 0:
        meas_qc = qc.copy()
        meas_qc.measure_all()
    else:
        meas_qc = qc
    result = sim.run(meas_qc, shots=shots).result()
    counts = result.get_counts()
    # Most frequent or unique deterministic bitstring
    bitstring = max(counts, key=counts.get)
    return bitstring


def export_circuit_diagram(qc: QuantumCircuit, output_path: Path, style: str = "mpl") -> None:
    """
    Export circuit diagram to file using matplotlib or text representation.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig = qc.draw(output="mpl", fold=40)
        fig.savefig(str(output_path), bbox_inches="tight", dpi=300)
        plt.close(fig)
    except Exception:
        # Fallback to text drawing
        text_drawing = qc.draw(output="text")
        with open(output_path.with_suffix(".txt"), "w", encoding="utf-8") as f:
            f.write(str(text_drawing))

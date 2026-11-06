"""Circuit A - baseline Toffoli-CNOT reversible full adder.

Equations:

    Sum  = A XOR B XOR Cin
    Cout = A.B XOR A.Cin XOR B.Cin  =  A.B XOR (A XOR B).Cin

The propagate term A XOR B is written into an ancilla line so that all three
inputs survive the circuit; that ancilla is then left holding A XOR B, i.e. it
is one garbage output. This is the reference design every later claim is
measured against.
"""

from __future__ import annotations

from circuits import circuit_utils as cu

QUBIT_MAP = {"A": 0, "B": 1, "Cin": 2, "Prop": 3, "Sum": 4, "Cout": 5}


def build_baseline_fulladder() -> cu.CircuitSpec:
    m = QUBIT_MAP
    ops = [
        cu.cx(m["A"], m["Prop"]),                    # Prop = A
        cu.cx(m["B"], m["Prop"]),                    # Prop = A XOR B
        cu.ccx(m["A"], m["B"], m["Cout"]),           # Cout = A.B
        cu.ccx(m["Prop"], m["Cin"], m["Cout"]),      # Cout = A.B + (A+B).Cin
        cu.cx(m["Prop"], m["Sum"]),                  # Sum = A XOR B
        cu.cx(m["Cin"], m["Sum"]),                   # Sum = A XOR B XOR Cin
    ]
    return cu.CircuitSpec(
        name="baseline_fulladder",
        ops=ops,
        n_qubits=6,
        registers={"A": [0], "B": [1], "Cin": [2], "Prop": [3], "Sum": [4], "Cout": [5]},
        inputs=("A", "B", "Cin"),
        outputs=("Sum", "Cout"),
        ancillas=("Prop", "Sum", "Cout"),
        garbage=("Prop",),
        notes=("Three Toffoli plus four CNOT. A, B and Cin keep their original "
               "values; Prop is left as A XOR B and is therefore garbage."),
    )


def expected(a: int, b: int, cin: int) -> tuple[int, int]:
    """Ideal (Sum, Cout) for one input triple."""
    total = a + b + cin
    return total & 1, total >> 1


def truth_table() -> list:
    return [(a, b, c, *expected(a, b, c))
            for a in (0, 1) for b in (0, 1) for c in (0, 1)]

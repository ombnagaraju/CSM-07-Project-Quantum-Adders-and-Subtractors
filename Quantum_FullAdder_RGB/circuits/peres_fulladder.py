"""Circuit B - Peres-gate-based reversible full adder.

Derivation, using P(x, y, z) = (x, x XOR y, x.y XOR z):

1. P(A, B, AB) with AB = |0>       ->  A, A XOR B, A.B
2. P(A XOR B, Cin, Cout) with Cout = |0>
                                   ->  A XOR B, (A XOR B) XOR Cin = Sum,
                                       (A XOR B).Cin
3. CX(AB -> Cout)                  ->  Cout = A.B XOR (A XOR B).Cin

So the Cin line ends as Sum and no CNOT-only carry chain is needed. The
construction needs two Peres blocks and one CNOT, but it leaves two garbage
lines (B holding A XOR B, and AB holding A.B) because neither is restored here.
"""

from __future__ import annotations

from circuits import circuit_utils as cu

QUBIT_MAP = {"A": 0, "B": 1, "Cin": 2, "AB": 3, "Cout": 4}


def build_peres_fulladder() -> cu.CircuitSpec:
    m = QUBIT_MAP
    ops = [
        cu.peres(m["A"], m["B"], m["AB"]),     # B = A XOR B, AB = A.B
        cu.peres(m["B"], m["Cin"], m["Cout"]), # Cin = Sum, Cout = (A XOR B).Cin
        cu.cx(m["AB"], m["Cout"]),             # Cout = A.B XOR (A XOR B).Cin
    ]
    return cu.CircuitSpec(
        name="peres_fulladder",
        ops=ops,
        n_qubits=5,
        registers={"A": [0], "B": [1], "Cin": [2], "AB": [3], "Sum": [2], "Cout": [4]},
        inputs=("A", "B", "Cin"),
        outputs=("Sum", "Cout"),
        ancillas=("AB", "Cout"),
        garbage=("B", "AB"),
        notes=("Two Peres blocks plus one CNOT. Sum is produced on the Cin line, "
               "so Cin is consumed rather than preserved; B and AB are garbage."),
    )


def expected(a: int, b: int, cin: int) -> tuple[int, int]:
    total = a + b + cin
    return total & 1, total >> 1


def truth_table() -> list:
    return [(a, b, c, *expected(a, b, c))
            for a in (0, 1) for b in (0, 1) for c in (0, 1)]

"""Circuit C - optimized reversible full adder (selected design).

The trick is to reuse the propagate ancilla instead of paying for a separate
sum line and a separate restore pass:

1. CX(A -> P)                       P = A
2. CX(B -> P)                       P = A XOR B
3. CCX(A, B -> Cout)                Cout = A.B
4. CCX(P, Cin -> Cout)              Cout = A.B XOR (A XOR B).Cin
5. CX(Cin -> P)                     P  = A XOR B XOR Cin = Sum

Line P finishes as the Sum output, so nothing is left over: the design has
zero garbage, keeps all three inputs intact and uses one qubit less than the
Peres construction of circuit B. Costs (NCV-L, Toffoli = 5, CNOT = 1):

    baseline  14   6 gates   6 qubits   1 garbage
    Peres      9   3 gates   5 qubits   2 garbage   (cheapest, least clean)
    optimized 13   5 gates   5 qubits   0 garbage   (selected)

Selection rule used here: strictly fewer gate blocks AND strictly lower quantum
cost AND no garbage than the baseline, all measured by
verification/verify_fulladder.py rather than asserted.
"""

from __future__ import annotations

from circuits import baseline_fulladder
from circuits import circuit_utils as cu

QUBIT_MAP = {"A": 0, "B": 1, "Cin": 2, "Sum": 3, "Cout": 4}


def build_optimized_fulladder() -> cu.CircuitSpec:
    m = QUBIT_MAP
    ops = [
        cu.cx(m["A"], m["Sum"]),
        cu.cx(m["B"], m["Sum"]),
        cu.ccx(m["A"], m["B"], m["Cout"]),
        cu.ccx(m["Sum"], m["Cin"], m["Cout"]),
        cu.cx(m["Cin"], m["Sum"]),
    ]
    return cu.CircuitSpec(
        name="optimized_fulladder",
        ops=ops,
        n_qubits=5,
        registers={"A": [0], "B": [1], "Cin": [2], "Sum": [3], "Cout": [4]},
        inputs=("A", "B", "Cin"),
        outputs=("Sum", "Cout"),
        ancillas=("Sum", "Cout"),
        garbage=(),
        notes=("Two Toffoli plus three CNOT. The propagate ancilla becomes the "
               "Sum line, so A, B and Cin all keep their input values and no "
               "line is left holding intermediate information."),
    )


def build_optimized_fulladder_no_sum_reuse() -> cu.CircuitSpec:
    """The same design with the last CNOT removed, i.e. before uncomputation.

    Without step 5 the propagate line keeps A XOR B instead of the Sum, so it
    becomes garbage and the Sum is not available as a quantum output at all.
    This is the pair used to measure what the uncomputation step buys.
    """
    m = QUBIT_MAP
    ops = [
        cu.cx(m["A"], m["Sum"]),
        cu.cx(m["B"], m["Sum"]),
        cu.ccx(m["A"], m["B"], m["Cout"]),
        cu.ccx(m["Sum"], m["Cin"], m["Cout"]),
    ]
    return cu.CircuitSpec(
        name="optimized_fulladder_pre_uncompute",
        ops=ops,
        n_qubits=5,
        registers={"A": [0], "B": [1], "Cin": [2], "Sum": [3], "Cout": [4]},
        inputs=("A", "B", "Cin"),
        outputs=("Cout",),
        ancillas=("Sum", "Cout"),
        garbage=("Sum",),
        notes=("Four gates, one garbage line: the Sum still sits on the "
               "propagate line XOR-ed with Cin and cannot be read directly."),
    )


def expected(a: int, b: int, cin: int) -> tuple[int, int]:
    return baseline_fulladder.expected(a, b, cin)


def truth_table() -> list:
    return baseline_fulladder.truth_table()

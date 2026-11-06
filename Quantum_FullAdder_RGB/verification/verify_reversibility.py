"""Reversibility verification: permutation, inverse round-trip and unitarity.

Three independent arguments are recorded per design in
results/csv/reversibility_verification.csv:

1. ``bijection``           the op list maps the tested states one-to-one.
2. ``inverse_roundtrip``   running the design and then its exact inverse
   restores every state, which is the constructive proof of reversibility.
3. ``unitary_permutation`` the Qiskit circuit operator is a permutation
   matrix, so no amplitude leaks off the computational basis.

Checks 1 and 2 enumerate the whole space up to MAX_EXHAUSTIVE_STATES and fall
back to a seeded random sample above it; the sampled rows say so in ``detail``
and verify_4bit.py covers the arithmetic subspace exhaustively anyway.
"""

from __future__ import annotations

import sys

import numpy as np

import config
from circuits import (
    alu_slice_2bit,
    baseline_fulladder,
    optimized_fulladder,
    parametrized_nbit_adder,
    peres_fulladder,
    uncomputation,
)
from circuits import circuit_utils as cu
from verification import nbit_designs

MAX_EXHAUSTIVE_STATES = 1 << 20
OPERATOR_QUBIT_LIMIT = 12
SAMPLED_STATES = 1 << 12


def all_designs(width: int = 4) -> dict:
    designs = {
        "baseline_fulladder": baseline_fulladder.build_baseline_fulladder(),
        "peres_fulladder": peres_fulladder.build_peres_fulladder(),
        "optimized_fulladder": optimized_fulladder.build_optimized_fulladder(),
        "peres_structural_uncompute": uncomputation.build_peres_with_structural_uncomputation(),
    }
    designs.update(nbit_designs(width))
    designs["baseline_dual_control_mux"] = parametrized_nbit_adder.build_nbit_design(
        width, "baseline", "dual_mux")
    designs["alu_slice_2bit"] = alu_slice_2bit.build_alu_slice_2bit()
    return designs


def unitary_is_permutation(spec: cu.CircuitSpec):
    """(True/False/None, detail): None means the check does not apply."""
    from qiskit.quantum_info import Operator

    if any(op[0] in ("measure", "cond_x", "reset") for op in spec.all_ops()):
        return None, "design uses measurement or reset, no unitary operator"
    if spec.n_qubits > OPERATOR_QUBIT_LIMIT:
        return None, f"{spec.n_qubits} qubits exceeds the dense-operator budget"
    matrix = Operator(spec.build(measure=False)).data
    occupied = abs(matrix) > 0.5
    per_column = occupied.sum(axis=0).tolist()
    per_row = occupied.sum(axis=1).tolist()
    if per_column != [1] * matrix.shape[1] or per_row != [1] * matrix.shape[0]:
        return False, "operator has a row or column without exactly one entry"
    return True, "operator is a permutation matrix"


def verify(write: bool = True, designs: dict | None = None) -> list[dict]:
    rows: list[dict] = []
    failures: list[str] = []
    for label, spec in (designs or all_designs()).items():
        lines = list(range(spec.n_qubits))
        states = 1 << spec.n_qubits
        exhaustive = states <= MAX_EXHAUSTIVE_STATES
        if exhaustive:
            values = np.arange(states, dtype=np.int64)
            scope = f"all {states} states"
        else:
            rng = np.random.default_rng(config.GLOBAL_SEED)
            values = rng.choice(states, size=SAMPLED_STATES, replace=False)
            scope = f"{SAMPLED_STATES} seeded random states of {states}"

        for name in ("bijection", "inverse_roundtrip", "unitary_permutation"):
            tested = len(values)
            if name == "unitary_permutation":
                ok, detail = unitary_is_permutation(spec)
                tested = len(values) if ok is not None else 0
            elif name == "bijection":
                ok, distinct = cu.is_bijective(spec, lines, values)
                detail = f"{distinct}/{len(values)} distinct output states ({scope})"
            else:
                try:
                    ok, restored, tested = cu.roundtrip_is_identity(spec, lines, values)
                    detail = f"inverse restored {restored}/{tested} states ({scope})"
                except ValueError as error:
                    ok, detail = None, str(error)

            result = {True: "pass", False: "fail", None: "skipped"}[ok]
            rows.append({"circuit": label, "check": name, "qubits": spec.n_qubits,
                         "states_tested": 0 if result == "skipped" else tested,
                         "result": result, "detail": detail})
            if result == "fail":
                failures.append(f"{label}: {name} - {detail}")

    if write and rows:
        config.write_rows(rows, "reversibility_verification")
    if failures:
        raise AssertionError(f"reversibility verification failed: {failures}")
    return rows


def summary(rows: list[dict]) -> dict:
    return {name: sum(1 for r in rows if r["check"] == name and r["result"] == "pass")
            for name in ("bijection", "inverse_roundtrip", "unitary_permutation")}


if __name__ == "__main__":
    config.ensure_directories()
    table = verify()
    for row in table:
        print(f"{row['circuit']:32s} {row['check']:20s} {row['result']:8s} {row['detail']}")
    print(f"\npassed: {summary(table)}")
    print(f"wrote {len(table)} rows to {config.csv_path('reversibility_verification')}")
    sys.exit(0)

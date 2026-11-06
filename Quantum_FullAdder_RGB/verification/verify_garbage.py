"""Contribution 6 verification: garbage reduction, its cost, and its price.

Writes results/csv/garbage_uncompute.csv. For every design, and for the
measurement-based uncomputation variants of that design, four things are
measured:

1. Resources. Gates, quantum cost, depth, ancilla and garbage qubits, plus the
   delta and delta percentage against the same design without uncomputation.
2. Arithmetic on basis states. The uncomputed variant must give exactly the
   same output-register answers as the original on every input combination. The
   op-list simulator treats a Z measurement followed by a conditional X, or an
   equivalent reset, as clearing the line, so this is a flat exhaustive check.
3. Answer statistics under superposition. With the inputs in superposition, the
   density matrix on the answer lines (every other line traced out) is compared
   between the coherent design and its measured variant. The maximum element
   difference is zero: clearing a garbage line cannot change the statistics of
   the answer, because a local operation on a traced subsystem is trace
   preserving.
4. The price. The same superposition probe, but the design is followed by the
   exact inverse of its gate list and the input Hadamards again. A coherent
   design returns |0...0> with probability 1, so the computation is undone. A
   measured variant cannot undo a collapse: its return probability drops and the
   state is mixed (purity below 1). That is the coherence penalty of
   measurement-based uncomputation as a number, not a claim.

The probe needs a 4^qubit density matrix, so it runs on designs up to
PROBE_QUBIT_LIMIT qubits; wider designs report resources and arithmetic and say
why the coherence columns are blank.
"""

from __future__ import annotations

import sys

import numpy as np

import config
from circuits import circuit_utils as cu
from circuits.uncomputation import garbage_lines, measurement_based_uncompute
from verification import garbage_designs

PROBE_QUBIT_LIMIT = 8
METRIC_COLUMNS = ("garbage_qubits", "ancilla_qubits", "total_gates", "quantum_cost",
                  "logical_depth")


def cases_for(spec: cu.CircuitSpec) -> list[dict]:
    """Every basis-state setting of the design's operands."""
    if "Cin" in spec.registers:
        return [{"A": a, "B": b, "Cin": c}
                for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    size = 1 << len(spec.registers["A"])
    shared = "M" in spec.registers
    out = []
    for a in range(size):
        for b in range(size):
            for mode in ((0, 1) if shared else (0,)):
                entry = {"A": a, "B": b}
                if shared:
                    entry["M"] = mode
                out.append(entry)
    return out


def answers_match(variant: cu.CircuitSpec, reference: cu.CircuitSpec) -> dict:
    """Same output answers as the un-uncomputed design, on every case.

    Only the declared output registers are compared: clearing the garbage lines
    is the point of the variant, so a difference there is the intended effect
    rather than a regression.
    """
    cases = cases_for(reference)
    names = list(reference.outputs)
    mine = [{k: v[k] for k in names} for v in cu.op_list_results(variant, cases)]
    theirs = [{k: v[k] for k in names} for v in cu.op_list_results(reference, cases)]
    mismatch_index = [i for i, (a, b) in enumerate(zip(mine, theirs)) if a != b]
    return {"cases": len(cases),
            "answer_mismatches_vs_before": len(mismatch_index),
            "compared_registers": names,
            "first_mismatch_case_index": mismatch_index[:1]}


def clearing_ops(variant: cu.CircuitSpec, base: cu.CircuitSpec) -> list:
    """The tail the uncomputation added: measure / conditional-X / reset ops."""
    return list(variant.ops[len(base.ops):])


def _density_matrix_friendly(ops) -> list:
    """Measure-then-conditional-X is the same channel as reset on that line, and
    reset is the form qiskit.quantum_info can evolve without control flow."""
    out = []
    for op in ops:
        if op[0] == "measure":
            continue
        out.append(("reset", op[1]) if op[0] == "cond_x" else op)
    return out


def _probe_circuit(base: cu.CircuitSpec, clearing: list, undo: bool):
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(base.n_qubits, name=f"probe_{base.name}")
    input_lines = sorted(set(base.flat(*base.inputs)))
    forward = base.all_ops()
    for qubit in input_lines:
        qc.h(qubit)
    cu.emit(qc, forward)
    cu.emit(qc, _density_matrix_friendly(clearing))
    if undo:
        # Exactly what a real run would execute afterwards: the inverse of the
        # arithmetic, with the collapse already in the middle of the sequence.
        cu.emit(qc, cu.inverse_ops(forward))
        for qubit in input_lines:
            qc.h(qubit)
    return qc


def superposition_probe(base: cu.CircuitSpec, clearing: list) -> dict:
    """Answer statistics and reversibility of the design under superposition."""
    from qiskit.quantum_info import DensityMatrix, partial_trace

    if base.n_qubits > PROBE_QUBIT_LIMIT:
        return {"probe_qubits": base.n_qubits, "purity": "", "roundtrip_probability": "",
                "answer_statistics_difference": "",
                "probe_note": f"{base.n_qubits} qubits exceeds the "
                              f"{PROBE_QUBIT_LIMIT}-qubit density-matrix probe limit"}

    answer_lines = set(base.flat(*base.outputs))
    traced = [q for q in range(base.n_qubits) if q not in answer_lines]

    def reduced_answers(ops_clearing) -> np.ndarray:
        state = DensityMatrix(_probe_circuit(base, ops_clearing, undo=False))
        return partial_trace(state, traced).data

    difference = float(np.abs(reduced_answers([]) - reduced_answers(clearing)).max())

    rho = DensityMatrix(_probe_circuit(base, clearing, undo=True)).data
    return {
        "probe_qubits": base.n_qubits,
        "purity": float(np.real(np.trace(rho @ rho))),
        "roundtrip_probability": float(np.real(rho[0, 0])),
        "answer_statistics_difference": difference,
        "probe_note": "",
    }


def empty_probe(note: str) -> dict:
    return {"probe_qubits": "", "purity": "", "roundtrip_probability": "",
            "answer_statistics_difference": "", "probe_note": note}


def verify(write: bool = True, confirm_coherence: bool = True) -> list[dict]:
    rows: list[dict] = []
    failures: list[str] = []

    for label, spec in garbage_designs().items():
        before = cu.spec_metrics(spec)
        dirty = garbage_lines(spec)
        variants = [("none", spec, [])]
        if dirty:
            for method in ("conditional", "reset"):
                variant = measurement_based_uncompute(spec, method)
                variants.append((f"measurement_based_{method}", variant,
                                 clearing_ops(variant, spec)))

        for method, variant, clearing in variants:
            metrics = cu.spec_metrics(variant)
            row = {"design": label, "method": method, "garbage_lines_before": dirty}
            row.update({key: metrics[key] for key in (
                "qubits", "ancilla_qubits", "garbage_qubits", "total_gates", "x_gates",
                "cx_gates", "ccx_gates", "peres_gates", "measure_ops", "cond_x_ops",
                "reset_ops", "quantum_cost", "logical_depth")})
            for metric in METRIC_COLUMNS:
                delta = row[metric] - before[metric]
                row[f"{metric}_delta"] = delta
                row[f"{metric}_delta_percent"] = (
                    round(delta / before[metric] * 100.0, 2) if before[metric] else 0.0)

            if method == "none":
                row["cases"] = ""
                row["answer_mismatches_vs_before"] = ""
                row["compared_registers"] = ""
                row["first_mismatch_case_index"] = ""
            else:
                row.update(answers_match(variant, spec))
                if row["answer_mismatches_vs_before"]:
                    failures.append(f"{label}/{method} changed "
                                    f"{row['answer_mismatches_vs_before']} case answers")

            row.update(empty_probe("coherence probe disabled") if not confirm_coherence
                       else superposition_probe(spec, clearing))

            difference = row["answer_statistics_difference"]
            probability = row["roundtrip_probability"]
            row["answer_pass"] = row["answer_mismatches_vs_before"] in (0, "")
            row["statistics_pass"] = difference == "" or abs(float(difference)) < 1e-9
            # Only a coherent design is expected to be perfectly undoable; for a
            # measured variant the drop is the result being reported.
            row["undoable"] = probability != "" and abs(float(probability) - 1.0) < 1e-9
            row["garbage_removed"] = row["garbage_qubits"] == 0
            row["pass"] = bool(row["answer_pass"] and row["statistics_pass"])
            if method == "none" and probability != "" and not row["undoable"]:
                failures.append(f"{label} is not undoable under superposition: "
                                f"P(0)={probability}")
            if not row["statistics_pass"]:
                failures.append(f"{label}/{method} changed the answer statistics: "
                                f"max difference {difference}")
            rows.append(row)

    if write and rows:
        config.write_rows(rows, "garbage_uncompute")
    if failures:
        raise AssertionError(f"garbage/uncomputation verification failed: {failures[:5]}")
    return rows


def summary(rows: list[dict]) -> str:
    def number(value) -> str:
        return "  n/a" if value == "" else f"{float(value):6.4f}"

    out = []
    for row in rows:
        probe = ("" if row["roundtrip_probability"] == "" and row["purity"] == "" else
                 f" | P(undo)={number(row['roundtrip_probability'])}"
                 f" purity={number(row['purity'])}"
                 f" d_answers={number(row['answer_statistics_difference'])}")
        out.append(f"{row['design']:34s} {row['method']:26s} "
                   f"garbage={row['garbage_qubits']:>2}"
                   f"(d={row['garbage_qubits_delta']:>+3}) "
                   f"gates={row['total_gates']:>3} cost={row['quantum_cost']:>3}"
                   f"{probe} {row['probe_note']}")
    return "\n".join(out)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    print(f"\nwrote {len(result)} rows to {config.csv_path('garbage_uncompute')}")
    sys.exit(0)

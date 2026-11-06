"""Contribution 10 verification: the two-bit ALU slice.

Writes two result files:

``results/csv/alu_slice_cost.csv``
    Resources of the slice with and without the select-decode uncomputation, so
    the garbage cost of keeping the one-hot decode lines is visible as a number.

``results/csv/alu_verification.csv``
    One row per (variant, A, B, select code). The arithmetic and logic results
    are checked three ways: against the closed-form expectation, against the
    Qiskit Aer simulator, and - for the two operation codes that the slice
    shares with the adder-subtractor - against the standalone 2-bit reversible
    adder/subtractor built by circuits.parametrized_nbit_adder. An ALU is only
    worth reporting if its arithmetic channel is the same circuit that already
    passed the 512-case study at the corresponding width.

The slice needs 23 qubits, so the Aer confirmation runs on the matrix product
state method instead of a dense statevector.
"""

from __future__ import annotations

import sys

import config
from circuits import alu_slice_2bit
from circuits import circuit_utils as cu
from circuits.parametrized_nbit_adder import build_nbit_design
from verification import check_case, run_both

AER_CHUNK = 32
AER_METHOD = "matrix_product_state"


def designs() -> dict:
    return {
        "alu_slice_2bit_uncomputed": alu_slice_2bit.build_alu_slice_2bit(True),
        "alu_slice_2bit_dirty_decode": alu_slice_2bit.build_alu_slice_2bit(False),
    }


def arithmetic_reference(width: int = 2) -> dict:
    """The 2-bit adder-subtractor the ALU's arithmetic codes must agree with."""
    return {mode: build_nbit_design(width, "optimized", mode,
                                    name=f"optimized_{mode}_{width}bit_alu_ref")
            for mode in ("add", "subtract")}


def cost_rows() -> list[dict]:
    """Resource comparison of the decode-uncomputation choice."""
    rows = []
    reference = None
    for label, spec in designs().items():
        metrics = cu.spec_metrics(spec)
        metrics.pop("circuit")
        row = {"circuit": label, "uncompute_decode": "dirty" not in label}
        row.update(metrics)
        row["garbage_lines"] = ",".join(spec.garbage)
        if reference is None:
            reference = row
            for metric in ("total_gates", "quantum_cost", "logical_depth",
                           "garbage_qubits", "ancilla_qubits"):
                row[f"{metric}_delta"] = 0
                row[f"{metric}_delta_percent"] = 0.0
        else:
            for metric in ("total_gates", "quantum_cost", "logical_depth",
                           "garbage_qubits", "ancilla_qubits"):
                delta = row[metric] - reference[metric]
                row[f"{metric}_delta"] = delta
                row[f"{metric}_delta_percent"] = (
                    round(delta / reference[metric] * 100.0, 2)
                    if reference[metric] else 0.0)
        rows.append(row)
    return rows


def verify(width: int = 2, confirm_aer: bool = True, write: bool = True) -> list[dict]:
    rows: list[dict] = []
    failures: list[str] = []
    references = arithmetic_reference(width)

    for label, spec in designs().items():
        cases_values = alu_slice_2bit.cases_values()
        fast, aer, agree = run_both(spec, cases_values, confirm_aer=confirm_aer,
                                    chunk=AER_CHUNK, method=AER_METHOD)
        for index, (a, b, code) in enumerate(alu_slice_2bit.all_cases()):
            expect = alu_slice_2bit.expected(a, b, code)
            for engine, measured in (("op_list", fast[index]), ("aer", aer[index])):
                checks = check_case(spec, cases_values[index], measured)
                ok = int(measured["R"]) == expect
                # The two logic codes have no carry semantics; the arithmetic
                # codes must reproduce the standalone 2-bit unit exactly.
                cross = ""
                if code in (0, 1):
                    unit = references["add" if code == 0 else "subtract"]
                    unit_result = cu.op_list_results(
                        unit, [{"A": a, "B": b}])[0]
                    cross = int(measured["Cout"]) == int(unit_result["Cout"])
                    ok = ok and cross
                rows.append({
                    "circuit": label,
                    "engine": engine,
                    "A": a, "B": b, "select_code": code,
                    "operation": alu_slice_2bit.OPERATIONS[code],
                    "expected_result": expect,
                    "measured_result": int(measured["R"]),
                    "measured_carry": int(measured["Cout"]),
                    "matches_adder_subtractor": cross if cross != "" else "",
                    "inputs_preserved": bool(checks["inputs_preserved"]),
                    "ancilla_restored": bool(checks["ancilla_restored"]),
                    "pass": bool(ok and agree),
                })
                if not ok:
                    failures.append(f"{label}/{engine} A={a} B={b} code={code} "
                                    f"got={measured['R']} want={expect} "
                                    f"carry_match={cross}")
        if not agree:
            failures.append(f"{label}: op list and Aer disagree")

    if write:
        if rows:
            config.write_rows(rows, "alu_verification")
        config.write_rows(cost_rows(), "alu_slice_cost")
    if failures:
        raise AssertionError(f"ALU slice verification failed: {failures[:6]}")
    return rows


def summary(rows: list[dict]) -> str:
    out = []
    for label in sorted({r["circuit"] for r in rows}):
        subset = [r for r in rows if r["circuit"] == label]
        out.append(f"{label:30s} rows={len(subset):3d} pass={sum(bool(r['pass']) for r in subset):3d} "
                   f"inputs_preserved={sum(bool(r['inputs_preserved']) for r in subset):3d} "
                   f"ancilla_restored={sum(bool(r['ancilla_restored']) for r in subset):3d}")
    return "\n".join(out)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    for row in config.read_rows("alu_slice_cost"):
        print(f"{row['circuit']:30s} qubits={row['qubits']:>3} gates={row['total_gates']:>4} "
              f"cost={row['quantum_cost']:>5} depth={row['logical_depth']:>3} "
              f"garbage={row['garbage_qubits']} ({row['garbage_lines']})")
    print(f"\nwrote {len(result)} rows to {config.csv_path('alu_verification')}")
    sys.exit(0)

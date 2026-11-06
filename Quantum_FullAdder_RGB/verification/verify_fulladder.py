"""Exhaustive 1-bit full-adder verification: all eight input combinations.

Writes results/csv/fulladder_verification.csv. Every design is checked three
ways for each case: the arithmetic expectation, the exact reversible op list,
and the Qiskit Aer simulator. `verify()` raises when anything disagrees, so a
broken circuit fails both this module and pytest rather than producing a CSV.
"""

from __future__ import annotations

import sys

import config
from circuits import baseline_fulladder
from verification import check_case, one_bit_designs, run_both


def verify(designs: dict | None = None, write: bool = True) -> list[dict]:
    designs = designs or one_bit_designs()
    truth = baseline_fulladder.truth_table()
    rows: list[dict] = []
    failures: list[str] = []

    for label, spec in designs.items():
        cases_values = [{"A": a, "B": b, "Cin": c} for a, b, c, *_ in truth]
        fast, aer, agree = run_both(spec, cases_values)
        for index, (a, b, c, sum_expect, cout_expect) in enumerate(truth):
            values = cases_values[index]
            for engine, measured in (("op_list", fast[index]), ("aer", aer[index])):
                checks = check_case(spec, values, measured)
                ok = (int(measured["Sum"]) == sum_expect
                      and int(measured["Cout"]) == cout_expect)
                row = {
                    "circuit": label,
                    "engine": engine,
                    "A": a, "B": b, "Cin": c,
                    "expected_sum": sum_expect,
                    "expected_cout": cout_expect,
                    "measured_sum": int(measured["Sum"]),
                    "measured_cout": int(measured["Cout"]),
                    "arithmetic_pass": bool(ok),
                    "inputs_preserved": bool(checks["inputs_preserved"]),
                    "preserved_detail": str(checks["preserved_detail"]),
                    "ancilla_restored": bool(checks["ancilla_restored"]),
                    "pass": bool(ok and agree),
                }
                rows.append(row)
                if not ok:
                    failures.append(f"{label}/{engine} A={a} B={b} Cin={c}")
        if not agree:
            failures.append(f"{label}: op list and Aer disagree")

    if write and rows:
        config.write_rows(rows, "fulladder_verification")
    if failures:
        raise AssertionError(f"full-adder verification failed: {failures[:8]}")
    return rows


def summary(rows: list[dict]) -> str:
    lines = []
    for label in sorted({r["circuit"] for r in rows}):
        subset = [r for r in rows if r["circuit"] == label]
        n = len(subset)
        lines.append(
            f"{label:36s} cases={n:2d} arithmetic_ok={sum(r['arithmetic_pass'] for r in subset)}/{n} "
            f"inputs_preserved={sum(r['inputs_preserved'] for r in subset)}/{n} "
            f"ancilla_restored={sum(r['ancilla_restored'] for r in subset)}/{n}")
    return "\n".join(lines)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    print(f"\nwrote {len(result)} rows to {config.csv_path('fulladder_verification')}")
    sys.exit(0)

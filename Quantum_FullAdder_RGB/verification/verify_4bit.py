"""Exhaustive 4-bit adder-subtractor verification: 16 x 16 x 2 = 512 cases.

Writes results/csv/four_bit_verification.csv with one row per (design, case).
The op-list result and the Qiskit Aer result are both required to match the
arithmetic expectation, including the documented carry/borrow convention:
Cout = 1 for subtraction means A >= B, so the borrow is NOT Cout.
"""

from __future__ import annotations

import sys

import config
from circuits import baseline_4bit_adder
from circuits import circuit_utils as cu
from verification import check_case, expected_arithmetic, nbit_designs, run_both

WIDTH = 4


def case_set(width: int = WIDTH, limit: int | None = None) -> list:
    """The (A, B, mode) triples to test; `limit` samples evenly for quick runs."""
    cases = baseline_4bit_adder.all_cases(width)
    if limit is None or limit >= len(cases):
        return cases
    stride = len(cases) / limit
    return [cases[int(i * stride)] for i in range(limit)]


def build_cases_values(spec: cu.CircuitSpec, cases: list, mode_filter: int | None = None) -> list:
    """Register-value dicts for the cases this design is meant to handle.

    Designs are driven by one shared mode line (`M`) or by a pair of one-hot
    select lines (`S_add`/`S_sub`); both are filled in from the mode of the case
    so a caller can hand the same (A, B, mode) triples to any design.
    """
    values = []
    for a, b, mode in cases:
        if mode_filter is not None and mode != mode_filter:
            continue
        entry = {"A": a, "B": b}
        if "M" in spec.registers:
            entry["M"] = mode
        if "S_add" in spec.registers:
            entry["S_add"], entry["S_sub"] = 1 - mode, mode
        values.append(entry)
    return values


def verify(width: int = WIDTH, confirm_aer: bool = True, limit: int | None = None,
           write: bool = True) -> list[dict]:
    designs = nbit_designs(width)
    universe = case_set(width, limit)
    rows: list[dict] = []
    failures: list[str] = []

    for label, spec in designs.items():
        # The label tells us which operation the unit implements; the shared
        # control design has to be tested on both.
        if label.endswith("_adder"):
            mode_filter: int | None = 0
        elif label.endswith("_subtractor"):
            mode_filter = 1
        else:
            mode_filter = None
        cases = [c for c in universe if mode_filter is None or c[2] == mode_filter]
        cases_values = build_cases_values(spec, cases, mode_filter)
        fast, aer, agree = run_both(spec, cases_values, confirm_aer=confirm_aer)
        for index, (a, b, mode) in enumerate(cases):
            expect_result, expect_carry = expected_arithmetic(a, b, mode, width)
            for engine, measured in (("op_list", fast[index]), ("aer", aer[index])):
                checks = check_case(spec, cases_values[index], measured)
                ok = (int(measured["R"]) == expect_result
                      and int(measured["Cout"]) == expect_carry)
                rows.append({
                    "circuit": label,
                    "engine": engine,
                    "style": "baseline" if label.startswith("baseline") else "optimized",
                    "width": width,
                    "mode": mode,
                    "A": a, "B": b,
                    "expected_result": expect_result,
                    "expected_carry": expect_carry,
                    "expected_borrow": 1 - expect_carry,
                    "measured_result": int(measured["R"]),
                    "measured_carry": int(measured["Cout"]),
                    "operands_preserved": bool(checks["inputs_preserved"]),
                    "ancilla_restored": bool(checks["ancilla_restored"]),
                    "pass": bool(ok and agree),
                })
                if not ok:
                    failures.append(
                        f"{label}/{engine} A={a} B={b} mode={mode} "
                        f"got=({measured['R']},{measured['Cout']}) "
                        f"want=({expect_result},{expect_carry})")
        if not agree:
            failures.append(f"{label}: op list and Aer disagree")

    if write and rows:
        config.write_rows(rows, "four_bit_verification")
    if failures:
        raise AssertionError(f"4-bit verification failed: {failures[:6]}")
    return rows


def summary(rows: list[dict]) -> str:
    out = []
    for label in sorted({r["circuit"] for r in rows}):
        subset = [r for r in rows if r["circuit"] == label]
        out.append(
            f"{label:28s} rows={len(subset):4d} pass={sum(r['pass'] for r in subset):4d} "
            f"operands_preserved={sum(r['operands_preserved'] for r in subset):4d} "
            f"ancilla_restored={sum(r['ancilla_restored'] for r in subset):4d}")
    return "\n".join(out)


if __name__ == "__main__":
    config.ensure_directories()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    result = verify(limit=limit)
    print(summary(result))
    print(f"\nwrote {len(result)} rows to {config.csv_path('four_bit_verification')}")
    sys.exit(0)

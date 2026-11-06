"""Ancilla verification: every helper line is tracked case by case.

Writes results/csv/ancilla_verification.csv, one row per (design, ancilla line).
For each line the study reports how many of the exhaustive cases leave it back
at the value it started from, whether the line carries input information
(documented garbage), and it confirms the op-list answer on Qiskit Aer.

Acceptance rule taken from the project specification: a dedicated ancilla that
the design claims to clean up must be restored in 100 % of cases. Lines the
design deliberately declares as garbage are recorded, not failed - they are the
quantity the uncomputation study (verify_garbage.py) then tries to remove.
"""

from __future__ import annotations

import sys

import config
from circuits import parametrized_nbit_adder
from circuits import circuit_utils as cu
from verification import nbit_designs, one_bit_designs
from verification.verify_4bit import build_cases_values, case_set

AER_SAMPLE = 96


def one_bit_cases() -> list[dict]:
    return [{"A": a, "B": b, "Cin": c}
            for a in (0, 1) for b in (0, 1) for c in (0, 1)]


def ancilla_lines(spec: cu.CircuitSpec) -> list[tuple[str, int, int]]:
    """(register name, qubit, position inside the register) for each ancilla line.

    Input and output registers are skipped: their final value is the answer, not
    a cleanup target.
    """
    output_lines = set(spec.flat(*spec.outputs))
    lines = []
    for name in spec.ancillas:
        if name in spec.inputs:
            continue
        for position, q in enumerate(spec.registers[name]):
            if q in output_lines:
                continue
            lines.append((name, q, position))
    return lines


def _initial_bits(spec: cu.CircuitSpec, name: str, cases_values: list[dict]) -> list[int]:
    """The value each case prepares on this ancilla register (0 unless it is an
    input-like control such as the add/subtract mode line)."""
    return [int(case.get(name, 0)) for case in cases_values]


def verify(width: int = 4, confirm_aer: bool = True, write: bool = True) -> list[dict]:
    designs = {**one_bit_designs(), **nbit_designs(width)}
    designs["baseline_dual_control_mux"] = parametrized_nbit_adder.build_nbit_design(
        width, "baseline", "dual_mux")

    nbit_cases = case_set(width)
    rows: list[dict] = []
    failures: list[str] = []

    for label, spec in designs.items():
        if "Cin" in spec.registers:
            cases_values = one_bit_cases()
        else:
            mode_filter = (0 if label.endswith("_adder") else
                           1 if label.endswith("_subtractor") else None)
            cases_values = build_cases_values(spec, nbit_cases, mode_filter)

        fast = cu.op_list_lines(spec, cases_values)
        stride = max(1, len(cases_values) // AER_SAMPLE)
        sampled = [(index, case) for index, case in enumerate(cases_values)
                   if index % stride == 0][:AER_SAMPLE]
        aer = (cu.run_cases(spec, [cu.case_dictionary(spec, case) for _, case in sampled])
               if confirm_aer else None)

        lines = ancilla_lines(spec)
        if not lines:
            # A design with no helper line outside its outputs needs no cleanup
            # at all; that is recorded as a single passing row so the CSV states
            # the footprint instead of staying silent.
            rows.append({
                "circuit": label,
                "width": width if len(spec.registers.get("A", [0])) > 1 else 1,
                "register": "(none)",
                "qubit": -1,
                "line_position": -1,
                "declared_garbage": False,
                "require_cleanup": True,
                "cases": len(cases_values),
                "cases_restored": len(cases_values),
                "restored_percent": 100.0,
                "final_values": [0],
                "initial_values": [0],
                "carries_input_information": False,
                "aer_cases": 0,
                "aer_cases_restored": 0,
                "aer_matches_op_list": "",
                "note": "no helper line outside the output registers, nothing to clean up",
                "pass": True,
            })

        for name, q, position in lines:
            initial = _initial_bits(spec, name, cases_values)
            restored = [int(fast[row, q]) == init for row, init in enumerate(initial)]
            finals = {int(fast[row, q]) for row in range(len(initial))}
            declared_garbage = name in spec.garbage
            require_cleanup = not declared_garbage

            aer_restored = 0
            agrees = True
            if aer is not None:
                for (index, case), measured in zip(sampled, aer):
                    init = int(case.get(name, 0))
                    got = (int(measured[name]) >> position) & 1
                    aer_restored += int(got == init)
                    agrees = agrees and got == int(fast[index, q])

            percent = round(100.0 * sum(restored) / len(restored), 2)
            ok = (percent == 100.0 if require_cleanup else True) and agrees
            rows.append({
                "circuit": label,
                "width": width if len(spec.registers.get("A", [0])) > 1 else 1,
                "register": name,
                "qubit": q,
                "line_position": position,
                "declared_garbage": declared_garbage,
                "require_cleanup": require_cleanup,
                "cases": len(cases_values),
                "cases_restored": sum(restored),
                "restored_percent": percent,
                "final_values": sorted(finals),
                "initial_values": sorted(set(initial)),
                "carries_input_information": len(finals) > 1 or finals != {0},
                "aer_cases": len(sampled) if aer is not None else 0,
                "aer_cases_restored": aer_restored,
                "aer_matches_op_list": agrees if aer is not None else "",
                "note": "" if aer is not None else f"{len(cases_values)} op-list cases, "
                          "Aer confirmation disabled",
                "pass": ok,
            })
            if not ok:
                failures.append(f"{label}: ancilla {name}[{q}] restored "
                                f"{percent}% (aer agreement={agrees})")

    if write and rows:
        config.write_rows(rows, "ancilla_verification")
    if failures:
        raise AssertionError(f"ancilla verification failed: {failures}")
    return rows


def summary(rows: list[dict]) -> str:
    out = []
    for label in sorted({r["circuit"] for r in rows}):
        subset = [r for r in rows if r["circuit"] == label]
        cleaned = [r for r in subset if r["require_cleanup"]]
        dirty = [r for r in subset if not r["require_cleanup"]]
        clean_ok = sum(r["cases_restored"] == r["cases"] for r in cleaned)
        out.append(f"{label:30s} lines={len(subset):2d} "
                   f"cleanup_required={len(cleaned):2d} cleanup_ok={clean_ok:2d} "
                   f"documented_garbage={len(dirty):2d} "
                   f"pass={sum(bool(r['pass']) for r in subset):2d}/{len(subset)}")
    return "\n".join(out)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    print(f"\nwrote {len(result)} rows to {config.csv_path('ancilla_verification')}")
    sys.exit(0)

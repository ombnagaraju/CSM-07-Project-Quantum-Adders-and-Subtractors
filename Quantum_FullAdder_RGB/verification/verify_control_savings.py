"""Contribution 1 verification: one mode qubit instead of two separate units.

Writes results/csv/control_qubit_savings.csv. Each row compares one shared
control architecture (single mode qubit, or the two-select-line multiplexer)
against the honest reference for a chip that advertises both operations: the
adder and the subtractor built as separate units, with the operand registers
counted once.

Two things are reported side by side so the headline claim cannot be an
artefact of the accounting:

* resource columns - qubits, ancillas, gates, quantum cost, logical depth and
  garbage, all measured by circuits.circuit_utils on the abstract op list, and
  the percentage saving against the separate pair;
* equivalence columns - the number of (A, B, mode) cases checked and how many
  of them the shared design got wrong, first through the exact reversible
  op-list simulator over all 2^(2n+1) cases and then on the Qiskit Aer
  simulator for a seeded subset.

transpilation/cost_report.py appends post-transpilation columns for the same
rows once the circuits are laid out on a fixed topology.
"""

from __future__ import annotations

import sys

import config
from circuits import circuit_utils as cu
from circuits.parametrized_nbit_adder import build_adder_pair, build_nbit_design
from circuits.shared_addsub_control import (
    build_shared_control_addsub,
    design_footprint,
    read_result,
    savings_table,
)
from verification.verify_4bit import build_cases_values, case_set

WIDTH = 4
AER_SAMPLE = 32
METRICS = ("qubits", "qubits_raw", "ancilla_qubits", "total_gates", "quantum_cost",
           "logical_depth", "logical_depth_serial", "garbage_qubits")


def equivalence(width: int = WIDTH, style: str = "baseline",
                confirm_aer: bool = True) -> dict:
    """Exact and Aer agreement of each shared architecture with the separate pair."""
    cases = case_set(width)
    shared = build_shared_control_addsub(width, style)
    pair = build_adder_pair(width, style)
    designs = {"shared_control": shared}
    if style == "baseline":
        designs["dual_control_mux"] = build_nbit_design(
            width, style, "dual_mux", name=f"{style}_dual_mux_{width}bit")

    out: dict[str, dict] = {}
    for approach, spec in designs.items():
        cases_values = build_cases_values(spec, cases)
        mismatches = []
        for entry, (a, b, mode) in zip(cases_values, cases):
            reference = pair["adder"] if mode == 0 else pair["subtractor"]
            ref_values = {"A": a, "B": b}
            if read_result(spec, entry) != read_result(reference, ref_values):
                mismatches.append((a, b, mode))

        row = {"cases": len(cases_values), "mismatches": len(mismatches),
               "examples": mismatches[:5]}

        if confirm_aer and mismatches == []:
            stride = max(1, len(cases_values) // AER_SAMPLE)
            sampled = cases_values[::stride][:AER_SAMPLE]
            modes = [entry.get("M", entry.get("S_sub", 0)) for entry in sampled]
            shared_measured = cu.run_cases(spec, [cu.case_dictionary(spec, v)
                                                  for v in sampled])
            reference_measured = {}
            operand_cases = [{"A": entry["A"], "B": entry["B"]} for entry in sampled]
            for mode, unit in ((0, pair["adder"]), (1, pair["subtractor"])):
                reference_measured[mode] = cu.run_cases(
                    unit, [cu.case_dictionary(unit, case) for case in operand_cases])
            aer_mismatches = 0
            for index, measured in enumerate(shared_measured):
                ref = reference_measured[modes[index]][index]
                if (int(measured["R"]), int(measured["Cout"])) != (
                        int(ref["R"]), int(ref["Cout"])):
                    aer_mismatches += 1
            row["aer_cases"] = len(sampled)
            row["aer_mismatches"] = aer_mismatches
        else:
            row["aer_cases"] = 0
            row["aer_mismatches"] = ""
        out[approach] = row
    return out


def verify(width: int = WIDTH, styles=("baseline", "optimized"),
           confirm_aer: bool = True, write: bool = True) -> list[dict]:
    """Build the control-qubit savings table with equivalence proof attached."""
    savings = {(row["style"], row["approach"]): row for row in savings_table(width, styles)}
    rows: list[dict] = []
    failures: list[str] = []

    for style in styles:
        absolute = design_footprint(width, style)
        checks = equivalence(width, style, confirm_aer=confirm_aer)
        for approach, measured in checks.items():
            entry = dict(savings[(style, approach)])
            entry["units"] = absolute[approach]["units"]
            entry["cases"] = measured["cases"]
            entry["op_list_mismatches"] = measured["mismatches"]
            entry["aer_cases"] = measured["aer_cases"]
            entry["aer_mismatches"] = measured["aer_mismatches"]
            entry["equivalence_pass"] = (measured["mismatches"] == 0
                                         and measured["aer_mismatches"] in (0, ""))
            entry["resources_pass"] = (entry["qubits_saving_percent"] > 0
                                       and entry["total_gates_saving_percent"] > 0
                                       and entry["quantum_cost_saving_percent"] > 0)
            entry["pass"] = bool(entry["equivalence_pass"] and entry["resources_pass"])
            rows.append(entry)
            if not entry["equivalence_pass"]:
                failures.append(f"{style}/{approach} is not equivalent to the separate pair "
                                f"({measured['mismatches']} op-list mismatches, "
                                f"{measured['aer_mismatches']} Aer mismatches)")

    # The reference architecture itself is published as a row so the absolute
    # numbers behind every percentage are visible in the same file.
    for style in styles:
        reference = design_footprint(width, style)["separate_pair"]
        row = {"style": style, "width": width, "approach": "separate_pair",
               "reference": "separate_pair", "units": reference["units"],
               "cases": (1 << width) ** 2 * 2, "op_list_mismatches": 0,
               "aer_cases": "", "aer_mismatches": "",
               "equivalence_pass": True, "resources_pass": True, "pass": True}
        for metric in METRICS:
            row[f"{metric}_shared"] = reference[metric]
            row[f"{metric}_reference"] = reference[metric]
            row[f"{metric}_saving_percent"] = 0.0
        rows.append(row)

    if write and rows:
        config.write_rows(rows, "control_savings")
    if failures:
        raise AssertionError(f"control-qubit verification failed: {failures}")
    return rows


def summary(rows: list[dict]) -> str:
    out = []
    for row in rows:
        if row["approach"] == "separate_pair":
            base = " ".join(f"{m}={row[f'{m}_reference']}" for m in METRICS)
            out.append(f"{row['style']:9s} separate_pair     {base} (reference)")
            continue
        savings = " ".join(f"{m}={row[f'{m}_saving_percent']:+7.2f}%"
                       for m in METRICS)
        out.append(f"{row['style']:9s} {row['approach']:17s} {savings} "
                   f"cases={row['cases']} mismatches={row['op_list_mismatches']}")
    return "\n".join(out)


if __name__ == "__main__":
    config.ensure_directories()
    result = verify()
    print(summary(result))
    print(f"\nwrote {len(result)} rows to {config.csv_path('control_savings')}")
    sys.exit(0)

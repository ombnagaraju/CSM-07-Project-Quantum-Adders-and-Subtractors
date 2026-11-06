"""Contribution 6 - reducing garbage outputs, two ways, both measured.

Structural uncomputation
    Re-apply the recomputation of a garbage value so that it XORs itself away.
    Works when the garbage is a function of lines that are still present, e.g.
    the A.B ancilla of the Peres full adder, restored by CCX(A, B -> AB) once
    A and B are back to their input values. It costs real gates but keeps the
    circuit fully coherent, so it is safe for superposed inputs.

Measurement-based uncomputation
    Measure the garbage line in the Z basis and use the classical outcome to
    clear it (measure + conditional X, or the equivalent mid-circuit reset).
    It costs no reversible gates and frees the ancilla for reuse, but it
    collapses the garbage line, which is only harmless when that line carries a
    classical function of the inputs. verification/verify_garbage.py quantifies
    the coherence penalty with a density-matrix comparison so the trade-off is
    a measured number rather than a claim.
"""

from __future__ import annotations

from circuits import circuit_utils as cu
from circuits.peres_fulladder import build_peres_fulladder


def build_peres_with_structural_uncomputation() -> cu.CircuitSpec:
    """Peres full adder whose two garbage lines are restored by two extra gates."""
    from circuits.peres_fulladder import QUBIT_MAP as m

    base = build_peres_fulladder()
    ops = list(base.ops) + [
        cu.cx(m["A"], m["B"]),              # B back to its input value
        cu.ccx(m["A"], m["B"], m["AB"]),    # AB ancilla back to |0>
    ]
    return cu.CircuitSpec(
        name="peres_structural_uncompute",
        ops=ops,
        n_qubits=base.n_qubits,
        registers=dict(base.registers),
        inputs=base.inputs,
        outputs=base.outputs,
        ancillas=("AB", "Cout"),
        garbage=(),
        notes=("Same two Peres blocks plus the carry CNOT, then CX(A->B) and "
               "CCX(A,B->AB) return both garbage lines to their initial values."),
    )


def garbage_lines(spec: cu.CircuitSpec) -> list:
    out = set(spec.flat(*spec.outputs))
    lines: list[int] = []
    for name in spec.garbage:
        lines.extend(q for q in spec.registers[name] if q not in out)
    return sorted(lines)


def measurement_based_uncompute(spec: cu.CircuitSpec, method: str = "conditional",
                                lines: list | None = None) -> cu.CircuitSpec:
    """Return a copy of `spec` whose garbage lines are cleared by measurement.

    method = "conditional": measure the line, then apply a classically
    controlled X when the outcome was 1 (feed-forward).
    method = "reset": the same effect expressed as one mid-circuit reset, which
    hardware implements as measurement plus a conditional drive.
    """
    if method not in ("conditional", "reset"):
        raise ValueError("method must be 'conditional' or 'reset'")
    targets = garbage_lines(spec) if lines is None else sorted(lines)
    if not targets:
        raise ValueError(f"'{spec.name}' declares no garbage lines to uncompute")

    tail: list = []
    for q in targets:
        if method == "conditional":
            tail.append(cu.measure(q))
            tail.append(cu.cond_x(q))
        else:
            tail.append(cu.reset(q))

    registers = dict(spec.registers)
    registers["Uncomputed"] = list(targets)
    return cu.CircuitSpec(
        name=f"{spec.name}_meas_uncompute_{method}",
        ops=list(spec.ops) + tail,
        n_qubits=spec.n_qubits,
        registers=registers,
        inputs=spec.inputs,
        outputs=spec.outputs,
        ancillas=tuple(dict.fromkeys(list(spec.ancillas))),
        garbage=(),
        notes=(f"Garbage lines {targets} cleared by {method} mid-circuit "
               "measurement feed-forward; arithmetic outputs are unchanged for "
               "basis-state inputs."),
    )

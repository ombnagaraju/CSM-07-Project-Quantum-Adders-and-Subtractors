"""Shared circuit machinery: gate blocks, resource bookkeeping and simulators.

All circuits in this project are described as a list of *abstract reversible
operations* (``Op`` tuples) before any Qiskit object exists.  That keeps the
logical resource counting (gate library of section "Fair comparison protocol")
separate from the hardware counting done in :mod:`transpilation.cost_report`,
and it lets the same core builder be emitted plain, controlled, or measured.
"""

from __future__ import annotations


from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Iterable, Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ClassicalRegister, Gate
from qiskit_aer import AerSimulator

import config

# ---------------------------------------------------------------------------
# Reversible gate blocks
# ---------------------------------------------------------------------------
# ("x", t) | ("cx", c, t) | ("ccx", c1, c2, t) | ("peres", a, b, c)
# ("measure", q) | ("cond_x", q) | ("reset", q)
Op = tuple


def x(t: int) -> Op:
    return ("x", t)


def cx(c: int, t: int) -> Op:
    return ("cx", c, t)


def ccx(c1: int, c2: int, t: int) -> Op:
    return ("ccx", c1, c2, t)


def peres(a: int, b: int, c: int) -> Op:
    """Peres block P(a, b, c) = (a, a XOR b, a.b XOR c)."""
    return ("peres", a, b, c)


def peres_dg(a: int, b: int, c: int) -> Op:
    """Inverse Peres block, used for structural uncomputation."""
    return ("peres_dg", a, b, c)


def measure(q: int) -> Op:
    """Z-basis measurement of one line into its own single-bit classical register."""
    return ("measure", q)


def cond_x(q: int) -> Op:
    """Classically controlled X that flips `q` only when its own measurement was 1."""
    return ("cond_x", q)


def reset(q: int) -> Op:
    """Mid-circuit reset of one line back to |0>."""
    return ("reset", q)


class PeresGate(Gate):
    """Peres gate as a named composite block so logical counts stay block level."""

    def __init__(self, inverse: bool = False):
        name = "peres_dg" if inverse else "peres"
        super().__init__(name, 3, [])
        self._inverse = inverse

    def _define(self) -> None:
        definition = QuantumCircuit(3, name=self.name)
        if self._inverse:
            definition.cx(0, 1)
            definition.ccx(0, 1, 2)
        else:
            definition.ccx(0, 1, 2)
            definition.cx(0, 1)
        self.definition = definition

    def get_inverse(self) -> "PeresGate":
        return PeresGate(inverse=not self._inverse)


def emit(qc: QuantumCircuit, ops: Iterable[Op], ro=None) -> QuantumCircuit:
    """Append abstract ops to a QuantumCircuit.

    `ro` is the single read-out classical register used by mid-circuit
    measurements, so that measurement-based uncomputation (contribution 6) and
    the final read-out share one bit ordering: classical bit k is qubit k.
    """
    for op in ops:
        kind = op[0]
        if kind == "x":
            qc.x(op[1])
        elif kind == "cx":
            qc.cx(op[1], op[2])
        elif kind == "ccx":
            qc.ccx(op[1], op[2], op[3])
        elif kind in ("peres", "peres_dg"):
            qc.append(PeresGate(inverse=kind == "peres_dg"), [op[1], op[2], op[3]])
        elif kind == "measure":
            if ro is None:
                raise ValueError("measure op needs the read-out register")
            qc.measure(op[1], ro[op[1]])
        elif kind == "cond_x":
            if ro is None:
                raise ValueError("cond_x op needs the read-out register")
            with qc.if_test((ro[op[1]], 1)):
                qc.x(op[1])
        elif kind == "reset":
            qc.reset(op[1])
        else:
            raise ValueError(f"Unknown op kind '{kind}'")
    return qc


# ---------------------------------------------------------------------------
# Circuit specification
# ---------------------------------------------------------------------------
@dataclass
class CircuitSpec:
    name: str
    ops: list
    n_qubits: int
    registers: dict
    inputs: tuple = ()
    outputs: tuple = ()
    ancillas: tuple = ()
    garbage: tuple = ()
    notes: str = ""
    extra_ops: list = field(default_factory=list)

    def reg(self, name: str) -> list:
        return list(self.registers[name])

    def flat(self, *names: str) -> list:
        out: list[int] = []
        for name in names:
            out.extend(self.registers[name])
        return out

    def qubit_count(self) -> int:
        return self.n_qubits

    def all_ops(self) -> list:
        return list(self.ops) + list(self.extra_ops)

    def build(self, measure: bool = True, add_barrier: bool = False) -> QuantumCircuit:
        qc = QuantumCircuit(self.n_qubits, name=self.name)
        ro = ClassicalRegister(self.n_qubits, "ro")
        qc.add_register(ro)
        emit(qc, self.all_ops(), ro)
        if add_barrier:
            qc.barrier()
        if measure:
            for qubit in range(self.n_qubits):
                qc.measure(qubit, ro[qubit])
        return qc

    def measured_registers(self) -> list:
        """Register names that hold the answer (used to read results)."""
        return list(self.outputs)


def controlled_ops(ops: Sequence[Op], ctrl: int, ancilla_pool: Sequence[int]) -> tuple[list, list]:
    """Return (new_ops, used_ancillas): every op gated by one extra control line.

    Used for the dual-control multiplexer design and the ALU slice, where the
    whole adder or subtractor block has to be conditioned on a select line.
    Rules stay inside the {x, cx, ccx} library so Aer and the transpiler accept
    the result without multi-control primitives:

      X(t)          -> CX(ctrl, t)
      CX(c, t)      -> CCX(ctrl, c, t)
      CCX(c1,c2,t)  -> CCX(c1,c2,a); CCX(a,ctrl,t); CCX(c1,c2,a)   (a uncomputed)

    The pool is cycled round-robin instead of consumed: each helper ancilla is
    returned to |0> by the third gate of its own triple, so reusing it later is
    exact and keeps the multiplexer from needing one ancilla per Toffoli.
    """
    pool = list(ancilla_pool)
    if not pool:
        raise ValueError("controlled_ops needs at least one ancilla qubit")
    used: list[int] = []
    out: list[Op] = []
    cursor = [0]

    def take_ancilla() -> int:
        anc = pool[cursor[0] % len(pool)]
        cursor[0] += 1
        if anc not in used:
            used.append(anc)
        return anc

    for op in ops:
        kind = op[0]
        if kind == "x":
            out.append(cx(ctrl, op[1]))
        elif kind == "cx":
            out.append(ccx(ctrl, op[1], op[2]))
        elif kind == "ccx":
            anc = take_ancilla()
            out.append(ccx(op[1], op[2], anc))
            out.append(ccx(anc, ctrl, op[3]))
            out.append(ccx(op[1], op[2], anc))
        elif kind in ("peres", "peres_dg"):
            # P = CCX(a,b,c) then CX(a,b); control each part separately.
            inner = ([ccx(op[1], op[2], op[3]), cx(op[1], op[2])]
                     if kind == "peres"
                     else [cx(op[1], op[2]), ccx(op[1], op[2], op[3])])
            sub, _ = controlled_ops(inner, ctrl, pool)
            out.extend(sub)
        else:
            raise ValueError(f"Cannot control op kind '{kind}'")
    return out, used


# ---------------------------------------------------------------------------
# Logical resource metrics (one metric code for every design, contribution 5)
# ---------------------------------------------------------------------------
def logical_counts(spec: CircuitSpec) -> dict:
    """Count gate blocks at the logical level (never mixed with decomposition).

    Mid-circuit measurements, conditional flips and resets are reported in their
    own fields and are NOT part of `total_gates`, because the NCV-L cost model
    only prices reversible gate blocks (contribution 6 measures their depth
    separately).
    """
    counter: Counter = Counter(op[0] for op in spec.all_ops())
    counts = {
        "x": counter.get("x", 0),
        "cx": counter.get("cx", 0),
        "ccx": counter.get("ccx", 0),
        "peres": counter.get("peres", 0) + counter.get("peres_dg", 0),
        "measure": counter.get("measure", 0),
        "cond_x": counter.get("cond_x", 0),
        "reset": counter.get("reset", 0),
    }
    counts["total_gates"] = counts["x"] + counts["cx"] + counts["ccx"] + counts["peres"]
    return counts


def quantum_cost(spec: CircuitSpec) -> int:
    """NCV-L cost of the logical block list (Toffoli = 5, Peres = 4).

    Measurements, conditional flips and resets cost zero here; they are charged
    through the depth and classical-feed-forward columns instead.
    """
    total = 0
    for op in spec.all_ops():
        if op[0] in ("measure", "cond_x", "reset"):
            continue
        total += config.gate_quantum_cost(op[0])
    return total


def logical_depth(spec: CircuitSpec) -> int:
    """Greedy circuit depth of the logical op list."""
    layer = [0] * spec.n_qubits
    for op in spec.all_ops():
        touched = op[1:]
        start = max(layer[q] for q in touched)
        for q in touched:
            layer[q] = start + 1
    return max(layer) if layer else 0


def ancilla_count(spec: CircuitSpec) -> int:
    return sum(len(spec.registers[name]) for name in spec.ancillas)


def garbage_count(spec: CircuitSpec) -> int:
    return sum(len(spec.registers[name]) for name in spec.garbage)


def input_count(spec: CircuitSpec) -> int:
    return sum(len(spec.registers[name]) for name in spec.inputs)


def output_count(spec: CircuitSpec) -> int:
    return sum(len(spec.registers[name]) for name in spec.outputs)


def unused_qubits(spec: CircuitSpec) -> list:
    seen: set[int] = set()
    for indices in spec.registers.values():
        seen.update(indices)
    return [q for q in range(spec.n_qubits) if q not in seen]


def spec_metrics(spec: CircuitSpec) -> dict:
    counts = logical_counts(spec)
    return {
        "circuit": spec.name,
        "qubits": spec.n_qubits,
        "input_qubits": input_count(spec),
        "output_qubits": output_count(spec),
        "ancilla_qubits": ancilla_count(spec),
        "garbage_qubits": garbage_count(spec),
        "x_gates": counts["x"],
        "cx_gates": counts["cx"],
        "ccx_gates": counts["ccx"],
        "peres_gates": counts["peres"],
        "total_gates": counts["total_gates"],
        "measure_ops": counts["measure"],
        "cond_x_ops": counts["cond_x"],
        "reset_ops": counts["reset"],
        "logical_depth": logical_depth(spec),
        "quantum_cost": quantum_cost(spec),
    }


def to_qasm(spec: CircuitSpec) -> str:
    return spec.build(measure=False).qasm()


def save_qasm(spec: CircuitSpec, filename: str) -> str:
    import os

    path = os.path.join(config.CIRCUITS_DIR, filename)
    os.makedirs(config.CIRCUITS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_qasm(spec))
    return path


def draw_circuit(spec: CircuitSpec, filename: str, wide: bool = True) -> str:
    """Render a circuit diagram into results/circuits/ as PNG."""
    import os

    from qiskit.visualization import circuit_drawer

    qc = spec.build(measure=False)
    os.makedirs(config.CIRCUITS_DIR, exist_ok=True)
    path = os.path.join(config.CIRCUITS_DIR, filename)
    try:
        image = circuit_drawer(qc, output="latex", filename=path)
    except Exception:
        image = circuit_drawer(qc, output="mpl", filename=path, scale=0.6 if wide else 1.0)
    return str(image or path)


# ---------------------------------------------------------------------------
# Classical (exact) reversible simulation of the op list
# ---------------------------------------------------------------------------
def apply_ops_to_bits(ops: Sequence[Op], bits: np.ndarray) -> np.ndarray:
    """Apply the op list to a batch of bit-vectors, shape (n_cases, n_qubits).

    These circuits contain only X, CNOT and Toffoli-type blocks, so their action
    on computational-basis states is an exact classical reversible map.  This is
    the fast path used for permutation and garbage analysis; :func:`run_cases`
    below re-checks the same truth tables on the Qiskit simulator.
    """
    state = np.array(bits, dtype=np.uint8, copy=True)
    for op in ops:
        kind = op[0]
        if kind == "x":
            state[:, op[1]] ^= 1
        elif kind == "cx":
            state[:, op[2]] ^= state[:, op[1]]
        elif kind == "ccx":
            state[:, op[3]] ^= state[:, op[1]] & state[:, op[2]]
        elif kind == "peres":
            a, b, c = op[1], op[2], op[3]
            carry = state[:, a] & state[:, b]
            state[:, c] ^= carry
            state[:, b] ^= state[:, a]
        elif kind == "peres_dg":
            a, b, c = op[1], op[2], op[3]
            state[:, b] ^= state[:, a]
            carry = state[:, a] & state[:, b]
            state[:, c] ^= carry
        elif kind in ("measure",):
            continue                     # Z measurement leaves a basis state unchanged
        elif kind in ("cond_x", "reset"):
            state[:, op[1]] = 0          # measure-then-flip-if-1 equals clearing
        else:
            raise ValueError(f"Unknown op kind '{kind}'")
    return state


def value_to_bits(value: int, qubits: Sequence[int]) -> dict:
    """Map an integer onto qubit indices, LSB first (config.LSB_QUBIT_INDEX)."""
    return {q: (value >> k) & 1 for k, q in enumerate(qubits)}


def bits_to_value(bits: Sequence[int], qubits: Sequence[int]) -> int:
    return sum(int(bits[k]) << k for k, q in enumerate(qubits))


def initial_ops(values: dict) -> list:
    """X ops that prepare a basis state given {qubit: 0/1}."""
    return [x(q) for q, bit in sorted(values.items()) if bit]


def permutation_map(spec: CircuitSpec, active_qubits: Sequence[int]) -> np.ndarray:
    """Exact truth permutation of `active_qubits` through the circuit.

    Returns an int array where index is the input value on `active_qubits` and
    the entry is the output value on the same lines (other lines stay 0).
    """
    n = len(active_qubits)
    size = 1 << n
    state = np.zeros((size, spec.n_qubits), dtype=np.uint8)
    for q_index, q in enumerate(active_qubits):
        state[:, q] = (np.arange(size) >> q_index) & 1
    out = apply_ops_to_bits(spec.all_ops(), state)
    result = np.zeros(size, dtype=np.int64)
    for q_index, q in enumerate(active_qubits):
        result += out[:, q].astype(np.int64) << q_index
    return result


def is_bijective(spec: CircuitSpec, active_qubits: Sequence[int]) -> bool:
    table = permutation_map(spec, active_qubits)
    return len(np.unique(table)) == len(table)


def garbage_lines(spec: CircuitSpec, active_qubits: Sequence[int]) -> dict:
    """Report which non-output lines end up depending on the input.

    A line is garbage when it is not declared as an output and its final value
    is not constant across the truth table (so it carries information the user
    did not ask for).
    """
    output_lines = set(spec.flat(*spec.outputs))
    n = len(active_qubits)
    state = np.zeros((1 << n, spec.n_qubits), dtype=np.uint8)
    for q_index, q in enumerate(active_qubits):
        state[:, q] = (np.arange(1 << n) >> q_index) & 1
    out = apply_ops_to_bits(spec.all_ops(), state)
    report = {}
    for q in range(spec.n_qubits):
        if q in output_lines:
            continue
        column = out[:, q]
        report[q] = {
            "constant": bool(np.all(column == column[0])),
            "value": int(column[0]),
            "varies": bool(not np.all(column == column[0])),
        }
    return report


# ---------------------------------------------------------------------------
# Qiskit / Aer simulation
# ---------------------------------------------------------------------------
def make_backend(seed: int | None = None, method: str | None = None) -> AerSimulator:
    return AerSimulator(
        method=method or config.SIMULATOR_METHOD,
        seed_simulator=config.GLOBAL_SEED if seed is None else seed,
    )


def run_cases(spec: CircuitSpec, cases: list[dict], shots: int = 1,
              chunk: int = 128, seed: int | None = None,
              method: str | None = None) -> list[dict]:
    """Execute basis-state cases on the Qiskit Aer simulator.

    `cases` is a list of {qubit: bit} dictionaries (only the qubits that must be
    set to 1 need to appear). Returns one dictionary per case mapping every
    register name to its measured integer, using the most probable shot.

    Circuits are transpiled only onto {ccx, cx, x} so that Peres blocks keep
    their documented meaning, and the single `ro` read-out register guarantees
    that classical bit k is qubit k.
    """
    from qiskit import transpile as _transpile

    backend = make_backend(seed=seed, method=method)
    body = spec.build(measure=True)
    results: list[dict] = []
    for start in range(0, len(cases), chunk):
        batch = cases[start:start + chunk]
        circuits = [_prepended(spec, case, body, tag=f"_{start + i}")
                    for i, case in enumerate(batch)]
        circuits = _transpile(circuits, backend, basis_gates=config.LOGICAL_BASIS_GATES,
                              optimization_level=0, seed_transpiler=config.GLOBAL_SEED)
        counts = backend.run(circuits, shots=shots).result().get_counts()
        if not isinstance(counts, list):
            counts = [counts]
        for one in counts:
            bits = max(one, key=one.get)[::-1]
            results.append(_registers_from_bits(bits, spec))
    return results


def _prepended(spec: CircuitSpec, case: dict, body: QuantumCircuit,
               tag: str = "") -> QuantumCircuit:
    prep = QuantumCircuit(spec.n_qubits, name="prep")
    prep.add_register(ClassicalRegister(spec.n_qubits, "ro"))
    for qubit, bit in sorted(case.items()):
        if bit:
            prep.x(qubit)
    out = prep.compose(body, qubits=list(range(spec.n_qubits)),
                       clbits=list(range(spec.n_qubits)))
    # Unique experiment names, otherwise Aer merges identical batch entries.
    out.name = f"{spec.name}{tag}"
    return out


def _registers_from_bits(bits: str, spec: CircuitSpec) -> dict:
    return {name: bits_to_value([bits[q] for q in indices], indices)
            for name, indices in spec.registers.items()}


def run_cases_statevector(spec: CircuitSpec, cases: list[dict]) -> list[dict]:
    """Exact statevector read-out, used to cross-check the sampled path.

    A deterministic reversible circuit puts all amplitude on one basis state, so
    argmax of the probability vector is the exact answer. Kept separate from
    :func:`run_cases` because it costs 2^n memory.
    """
    from qiskit.quantum_info import Statevector

    if any(op[0] in ("measure", "cond_x", "reset") for op in spec.all_ops()):
        raise ValueError(
            f"'{spec.name}' contains mid-circuit measurement or reset, which the "
            "statevector cross-check cannot represent. Use run_cases (Aer) for it."
        )
    body = spec.build(measure=False)
    out = []
    for case in cases:
        qc = QuantumCircuit(spec.n_qubits)
        qc.add_register(ClassicalRegister(spec.n_qubits, "ro"))
        for qubit, bit in sorted(case.items()):
            if bit:
                qc.x(qubit)
        qc = qc.compose(body, qubits=list(range(spec.n_qubits)),
                        clbits=list(range(spec.n_qubits)))
        index = int(np.argmax(np.abs(Statevector(qc).data) ** 2))
        bits = "".join(str((index >> q) & 1) for q in range(spec.n_qubits))
        out.append(_registers_from_bits(bits, spec))
    return out


def case_dictionary(spec: CircuitSpec, values: dict) -> dict:
    """Turn {register_name: integer} into the {qubit: bit} form the simulators want."""
    state: dict[int, int] = {}
    for name, value in values.items():
        for qubit, bit in value_to_bits(int(value), spec.registers[name]).items():
            state[qubit] = bit
    return state


def format_metrics_table(rows: list[dict], columns: Sequence[str]) -> str:
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    header = " | ".join(c.ljust(widths[c]) for c in columns)
    line = "-+-".join("=" * widths[c] for c in columns)
    body = "\n".join(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns)
                     for r in rows)
    return f"{header}\n{line}\n{body}"

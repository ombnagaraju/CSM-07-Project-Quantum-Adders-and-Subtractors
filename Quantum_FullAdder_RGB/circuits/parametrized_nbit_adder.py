"""Parameterised n-bit reversible adder-subtractor designs (contributions 1 and 3).

One builder produces every ripple variant used in the project so the comparison
is always like-for-like.

style
    ``baseline``   Toffoli-CNOT ripple stage: 2 Toffoli + 4 CNOT per bit. Results
                   live in their own R register, so the carry chain lines
                   (carry-in copy plus intermediate carries) remain garbage.
    ``optimized``  Peres-block ripple stage: 2 Peres + 1 CNOT per bit. Each carry
                   line is turned into its sum bit by the second Peres gate, so
                   there is no R register and no garbage line at all.

mode
    ``add``        plain addition, R = (A + B) mod 2^n.
    ``subtract``   two's-complement subtraction, R = (A - B) mod 2^n.
    ``shared``     one control qubit M selects the operation (contribution 1).
    ``dual_mux``   two select qubits gate a full add block and a full subtract
                   block inside one unit (baseline style only).

Qubit convention: the LSB of every register is its lowest qubit index
(``config.LSB_QUBIT_INDEX``); Qiskit bit strings are reversed when read.
"""

from __future__ import annotations

from circuits import circuit_utils as cu

STYLES = ("baseline", "optimized")
MODES = ("add", "subtract", "shared", "dual_mux")


def _stage_ops(style: str, i: int, A, B, chain, R) -> list:
    if style == "baseline":
        return [
            cu.ccx(A[i], B[i], chain[i + 1]),      # generate term into carry line
            cu.cx(A[i], B[i]),                     # B[i] becomes propagate g_i
            cu.ccx(B[i], chain[i], chain[i + 1]),  # carry line = a.b' + g_i.c_i
            cu.cx(B[i], R[i]),                     # sum bit, part 1
            cu.cx(chain[i], R[i]),                 # sum bit, part 2
            cu.cx(A[i], B[i]),                     # restore muxed B[i]
        ]
    return [
        cu.peres(A[i], B[i], chain[i + 1]),        # chain[i+1] = a.b', B[i] = g_i
        cu.peres(B[i], chain[i], chain[i + 1]),    # chain[i] = sum_i, chain[i+1] = carry_i
        cu.cx(A[i], B[i]),                         # restore muxed B[i]
    ]


def build_nbit_design(width: int = 4, style: str = "baseline", mode: str = "shared",
                      name: str | None = None) -> cu.CircuitSpec:
    """Build an n-bit reversible adder-subtractor and describe its registers."""
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    n = int(width)
    if n < 1:
        raise ValueError("width must be at least 1")

    cursor = 0
    A = list(range(cursor, cursor + n)); cursor += n
    B = list(range(cursor, cursor + n)); cursor += n
    chain = list(range(cursor, cursor + n + 1)); cursor += n + 1
    if style == "baseline":
        R = list(range(cursor, cursor + n)); cursor += n
    else:
        R = chain[:n]

    registers = {"A": A, "B": B, "R": R, "Cout": [chain[n]]}
    ops: list = []

    if mode == "shared":
        M = [cursor]; cursor += 1
        registers["M"] = M

    def plain_arithmetic(block_mode: str) -> list:
        local: list = []
        if block_mode == "subtract":
            local.append(cu.x(chain[0]))
            local.extend(cu.x(B[i]) for i in range(n))
        elif block_mode == "shared":
            local.append(cu.cx(M[0], chain[0]))
            local.extend(cu.cx(M[0], B[i]) for i in range(n))
        for i in range(n):
            local.extend(_stage_ops(style, i, A, B, chain, R))
        if block_mode == "subtract":
            local.extend(cu.x(B[i]) for i in range(n))
        elif block_mode == "shared":
            local.extend(cu.cx(M[0], B[i]) for i in range(n))
        return local

    if mode == "dual_mux":
        if style != "baseline":
            raise NotImplementedError(
                "dual_mux needs a result register that the two gated blocks can "
                "share, and the Peres style writes its sums onto its own carry "
                "chain. Use mode='shared' or the separate-pair design instead."
            )
        s_add = [cursor]; cursor += 1
        s_sub = [cursor]; cursor += 1
        registers["S_add"] = s_add
        registers["S_sub"] = s_sub
        # Each gated Toffoli uncomputes its helper line immediately, so a small
        # rotating pool is enough however wide the adder is.
        pool = list(range(cursor, cursor + 4))
        registers["Ctrl_anc"] = pool
        cursor += len(pool)
        controlled_add, used = cu.controlled_ops(plain_arithmetic("add"), s_add[0], pool)
        ops.extend(controlled_add)
        controlled_sub, used2 = cu.controlled_ops(
            plain_arithmetic("subtract"), s_sub[0], pool)
        ops.extend(controlled_sub)
    elif mode in ("add", "subtract", "shared"):
        ops.extend(plain_arithmetic(mode))

    # ---- register roles --------------------------------------------------
    outputs = ["R", "Cout"]
    ancillas = ["R", "Cout"] if style == "baseline" else ["R", "Cout"]
    garbage: list[str] = []
    if style == "baseline":
        # carry-in copy plus the n-1 intermediate carries are never read again
        registers["Carry_internal"] = chain[:n]
        ancillas.append("Carry_internal")
        garbage.append("Carry_internal")
    if mode == "shared":
        ancillas.append("M")
    if mode == "dual_mux":
        ancillas.extend(["S_add", "S_sub", "Ctrl_anc"])

    notes = (
        f"style={style}, mode={mode}, width={n}. Convention: R = (A + B) mod 2^{n} "
        f"when the mode line is 0 and R = (A - B) mod 2^{n} when it is 1; "
        f"Cout=1 for addition means carry out, Cout=1 for subtraction means "
        f"A >= B, so borrow = NOT Cout. A and B are restored by the documented "
        f"uncomputation pass."
    )

    return cu.CircuitSpec(
        name=name or f"{style}_{mode}_{n}bit",
        ops=ops,
        n_qubits=cursor,
        registers=registers,
        inputs=tuple(["A", "B"] + (["M"] if "M" in registers else [])),
        outputs=tuple(outputs),
        ancillas=tuple(dict.fromkeys(ancillas)),
        garbage=tuple(dict.fromkeys(garbage)),
        notes=notes,
    )


def build_adder_pair(width: int = 4, style: str = "baseline") -> dict:
    """The 'separate circuits' reference design for contribution 1.

    A machine that offers both operations from two standalone units needs both
    blocks present at once, so the combined resource footprint is the sum.
    """
    return {
        "adder": build_nbit_design(width, style, "add", name=f"{style}_add_{width}bit"),
        "subtractor": build_nbit_design(width, style, "subtract",
                                        name=f"{style}_sub_{width}bit"),
    }


def combined_metrics(specs, share_operands: bool = True) -> dict:
    """Footprint of several units that must all exist in the same machine.

    Operand registers are physically shared by the two units of a real chip, so
    with ``share_operands`` the duplicated A/B qubits are counted once. Both the
    shared and the raw sum are reported; the parallel depth is the max of the
    unit depths and the serial depth is their sum.
    """
    specs = list(specs)
    rows = [cu.spec_metrics(s) for s in specs]
    combined = {"circuit": " + ".join(s.name for s in specs)}
    for key in ("input_qubits", "output_qubits", "ancilla_qubits", "garbage_qubits",
                "x_gates", "cx_gates", "ccx_gates", "peres_gates", "total_gates",
                "quantum_cost"):
        combined[key] = sum(row[key] for row in rows)
    combined["qubits_raw"] = sum(row["qubits"] for row in rows)
    duplicate_operands = 0
    if share_operands:
        for name in ("A", "B"):
            sizes = {len(s.registers[name]) for s in specs if name in s.registers}
            if len(specs) > 1 and sizes:
                duplicate_operands += (len(specs) - 1) * sizes.pop()
    combined["qubits"] = combined["qubits_raw"] - duplicate_operands
    combined["duplicate_operand_qubits_removed"] = duplicate_operands
    combined["logical_depth"] = max(row["logical_depth"] for row in rows)
    combined["logical_depth_serial"] = sum(row["logical_depth"] for row in rows)
    return combined


def read_result(measured: dict) -> tuple[int, int]:
    """Return (result, carry_out) from a measured-register dictionary."""
    return int(measured["R"]), int(measured["Cout"])

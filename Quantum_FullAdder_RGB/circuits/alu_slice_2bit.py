"""Contribution 10 (stretch) - a two-bit ALU slice around the adder-subtractor.

Select code k = 2*S1 + S0:

    00  A + B      01  A - B      10  A AND B     11  A OR  B

Construction, entirely inside the {X, CNOT, Toffoli} library:

* the two select lines are decoded into four one-hot lines,
* the two Peres arithmetic stages run once per operation, each gated by its own
  one-hot line, so the inactive block is the identity,
* AND is a Toffoli into a zeroed line; OR is a Toffoli sandwiched by X gates
  (De Morgan) into another zeroed line,
* a one-hot multiplexer copies the winning result into the shared output
  register, and
* optionally the decode lines are uncomputed again, which is what the garbage
  column of alu_slice_cost.csv measures.

This is deliberately a *slice*: two bits, one operation per call, so the whole
2^(2+2+2) = 64 case space is exhaustively verifiable.
"""

from __future__ import annotations

from circuits import circuit_utils as cu

WIDTH = 2
OPERATIONS = {0: "add", 1: "subtract", 2: "and", 3: "or"}


def build_alu_slice_2bit(uncompute_decode: bool = True,
                         name: str | None = None) -> cu.CircuitSpec:
    n = WIDTH
    cursor = 0
    A = list(range(cursor, cursor + n)); cursor += n
    B = list(range(cursor, cursor + n)); cursor += n
    chain = list(range(cursor, cursor + n + 1)); cursor += n + 1
    and_r = list(range(cursor, cursor + n)); cursor += n
    or_r = list(range(cursor, cursor + n)); cursor += n
    R = list(range(cursor, cursor + n)); cursor += n
    S1 = cursor; S0 = cursor + 1; cursor += 2
    op = [cursor + k for k in range(4)]; cursor += 4
    pool = list(range(cursor, cursor + 4)); cursor += 4

    ops: list = []

    # ---- one-hot decode of the select lines ------------------------------
    def decode_ops(index: int) -> list:
        s1_neg = not (index & 0b10)
        s0_neg = not (index & 0b01)
        local: list = []
        if s1_neg:
            local.append(cu.x(S1))
        if s0_neg:
            local.append(cu.x(S0))
        local.append(cu.ccx(S1, S0, op[index]))
        if s0_neg:
            local.append(cu.x(S0))
        if s1_neg:
            local.append(cu.x(S1))
        return local

    for index in range(4):
        ops.extend(decode_ops(index))

    # ---- arithmetic stages (Peres ripple, sums land on the chain) --------
    def stages() -> list:
        local: list = []
        for i in range(n):
            local.append(cu.peres(A[i], B[i], chain[i + 1]))
            local.append(cu.peres(B[i], chain[i], chain[i + 1]))
            local.append(cu.cx(A[i], B[i]))
        return local

    add_block, _ = cu.controlled_ops(stages(), op[0], pool)
    sub_pre = [cu.x(chain[0])] + [cu.x(B[i]) for i in range(n)]
    sub_post = [cu.x(B[i]) for i in range(n)]
    sub_block, _ = cu.controlled_ops(sub_pre + stages() + sub_post, op[1], pool)
    ops.extend(add_block)
    ops.extend(sub_block)

    # ---- logic blocks ----------------------------------------------------
    and_ops = [cu.ccx(A[i], B[i], and_r[i]) for i in range(n)]
    or_ops: list = []
    for i in range(n):
        or_ops.extend([cu.x(A[i]), cu.x(B[i]), cu.ccx(A[i], B[i], or_r[i]),
                       cu.x(A[i]), cu.x(B[i]), cu.x(or_r[i])])
    and_block, _ = cu.controlled_ops(and_ops, op[2], pool)
    or_block, _ = cu.controlled_ops(or_ops, op[3], pool)
    ops.extend(and_block)
    ops.extend(or_block)

    # ---- one-hot multiplexer into the shared output register -------------
    for i in range(n):
        ops.append(cu.ccx(op[0], chain[i], R[i]))
        ops.append(cu.ccx(op[1], chain[i], R[i]))
        ops.append(cu.ccx(op[2], and_r[i], R[i]))
        ops.append(cu.ccx(op[3], or_r[i], R[i]))

    garbage = ["AND_internal", "OR_internal", "Carry_internal"]
    if uncompute_decode:
        for index in reversed(range(4)):
            ops.extend(decode_ops(index))
    else:
        garbage.append("Op_decode")

    registers = {
        "A": A, "B": B, "R": R, "Cout": [chain[n]],
        "Carry_internal": chain[:n], "AND_internal": and_r, "OR_internal": or_r,
        "S": [S0, S1], "Op_decode": op, "Ctrl_anc": pool,
    }
    return cu.CircuitSpec(
        name=name or f"alu_slice_2bit{'_uncomputed' if uncompute_decode else ''}",
        ops=ops,
        n_qubits=cursor,
        registers=registers,
        inputs=("A", "B", "S"),
        outputs=("R",),
        ancillas=("R", "Carry_internal", "AND_internal", "OR_internal",
                  "Op_decode", "Ctrl_anc"),
        garbage=tuple(garbage),
        notes=("Two-bit ALU slice. R holds the selected operation result; "
               "Cout is meaningful only for the arithmetic codes 00 and 01, "
               "where Cout=1 for 01 means A >= B (borrow = NOT Cout). "
               f"Decode uncomputation: {uncompute_decode}."),
    )


def expected(a: int, b: int, code: int) -> int:
    if code == 0:
        return (a + b) & 0b11
    if code == 1:
        return (a - b) & 0b11
    if code == 2:
        return a & b
    return a | b


def all_cases() -> list:
    return [(a, b, code) for a in range(4) for b in range(4) for code in range(4)]


def cases_values() -> list:
    """Every (A, B, select code) setting as register values."""
    return [{"A": a, "B": b, "S": code} for a, b, code in all_cases()]


def run_expected_check(spec: cu.CircuitSpec) -> list:
    """Exact op-list comparison of every 64 (A, B, code) case."""
    failures: list = []
    for (a, b, code), measured in zip(all_cases(),
                                      cu.op_list_results(spec, cases_values())):
        got = int(measured["R"])
        if got != expected(a, b, code):
            failures.append((a, b, OPERATIONS[code], got, expected(a, b, code)))
    return failures

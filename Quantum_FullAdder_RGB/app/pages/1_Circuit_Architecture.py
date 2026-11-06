"""
Page 2: Reversible Circuit Architectures & Live Simulator
=========================================================
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from PIL import Image

from config import CIRCUITS_RESULTS_DIR
from circuits.baseline_fulladder import build_baseline_fulladder, simulate_baseline_fulladder
from circuits.peres_fulladder import build_peres_fulladder, simulate_peres_fulladder
from circuits.optimized_fulladder import build_optimized_fulladder, simulate_optimized_fulladder
from circuits.baseline_4bit_adder import build_baseline_4bit_adder_circuit, simulate_baseline_4bit
from circuits.optimized_4bit_adder import build_optimized_4bit_adder_circuit, simulate_optimized_4bit
from circuits.circuit_utils import get_circuit_resources

st.set_page_config(page_title="Circuit Architecture - Quantum Adder", page_icon="📐", layout="wide")

st.title("📐 Quantum Reversible Circuit Architecture")
st.markdown("Detailed mathematical formulations, qubit allocations, gate breakdowns, and interactive circuit simulations.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Circuit A: Baseline 1-Bit",
    "Circuit B: Peres 1-Bit",
    "Circuit C: Optimized 1-Bit",
    "4-Bit Baseline Architecture",
    "4-Bit Optimized Architecture"
])

# ----------------- Tab 1: Baseline 1-Bit -----------------
with tab1:
    st.subheader("Circuit A: Baseline Toffoli-CNOT Reversible Full Adder")
    col_a1, col_a2 = st.columns([3, 2])
    with col_a1:
        st.markdown("""
        **Mathematical Equations:**
        - $\\text{Sum} = A \\oplus B \\oplus C_{in}$
        - $C_{out} = AB \\oplus (A \\oplus B)C_{in} = AB \\oplus AC_{in} \\oplus BC_{in}$

        **Qubit Allocation (5 Qubits):**
        - `q[0]`: Input $A$ (Preserved)
        - `q[1]`: Input $B$ (Preserved via CNOT uncomputation)
        - `q[2]`: Input $C_{in}$ (Preserved)
        - `q[3]`: Ancilla $|0\\rangle \\to C_{out}$
        - `q[4]`: Ancilla $|0\\rangle \\to \\text{Sum}$

        **Gate Sequence:**
        1. `CCX(q[0], q[1], q[3])` : Compute $AB$
        2. `CX(q[0], q[1])` : Propagate $A \\oplus B$
        3. `CCX(q[1], q[2], q[3])` : Complete $C_{out} = AB \\oplus (A\\oplus B)C_{in}$
        4. `CX(q[1], q[4])` : Copy propagate term
        5. `CX(q[2], q[4])` : Complete $\\text{Sum} = A \\oplus B \\oplus C_{in}$
        6. `CX(q[0], q[1])` : Restore $B = (A \\oplus B) \\oplus A$
        """)
        m_base = get_circuit_resources(build_baseline_fulladder())
        st.info(f"**Metrics:** Total Qubits: 5 | Gates: {m_base['total_gates']} (2 CCX, 4 CX) | Depth: {m_base['circuit_depth']} | NCV Cost: {m_base['quantum_cost']}")

    with col_a2:
        img_path = CIRCUITS_RESULTS_DIR / "baseline_fulladder.png"
        if img_path.exists():
            st.image(str(img_path), caption="Baseline Reversible Full Adder Schematic", use_container_width=True)

# ----------------- Tab 2: Peres 1-Bit -----------------
with tab2:
    st.subheader("Circuit B: Peres Gate-Based Reversible Full Adder")
    col_b1, col_b2 = st.columns([3, 2])
    with col_b1:
        st.markdown("""
        **Peres Gate Transformation:**
        $$P(A, B, C) = (A, A \\oplus B, AB \\oplus C)$$
        Realized with 1 Toffoli and 1 CNOT gate (NCV Cost = 4 in Peres macro).

        **Full Adder Cascade (2 Peres Gates):**
        - **Gate 1** $P_1(A, B, 0) \\to (A, A\\oplus B, AB)$
        - **Gate 2** $P_2(A\\oplus B, C_{in}, AB) \\to (A\\oplus B, \\text{Sum}, C_{out})$
          - $C_{out} = (A\\oplus B)C_{in} \\oplus AB$
          - $\\text{Sum} = (A\\oplus B) \\oplus C_{in}$

        **Qubit Allocation (4 Qubits):**
        - `q[0]`: Input $A$ (Preserved)
        - `q[1]`: Input $B \\to A \\oplus B$ (Garbage output)
        - `q[2]`: Input $C_{in} \\to \\text{Sum}$
        - `q[3]`: Ancilla $|0\\rangle \\to C_{out}$
        """)
        m_peres = get_circuit_resources(build_peres_fulladder())
        st.info(f"**Metrics:** Total Qubits: 4 | Gates: 4 (2 CCX, 2 CX) | Depth: {m_peres['circuit_depth']} | NCV Cost: 12 (8 in Peres metric)")

    with col_b2:
        img_path = CIRCUITS_RESULTS_DIR / "peres_fulladder.png"
        if img_path.exists():
            st.image(str(img_path), caption="Peres-Based Full Adder Schematic", use_container_width=True)

# ----------------- Tab 3: Optimized 1-Bit -----------------
with tab3:
    st.subheader("Circuit C: Optimized Reversible Full Adder (with Restoration)")
    col_c1, col_c2 = st.columns([3, 2])
    with col_c1:
        st.markdown("""
        **Optimization Rationale:**
        Combines the compact 4-qubit layout of the Peres cascade with a zero-garbage uncomputing CNOT gate
        `CX(q[0], q[1])` to restore input $B$.

        **Resource Comparison vs Baseline:**
        - **Qubit Reduction:** 4 qubits vs 5 (-20.0%)
        - **Gate Reduction:** 5 gates vs 6 (-16.7%)
        - **NCV Cost Reduction:** 13 vs 14 (-7.1% in primitive; 9 vs 14 = -35.7% in Peres macro)
        - **Preserved Inputs:** Both $A$ and $B$ are 100% preserved!
        """)
        m_opt = get_circuit_resources(build_optimized_fulladder(restore_b=True))
        st.success(f"**Optimized Metrics:** Total Qubits: 4 | Gates: {m_opt['total_gates']} | Depth: {m_opt['circuit_depth']} | NCV Cost: {m_opt['quantum_cost']}")

    with col_c2:
        img_path = CIRCUITS_RESULTS_DIR / "optimized_fulladder.png"
        if img_path.exists():
            st.image(str(img_path), caption="Optimized Full Adder with B-Restoration Schematic", use_container_width=True)

# ----------------- Tab 4 & 5: 4-Bit Architectures -----------------
with tab4:
    st.subheader("Baseline 4-Bit Ripple-Carry Adder-Subtractor")
    st.markdown("""
    - **Total Qubits:** 18 (1 Mode $M$, 4 $A$, 4 $B$, 4 Result $R$, 1 $C_{out}$, 4 Intermediate Carry Ancillas $C_0..C_3$)
    - **Gate Count:** 50 gates (36 CX, 14 CCX)
    - **Quantum Cost:** 106
    - **Carry Uncomputation:** Standard Bennett uncomputation backward pass.
    """)
    img_path = CIRCUITS_RESULTS_DIR / "baseline_4bit_adder.png"
    if img_path.exists():
        st.image(str(img_path), caption="Baseline 4-Bit Adder-Subtractor", use_container_width=True)

with tab5:
    st.subheader("Optimized 4-Bit Adder-Subtractor (Peres Carry-Pipeline)")
    st.markdown("""
    - **Total Qubits:** 18 (9 preserved inputs, 5 outputs, 4 intermediate carries 100% restored to $|0\\rangle$)
    - **Gate Count:** 40 gates (26 CX, 14 CCX) — **20.0% Reduction (10 fewer CNOT gates!)**
    - **Quantum Cost:** 96 (vs 106) — **9.43% Reduction!**
    - **Circuit Depth:** 24 (vs 32) — **25.0% Reduction!**
    - **Mechanism:** Maintains $B[i]$ in propagate state $A[i] \\oplus B[i]$, saves 1 CX per sum bit, and combines backward uncomputation with $B$-restoration in a synchronized sweep.
    """)
    img_path = CIRCUITS_RESULTS_DIR / "optimized_4bit_adder.png"
    if img_path.exists():
        st.image(str(img_path), caption="Optimized 4-Bit Adder-Subtractor", use_container_width=True)

st.markdown("---")

# Interactive Simulator Section
st.subheader("🧪 Interactive Quantum Circuit Simulator")
st.write("Run real basis-state quantum simulations using Qiskit Aer on the selected inputs.")

sim_type = st.radio("Select Circuit to Simulate:", ["1-Bit Full Adder", "4-Bit Adder-Subtractor"], horizontal=True)

if sim_type == "1-Bit Full Adder":
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        sim_a = st.selectbox("Input A:", [0, 1], index=1)
    with col_s2:
        sim_b = st.selectbox("Input B:", [0, 1], index=1)
    with col_s3:
        sim_cin = st.selectbox("Input Cin:", [0, 1], index=0)
    with col_s4:
        sim_arch = st.selectbox("Adder Type:", ["Baseline (5-Qubit)", "Peres (4-Qubit)", "Optimized (4-Qubit Restored)"])

    if st.button("🚀 Execute 1-Bit Circuit Simulation"):
        with st.spinner("Simulating circuit on Qiskit Aer..."):
            if "Baseline" in sim_arch:
                res = simulate_baseline_fulladder(sim_a, sim_b, sim_cin)
            elif "Peres" in sim_arch:
                res = simulate_peres_fulladder(sim_a, sim_b, sim_cin)
            else:
                res = simulate_optimized_fulladder(sim_a, sim_b, sim_cin, restore_b=True)

            st.write("### Simulation Results:")
            res_col1, res_col2, res_col3, res_col4 = st.columns(4)
            with res_col1:
                st.metric("Sum Output", res["output_sum"], delta="Expected: " + str(res["expected_sum"]))
            with res_col2:
                st.metric("Cout Output", res["output_cout"], delta="Expected: " + str(res["expected_cout"]))
            with res_col3:
                st.metric("Preserved A", res["preserved_a"])
            with res_col4:
                st.metric("Status", "CORRECT ✅" if res["is_correct"] else "INCORRECT ❌")

else:
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        sim_mode = st.selectbox("Mode M:", [0, 1], format_func=lambda x: "0 (Addition: A + B)" if x == 0 else "1 (Subtraction: A - B)")
    with col_m2:
        val_a = st.slider("Input A (0-15):", 0, 15, 11)
    with col_m3:
        val_b = st.slider("Input B (0-15):", 0, 15, 6)
    with col_m4:
        arch_4 = st.selectbox("4-Bit Architecture:", ["Optimized (40 Gates)", "Baseline (50 Gates)"])

    if st.button("🚀 Execute 4-Bit Circuit Simulation"):
        with st.spinner("Executing 18-qubit quantum circuit..."):
            if "Optimized" in arch_4:
                res = simulate_optimized_4bit(sim_mode, val_a, val_b)
            else:
                res = simulate_baseline_4bit(sim_mode, val_a, val_b)

            st.write("### 4-Bit Simulation Results:")
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                st.metric("Result R", f"{res['output_r']} (Binary: {format(res['output_r'], '04b')})")
            with rc2:
                if sim_mode == 0:
                    st.metric("Carry Out", res["output_cout"])
                else:
                    st.metric("Borrow", res["borrow"])
            with rc3:
                st.metric("Inputs Preserved", f"A={res['preserved_a']}, B={res['preserved_b']}")
            with rc4:
                st.metric("Ancillas Clean", "100% |0> Restored" if res["ancillas_restored"] else "Dirty Ancillas")

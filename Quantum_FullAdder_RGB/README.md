# Design and Performance Analysis of an Optimized Reversible Quantum Full Adder for RGB Image Processing Using Qiskit

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Qiskit 2.6](https://img.shields.io/badge/Qiskit-2.6.1-purple.svg)](https://qiskit.org/)
[![Pytest 9.2](https://img.shields.io/badge/Pytest-145%20Passed-brightgreen.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Project Abstract
Energy dissipation in conventional digital arithmetic circuits presents a fundamental barrier to modern high-performance microelectronics. Reversible computing provides an information-conserving alternative where computational steps are strictly bijective and dissipate no heat under ideal thermodynamic limits. This research project presents the design, resource analysis, formal exhaustive verification, and practical application of an **Optimized Reversible Quantum Full Adder and 4-Bit Ripple-Carry Adder-Subtractor** implemented in **Qiskit 2.6.1**. The circuit is evaluated both analytically and empirically through color channel arithmetic in RGB digital image processing, demonstrating **100% reversible pixel recovery** and measurable hardware resource reductions.

---

## 2. Introduction
In classical CMOS logic, basic gates such as AND, OR, and NAND are irreversible: they map multiple input bit configurations to a single output bit, destroying entropy. In contrast, quantum computation utilizes unitary operators ($U^\dagger U = I$), necessitating reversible logic circuits where all input states can be recovered from the output states. This project designs and compares multiple reversible adder topologies, benchmarks their efficiency under the NCV gate cost model, and demonstrates their utility in digital image processing pipelines.

---

## 3. Research Problem
Conventional classical addition discards carry propagation histories and intermediate operand states, destroying information and generating thermal dissipation according to Landauer's thermodynamic bound. Existing reversible full adders often suffer from:
1. Excessive ancilla qubit overhead (allocating clean qubits without uncomputation).
2. Proliferation of garbage outputs (entangled dead bits that cannot be reused).
3. Redundant intermediate gate uncomputations in multi-bit adder-subtractors.

This project addresses these challenges by synthesizing an **Optimized Reversible Full Adder** and a **4-Bit Adder-Subtractor** that reduce total gate count, CNOT count, circuit depth, and quantum cost while guaranteeing 100% uncomputation of intermediate ancillas.

---

## 4. Project Objectives
1. **Circuit Synthesis**: Construct Baseline (Toffoli-CNOT), Peres-based, and Optimized reversible full adders.
2. **Multi-Bit Arithmetic**: Construct Baseline and Optimized 4-bit ripple-carry adder-subtractors with mode control ($M=0$: Addition, $M=1$: Subtraction).
3. **Formal Verification**: Verify all 8 computational basis states for 1-bit full adders and all 512 input combinations for 4-bit adder-subtractors in Qiskit Aer.
4. **Benchmarking**: Quantify total qubits, gate counts, CNOT counts, Toffoli counts, circuit depth, and quantum cost under the NCV model.
5. **RGB Image Processing**: Quantize 8-bit digital color channels to 4-bit depth, execute quantum channel addition and subtraction, and prove exact lossless image recovery ($((A + B) - B) \bmod 16 = A_{quantized}$).

---

## 5. Reversible Logic Theory
According to **Landauer's Principle**, erasing one bit of digital information dissipates at least:
$$\Delta Q = k_B T \ln 2$$
where $k_B$ is Boltzmann's constant and $T$ is absolute temperature.

**Bennett's Theorem** proved that zero energy dissipation is theoretically achievable if computations are performed reversibly. For a quantum circuit represented by unitary matrix $U$, the mapping is bijective:
$$|\psi_{out}\rangle = U |\psi_{in}\rangle \implies |\psi_{in}\rangle = U^\dagger |\psi_{out}\rangle$$

---

## 6. Full-Adder Equations
For binary operands $A, B \in \{0, 1\}$ and input carry $C_{in} \in \{0, 1\}$:
$$\text{Sum} = A \oplus B \oplus C_{in}$$
$$C_{out} = AB \oplus AC_{in} \oplus BC_{in} = AB \oplus (A \oplus B)C_{in}$$

In reversible logic:
- The circuit must produce both $\text{Sum}$ and $C_{out}$.
- The input bits ($A, B, C_{in}$) must be preserved or uncomputed without information loss.

---

## 7. Peres Gate Theory
A Peres Gate $P(A, B, C)$ is an equal-input, equal-output $3 \times 3$ reversible gate defined by:
$$P(A, B, C) = (A, A \oplus B, AB \oplus C)$$

In elementary gates, a Peres gate consists of:
1. `CCX(A, B, C)`: $C \to AB \oplus C$
2. `CX(A, B)`: $B \to A \oplus B$

While a naive Toffoli + CNOT implementation costs $5 + 1 = 6$, in the NCV decomposition model the Peres gate can be directly synthesized with 4 elementary 2-qubit gates (Quantum Cost = 4).

---

## 8. Baseline Circuit Architecture
The Baseline Toffoli-CNOT Full Adder utilizes 5 qubits:
- Input Qubits: $q_0 = A, q_1 = B, q_2 = C_{in}$
- Ancilla / Output Qubits: $q_3 = |0\rangle \to C_{out}, q_4 = |0\rangle \to \text{Sum}$
- Gate Sequence:
  1. `CCX(0, 1, 3)`
  2. `CX(0, 1)`
  3. `CCX(1, 2, 3)`
  4. `CX(1, 4)`
  5. `CX(2, 4)`
  6. `CX(0, 1)` (restores input $B$)
- Metrics: 5 Qubits, 6 Gates (2 CCX, 4 CX), Depth = 5, NCV Quantum Cost = 14.

---

## 9. Optimized Circuit Architecture
The Optimized Reversible Full Adder utilizes a 4-qubit layout by cascading two Peres transformations:
- $P_1(A, B, 0) \to (A, A \oplus B, AB)$
- $P_2(A \oplus B, C_{in}, AB) \to (A \oplus B, \text{Sum}, C_{out})$
- Uncomputing step: `CX(0, 1)` restores input $B$.
- Metrics: 4 Qubits (-20.0%), 5 Gates (-16.7%), Depth = 5, NCV Cost = 13 (or 9 in Peres macro).
- Preserves both $A$ and $B$, leaves zero garbage on $B$, and eliminates 1 ancilla qubit.

---

## 10. Four-Bit Adder-Subtractor
Inputs: $M \in \{0, 1\}$ (Mode), $A = A_3 A_2 A_1 A_0$, $B = B_3 B_2 B_1 B_0$.
Outputs: $R = R_3 R_2 R_1 R_0$, $C_{out}$, and clean uncomputed ancillas $C_0..C_3 = |0\rangle$.

- **Addition ($M=0$):**
  $$R = (A + B) \bmod 16, \quad C_{out} = (A + B) // 16$$
- **Subtraction ($M=1$):**
  Two's complement logic: $A - B = A + (\sim B) + 1$.
  $B_{eff}[i] = B[i] \oplus M$, $C_0 = M = 1$.
  $$R = (A - B) \bmod 16, \quad \text{Borrow} = 1 \oplus C_{out}$$

### Baseline vs Optimized 4-Bit Implementation:
- **Baseline:** Immediate uncomputation of $B[i]$ after each carry stage $\implies$ 50 gates (36 CX, 14 CCX), Depth = 32, Cost = 106.
- **Optimized:** Pipelined Peres propagate ripple; extracts sum bits using only 2 CX per bit; synchronizes backward carry uncomputation with $B$-restoration $\implies$ **40 gates (26 CX, 14 CCX)**, **Depth = 24 (-25.0%)**, **Cost = 96 (-9.43%)**.

---

## 11. Quantum-Cost Calculation (NCV Model)
The NCV model evaluates quantum cost by decomposing circuits into elementary 1-qubit and 2-qubit operations:
- NOT ($X$): 1
- CNOT ($CX$): 1
- Controlled-$V$ / Controlled-$V^\dagger$: 1
- Toffoli ($CCX$): 5 (decomposed into 2 CNOTs + 1 $V$ + 2 $V^\dagger$)
- Peres Gate: 4

---

## 12. RGB Image Processing
Digital color images in PNG, JPG, or JPEG formats are processed channel-by-channel:
1. Classical loading and resolution normalization using Pillow.
2. 2D decomposition into Red, Green, and Blue channels.
3. 4-bit uniform quantization.
4. Channel arithmetic via the verified Quantum Lookup Table.
5. Reassembly and 8-bit dynamic range reconstruction.

---

## 13. Quantization
- Forward Quantization (8-bit to 4-bit):
  $$q = \lfloor \text{pixel\_value} / 16 \rfloor \in [0, 15]$$
- Reconstruction (4-bit to 8-bit):
  $$\text{reconstructed} = q \times 17 \in [0, 255]$$
Quantization from 256 down to 16 levels introduces bounded quantization noise (~30-35 dB PSNR). Subsequent quantum arithmetic is 100% lossless.

---

## 14. Experimental Methodology
1. **Simulation Platform**: Qiskit Aer 0.18.2 basis-state simulation.
2. **Deterministic Lookups**: Quantum Lookup Table pre-computed across all 512 operations $(M, A, B)$ directly from Qiskit circuit outputs.
3. **Unitary Reversibility**: Evaluating $U^\dagger U |\psi\rangle = |\psi\rangle$ across computational basis states.

---

## 15. Performance Comparison

| Metric | 1-Bit Baseline | 1-Bit Optimized | 1-Bit Reduction | 4-Bit Baseline | 4-Bit Optimized | 4-Bit Reduction |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Total Qubits** | 5 | 4 | **-20.0%** | 18 | 18 | 0.0% |
| **Ancilla Qubits** | 2 | 1 | **-50.0%** | 4 | 4 | 0.0% |
| **Garbage Outputs**| 0 | 0 | 0.0% | 0 | 0 | 0.0% |
| **Total Gate Count**| 6 | 5 | **-16.7%** | 50 | 40 | **-20.0%** |
| **CNOT Count** | 4 | 3 | **-25.0%** | 36 | 26 | **-27.8%** |
| **Toffoli Count** | 2 | 2 | 0.0% | 14 | 14 | 0.0% |
| **Circuit Depth** | 5 | 5 | 0.0% | 32 | 24 | **-25.0%** |
| **Quantum Cost (NCV)**| 14 | 13 (9 macro) | **-7.1% (-35.7%)** | 106 | 96 | **-9.43%** |

Both the 1-bit and 4-bit optimized designs demonstrate strictly lower total gate count AND lower quantum cost, satisfying the optimization acceptance criteria.

---

## 16. Verification Results
- **1-Bit Full Adder:** 8 / 8 cases PASSED (100%).
- **4-Bit Adder-Subtractor:** 512 / 512 cases PASSED (100%).
- **Ancilla Cleanup:** 512 / 512 operations with 100% $|0\rangle$ carry restoration.
- **Unitary Inversion ($U^\dagger U = I$):** 32 / 32 basis states verified.
- **Automated Tests:** 145 / 145 pytest unit tests PASSED.

---

## 17. Image Quality Analysis
Evaluation on sample images:
- **Quantization Loss (8-bit vs 4-bit):** PSNR $\approx 31.8$ dB, SSIM $\approx 0.942$.
- **Arithmetic Recovery ($((A + B) - B) \bmod 16$ vs $A_{quantized}$):**
  - **MSE = 0.0000**
  - **PSNR = 100.00 dB (Lossless Perfect Match)**
  - **SSIM = 1.0000 (Identical Structure)**
  - **Pixel Fidelity = 100.0%**

---

## 18. Installation Instructions

```bash
# Clone or navigate to the repository
cd Quantum_FullAdder_RGB

# Create and activate Python 3.12 virtual environment
python -m venv .venv
.\.venv\Scripts\activate  # On Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

---

## 19. Execution Commands

```bash
# 1. Run all unit tests (145 tests)
python -m pytest tests -v

# 2. Run formal verification scripts
python verification/verify_fulladder.py
python verification/verify_4bit.py
python verification/verify_ancilla.py
python verification/verify_reversibility.py
python verification/verify_image_recovery.py

# 3. Generate performance metrics, comparisons, and charts
python performance/comparison.py
python performance/visualization.py

# 4. Launch Streamlit Multi-Page Web Application
streamlit run app/streamlit_app.py
```

---

## 20. Limitations and Future Scope
- **Current Limitations:** Quantization from 8-bit to 4-bit is lossy due to the 4-bit register width. Full 8-bit quantum adders require 34 qubits, exceeding classical desktop statevector limits.
- **Future Scope:** Implement fault-tolerant quantum error correction (surface codes), synthesize 8-bit ripple-carry adders using Clifford+T decompositions, and benchmark against real noisy quantum backends via IBM Quantum.

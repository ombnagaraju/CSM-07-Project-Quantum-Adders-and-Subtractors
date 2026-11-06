# Quantum Full Adder RGB

**Design and Performance Analysis of an Optimized Reversible Quantum Full Adder for
RGB Image Processing Using Qiskit**

This folder is the reproducible research package for the CSM-07 project. It contains the
reversible adder/subtractor circuits, the verification suite, the post-transpilation
benchmark, the RGB image pipeline and the Streamlit application.

## Quick start

```bash
python -m pip install -r Quantum_FullAdder_RGB/requirements.lock.txt
python Quantum_FullAdder_RGB/repro/run_all.py       # regenerates every CSV and chart
python -m pytest Quantum_FullAdder_RGB/tests -v     # runs the test suite
streamlit run Quantum_FullAdder_RGB/app/streamlit_app.py
```

Everything is simulated with Qiskit Aer. **No real quantum hardware was used and no
hardware result is claimed.**

## Layout

| Folder | Contents |
| --- | --- |
| `circuits/` | Baseline, Peres, optimized full adders; 4-bit adder-subtractor; one-control-qubit shared design; uncomputation; parameterised n-bit; 2-bit ALU slice |
| `verification/` | Exhaustive truth-table, reversibility, ancilla and garbage checks |
| `transpilation/` | Line / grid / heavy-hex topologies, post-transpile cost report, decomposition selector |
| `performance/` | Gate count, quantum cost, depth, scaling law, fault-tolerant cost, energy model |
| `benchmark/` | Published fair-comparison protocol, metric code, open circuit set, leaderboard |
| `mitigation/` | Zero-noise extrapolation on arithmetic outputs |
| `image_processing/` | Loading, RGB split, 4-bit quantisation, quantum lookup table, add/subtract/recover, MSE/PSNR/SSIM |
| `app/` | Streamlit application, eight pages |
| `notebooks/` | Eleven teaching notebooks |
| `repro/` | One-command regeneration, seeds, job logs |
| `results/` | Generated CSVs, charts, circuit images, processed images, reports, logs |

## Research contributions

1. **One control qubit for addition and subtraction** — measured ancilla, gate and depth
   saving against separate circuits, after transpilation on a fixed topology.
2. **Post-transpilation benchmarking across topologies** — line, grid and heavy-hex.
3. **Scaling law for cost versus bit-width** — fitted gate count and depth against `n`
   with confidence intervals.
4. **Hardware-aware decomposition choice** — low-depth versus low-T-count Toffoli costed
   from backend error rates. Measured: Qiskit 2.5.2 ANC-clean syntheses (v24 and hp24) both
   need 7 T-equivalent gates, so the low-T variant gives no T saving and the selector
   rejects it in favour of the strictly shallower low-depth synthesis.
5. **Fair comparison protocol** — one gate library, one metric code, one topology.
6. **Garbage minimisation by uncomputation.**
7. **Fault-tolerant cost estimate** — T-count and Toffoli depth.
8. **Open benchmark for reversible arithmetic** — circuits plus metric code.
9. **Error mitigation (stretch)** — zero-noise extrapolation, including the cases where
   it does not help.
10. **Small ALU slice (stretch)** — two-bit ALU embedding the adder-subtractor.
11. **Energy figures only with a stated Landauer model** — no unsupported claims.
12. **Reproducibility package** — pinned versions, seeds, job logs.

Full documentation, equations and measured results are in the expanded README generated
by `repro/run_all.py`.

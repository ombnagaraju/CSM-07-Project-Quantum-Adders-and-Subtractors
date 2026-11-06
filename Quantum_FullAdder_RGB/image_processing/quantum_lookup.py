"""
Quantum Lookup Table Generation Module
======================================

Constructs and caches the verified 4-bit arithmetic lookup tables by
executing the actual Qiskit quantum circuits across all 512 input combinations.

Architecture:
-------------
- Executes the verified Qiskit 4-bit Adder-Subtractor circuit for:
    Mode M in {0, 1} (Addition vs Subtraction)
    A in [0, 15]
    B in [0, 15]
- Verifies and caches the output result R, carry, and borrow for all 512 cases.
- Persists verified tables to results/quantum_lut.npz so subsequent lookups
  execute instantly (< 1 ms) without repeating 512 dense quantum simulations.
"""

from typing import Tuple, Dict, Any
from pathlib import Path
import numpy as np

from config import RESULTS_DIR
from circuits.optimized_4bit_adder import simulate_optimized_4bit

CACHE_PATH = RESULTS_DIR / "quantum_lut.npz"


class QuantumLookupTable:
    """
    Verified Quantum Arithmetic Lookup Table populated strictly
    by running Qiskit quantum circuit simulations and cached to disk.
    """
    _instance = None

    def __init__(self, force_regenerate: bool = False):
        self.add_lut = np.zeros((16, 16), dtype=np.uint8)
        self.carry_lut = np.zeros((16, 16), dtype=np.uint8)
        self.sub_lut = np.zeros((16, 16), dtype=np.uint8)
        self.borrow_lut = np.zeros((16, 16), dtype=np.uint8)
        self.is_populated = False

        if not force_regenerate and CACHE_PATH.exists():
            self._load_from_cache()
        else:
            self._populate_from_quantum_circuits()
            self._save_to_cache()

    def _load_from_cache(self) -> None:
        """Load pre-simulated and verified tables from disk."""
        data = np.load(CACHE_PATH)
        self.add_lut = data["add_lut"]
        self.carry_lut = data["carry_lut"]
        self.sub_lut = data["sub_lut"]
        self.borrow_lut = data["borrow_lut"]
        self.is_populated = True

    def _save_to_cache(self) -> None:
        """Save verified tables to disk."""
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            CACHE_PATH,
            add_lut=self.add_lut,
            carry_lut=self.carry_lut,
            sub_lut=self.sub_lut,
            borrow_lut=self.borrow_lut
        )

    def _populate_from_quantum_circuits(self) -> None:
        """Execute Qiskit Aer simulations for all 512 combinations."""
        for m in [0, 1]:
            for a in range(16):
                for b in range(16):
                    sim_result = simulate_optimized_4bit(m, a, b)
                    if not sim_result["is_correct"]:
                        raise RuntimeError(f"Quantum simulation failed at M={m}, A={a}, B={b}")

                    r = sim_result["output_r"]
                    cout = sim_result["output_cout"]
                    borrow = sim_result["borrow"]

                    if m == 0:
                        self.add_lut[a, b] = r
                        self.carry_lut[a, b] = cout
                    else:
                        self.sub_lut[a, b] = r
                        self.borrow_lut[a, b] = borrow

        self.is_populated = True

    def query_addition(self, a_channel: np.ndarray, b_channel: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Apply quantum-verified addition on 4-bit arrays."""
        sum_channel = self.add_lut[a_channel, b_channel]
        carry_channel = self.carry_lut[a_channel, b_channel]
        return sum_channel, carry_channel

    def query_subtraction(self, a_channel: np.ndarray, b_channel: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Apply quantum-verified subtraction on 4-bit arrays."""
        diff_channel = self.sub_lut[a_channel, b_channel]
        borrow_channel = self.borrow_lut[a_channel, b_channel]
        return diff_channel, borrow_channel


# Global instance
_GLOBAL_QLUT = None


def get_quantum_lut(force_regenerate: bool = False) -> QuantumLookupTable:
    """Retrieve or initialize the global verified Quantum Lookup Table."""
    global _GLOBAL_QLUT
    if _GLOBAL_QLUT is None or force_regenerate:
        _GLOBAL_QLUT = QuantumLookupTable(force_regenerate=force_regenerate)
    return _GLOBAL_QLUT

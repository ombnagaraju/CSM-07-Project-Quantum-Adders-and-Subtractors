"""
Configuration Module for Quantum Full Adder RGB Image Processing Project
========================================================================

Centralized configuration file defining project paths, quantum circuit
specifications, quantization constants, and quantum cost parameters.
"""

from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent
CIRCUITS_DIR = PROJECT_ROOT / "circuits"
VERIFICATION_DIR = PROJECT_ROOT / "verification"
IMAGE_PROCESSING_DIR = PROJECT_ROOT / "image_processing"
PERFORMANCE_DIR = PROJECT_ROOT / "performance"
APP_DIR = PROJECT_ROOT / "app"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
TESTS_DIR = PROJECT_ROOT / "tests"
RESULTS_DIR = PROJECT_ROOT / "results"
SAMPLE_IMAGES_DIR = PROJECT_ROOT / "sample_images"

# Results Subdirectories
CSV_DIR = RESULTS_DIR / "csv"
CHARTS_DIR = RESULTS_DIR / "charts"
CIRCUITS_RESULTS_DIR = RESULTS_DIR / "circuits"
PROCESSED_IMAGES_DIR = RESULTS_DIR / "processed_images"
REPORTS_DIR = RESULTS_DIR / "reports"

# Ensure all result directories exist
for directory in [CSV_DIR, CHARTS_DIR, CIRCUITS_RESULTS_DIR, PROCESSED_IMAGES_DIR, REPORTS_DIR, SAMPLE_IMAGES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Quantum Arithmetic Constants
BIT_WIDTH = 4
MAX_VAL = (1 << BIT_WIDTH) - 1  # 15
TOTAL_COMBINATIONS_1BIT = 8      # 2^3
TOTAL_COMBINATIONS_4BIT = 512    # 16 * 16 * 2 (A=0..15, B=0..15, M=0..1)

# Quantization Constants
QUANTIZATION_BITS = 4
QUANTIZATION_LEVELS = 16
QUANTIZATION_FACTOR = 16  # q = floor(pixel / 16)
RECONSTRUCTION_FACTOR = 17  # pixel = q * 17

# Supported Image Extensions
SUPPORTED_IMAGE_FORMATS = (".png", ".jpg", ".jpeg")
DEFAULT_IMAGE_SIZE = (64, 64)

# Quantum Cost (NCV Model)
GATE_COSTS = {
    "x": 1,
    "cx": 1,
    "v": 1,
    "v_dag": 1,
    "ccx": 5,
    "peres": 4,
}

# CSV Filenames
CSV_FULLADDER_VERIFY = CSV_DIR / "fulladder_verification.csv"
CSV_FOURBIT_VERIFY = CSV_DIR / "four_bit_verification.csv"
CSV_ANCILLA_VERIFY = CSV_DIR / "ancilla_verification.csv"
CSV_REVERSIBILITY_VERIFY = CSV_DIR / "reversibility_verification.csv"
CSV_IMAGE_RECOVERY = CSV_DIR / "image_recovery_verification.csv"

CSV_BASELINE_METRICS = CSV_DIR / "baseline_metrics.csv"
CSV_OPTIMIZED_METRICS = CSV_DIR / "optimized_metrics.csv"
CSV_GATE_COMPARISON = CSV_DIR / "gate_comparison.csv"
CSV_QUANTUM_COST_COMPARISON = CSV_DIR / "quantum_cost_comparison.csv"
CSV_CIRCUIT_DEPTH_COMPARISON = CSV_DIR / "circuit_depth_comparison.csv"
CSV_IMAGE_METRICS = CSV_DIR / "image_metrics.csv"

# Chart Filenames
CHART_GATE_COMPARISON = CHARTS_DIR / "gate_count_comparison.png"
CHART_QUANTUM_COST = CHARTS_DIR / "quantum_cost_comparison.png"
CHART_CIRCUIT_DEPTH = CHARTS_DIR / "circuit_depth_comparison.png"
CHART_RESOURCE_SUMMARY = CHARTS_DIR / "resource_summary.png"

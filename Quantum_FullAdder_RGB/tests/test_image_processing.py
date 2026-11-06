"""
Unit Tests for RGB Image Processing Module
==========================================

Tests:
  - Synthetic sample image generation
  - 8-bit to 4-bit quantization and 4-bit to 8-bit reconstruction
  - Quantum lookup table operations
  - Quantum RGB image addition
  - Quantum RGB image subtraction
  - Lossless quantum image recovery ((A + B) - B) mod 16 == A_quantized
  - Metric calculations (MSE, PSNR, SSIM)
"""

import pytest
import sys
from pathlib import Path
from PIL import Image
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import SAMPLE_IMAGES_DIR, DEFAULT_IMAGE_SIZE
from image_processing.image_loader import generate_sample_images, load_and_preprocess_pair
from image_processing.quantization import quantize_channel, reconstruct_channel, quantize_and_reconstruct
from image_processing.quantum_lookup import get_quantum_lut
from image_processing.image_addition import perform_image_addition
from image_processing.image_subtraction import perform_image_subtraction
from image_processing.image_recovery import run_full_recovery_cycle
from image_processing.image_metrics import calculate_mse, calculate_psnr, calculate_ssim


@pytest.fixture
def sample_pair():
    path_a = SAMPLE_IMAGES_DIR / "image_a.png"
    path_b = SAMPLE_IMAGES_DIR / "image_b.png"
    if not path_a.exists() or not path_b.exists():
        generate_sample_images(SAMPLE_IMAGES_DIR, size=(32, 32))
    return load_and_preprocess_pair(path_a, path_b, target_size=(32, 32))


def test_quantization_bounds():
    arr_8bit = np.array([0, 15, 16, 31, 240, 255], dtype=np.uint8)
    q_4bit = quantize_channel(arr_8bit)
    expected_q = np.array([0, 0, 1, 1, 15, 15], dtype=np.uint8)
    assert np.array_equal(q_4bit, expected_q)

    recon_8bit = reconstruct_channel(q_4bit)
    expected_recon = np.array([0, 0, 17, 17, 255, 255], dtype=np.uint8)
    assert np.array_equal(recon_8bit, expected_recon)


def test_quantum_lookup_consistency():
    qlut = get_quantum_lut()
    for a in range(16):
        for b in range(16):
            add_val, carry = qlut.query_addition(np.array([a]), np.array([b]))
            sub_val, borrow = qlut.query_subtraction(np.array([a]), np.array([b]))
            assert add_val[0] == (a + b) % 16
            assert carry[0] == (a + b) // 16
            assert sub_val[0] == (a - b) % 16
            assert borrow[0] == (1 if a < b else 0)


def test_quantum_image_addition_subtraction(sample_pair):
    img_a, img_b = sample_pair
    add_img, add_meta = perform_image_addition(img_a, img_b)
    sub_img, sub_meta = perform_image_subtraction(img_a, img_b)

    assert isinstance(add_img, Image.Image)
    assert isinstance(sub_img, Image.Image)
    assert add_img.size == img_a.size
    assert sub_img.size == img_a.size


def test_quantum_image_lossless_recovery(sample_pair):
    img_a, img_b = sample_pair
    res = run_full_recovery_cycle(img_a, img_b)

    assert res["exact_match"] is True, "Quantum recovery must be 100% exact on quantized pixels"
    assert res["fidelity_pct"] == 100.0
    assert res["r_match"] is True
    assert res["g_match"] is True
    assert res["b_match"] is True

    quant_a = quantize_and_reconstruct(img_a)
    mse = calculate_mse(quant_a, res["recovered_image"])
    assert mse == 0.0, f"Expected 0.0 MSE between Quantized A and Recovered A, got {mse}"


def test_metrics_calculation(sample_pair):
    img_a, _ = sample_pair
    # Identity metrics
    assert calculate_mse(img_a, img_a) == 0.0
    assert calculate_psnr(img_a, img_a) == 100.0
    assert calculate_ssim(img_a, img_a) == 1.0

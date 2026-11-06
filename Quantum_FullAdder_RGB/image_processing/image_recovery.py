"""
Quantum Image Recovery Module
=============================

Demonstrates information conservation and reversibility in quantum RGB
image processing:
    Sum       = (A + B) mod 16
    Recovered = (Sum - B) mod 16 = ((A + B) - B) mod 16 = A_quantized

Verifies that the recovered quantized channels match the original quantized
input channels with 100.0% exact pixel-wise fidelity.
"""

from typing import Tuple, Dict, Any
from PIL import Image
import numpy as np

from image_processing.quantization import quantize_image, reconstruct_image
from image_processing.quantum_lookup import get_quantum_lut
from image_processing.image_addition import perform_image_addition


def recover_image(sum_image: Image.Image, img_b: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Recover Image A from sum_image by subtracting Image B via quantum subtraction.
    """
    # Quantize sum image and image B
    r_sum, g_sum, b_sum = quantize_image(sum_image)
    r_b, g_b, b_b = quantize_image(img_b)

    qlut = get_quantum_lut()
    r_rec, r_borrow = qlut.query_subtraction(r_sum, r_b)
    g_rec, g_borrow = qlut.query_subtraction(g_sum, g_b)
    b_rec, b_borrow = qlut.query_subtraction(b_sum, b_b)

    recovered_img = reconstruct_image(r_rec, g_rec, b_rec)

    meta = {
        "r_recovered": r_rec,
        "g_recovered": g_rec,
        "b_recovered": b_rec,
        "r_borrow": r_borrow,
        "g_borrow": g_borrow,
        "b_borrow": b_borrow
    }
    return recovered_img, meta


def run_full_recovery_cycle(img_a: Image.Image, img_b: Image.Image) -> Dict[str, Any]:
    """
    Execute full cycle:
      1. Add: (A + B) mod 16
      2. Subtract: ((A + B) - B) mod 16
      3. Verify exact equivalence against A_quantized
    """
    r_a_quant, g_a_quant, b_a_quant = quantize_image(img_a)
    r_b_quant, g_b_quant, b_b_quant = quantize_image(img_b)

    qlut = get_quantum_lut()
    # Step 1: Addition
    r_sum, r_carry = qlut.query_addition(r_a_quant, r_b_quant)
    g_sum, g_carry = qlut.query_addition(g_a_quant, g_b_quant)
    b_sum, b_carry = qlut.query_addition(b_a_quant, b_b_quant)
    sum_img = reconstruct_image(r_sum, g_sum, b_sum)

    # Step 2: Subtraction
    r_rec, r_borrow = qlut.query_subtraction(r_sum, r_b_quant)
    g_rec, g_borrow = qlut.query_subtraction(g_sum, g_b_quant)
    b_rec, b_borrow = qlut.query_subtraction(b_sum, b_b_quant)
    recovered_img = reconstruct_image(r_rec, g_rec, b_rec)

    # Step 3: Verification
    r_match = bool(np.array_equal(r_rec, r_a_quant))
    g_match = bool(np.array_equal(g_rec, g_a_quant))
    b_match = bool(np.array_equal(b_rec, b_a_quant))
    exact_match = (r_match and g_match and b_match)

    total_pixels = r_a_quant.size * 3
    matching_pixels = (
        int(np.sum(r_rec == r_a_quant)) +
        int(np.sum(g_rec == g_a_quant)) +
        int(np.sum(b_rec == b_a_quant))
    )
    fidelity_pct = (matching_pixels / total_pixels) * 100.0

    return {
        "sum_image": sum_img,
        "recovered_image": recovered_img,
        "r_match": r_match,
        "g_match": g_match,
        "b_match": b_match,
        "exact_match": exact_match,
        "fidelity_pct": fidelity_pct,
        "total_pixels_evaluated": total_pixels
    }

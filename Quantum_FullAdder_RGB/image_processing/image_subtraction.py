"""
Quantum RGB Image Subtraction Module
====================================

Performs channel-wise reversible quantum subtraction on two RGB images:
  R_out = (A_R - B_R) mod 16
  G_out = (A_G - B_G) mod 16
  B_out = (A_B - B_B) mod 16

Borrows are tracked separately for each color channel.
"""

from typing import Tuple, Dict, Any
from PIL import Image
import numpy as np

from image_processing.quantization import quantize_image, reconstruct_image
from image_processing.quantum_lookup import get_quantum_lut


def perform_image_subtraction(
    img_a: Image.Image,
    img_b: Image.Image
) -> Tuple[Image.Image, Dict[str, np.ndarray]]:
    """
    Perform 4-bit quantum subtraction: Image A - Image B.
    
    Returns:
      reconstructed_image: 8-bit RGB PIL Image
      metadata: Dictionary containing 4-bit diff and borrow channels
    """
    # 1. Classical extraction & 4-bit quantization
    r_a, g_a, b_a = quantize_image(img_a)
    r_b, g_b, b_b = quantize_image(img_b)

    # 2. Quantum lookup arithmetic
    qlut = get_quantum_lut()
    r_diff, r_borrow = qlut.query_subtraction(r_a, r_b)
    g_diff, g_borrow = qlut.query_subtraction(g_a, g_b)
    b_diff, b_borrow = qlut.query_subtraction(b_a, b_b)

    # 3. Classical 8-bit image reconstruction
    result_image = reconstruct_image(r_diff, g_diff, b_diff)

    metadata = {
        "r_diff": r_diff,
        "g_diff": g_diff,
        "b_diff": b_diff,
        "r_borrow": r_borrow,
        "g_borrow": g_borrow,
        "b_borrow": b_borrow,
        "r_a_quant": r_a,
        "g_a_quant": g_a,
        "b_a_quant": b_a,
        "r_b_quant": r_b,
        "g_b_quant": g_b,
        "b_b_quant": b_b
    }

    return result_image, metadata

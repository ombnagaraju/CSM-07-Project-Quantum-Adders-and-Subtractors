"""
Quantum RGB Image Addition Module
=================================

Performs channel-wise reversible quantum addition on two RGB images:
  R_out = (A_R + B_R) mod 16
  G_out = (A_G + B_G) mod 16
  B_out = (A_B + B_B) mod 16

Carries are tracked separately for each color channel.
"""

from typing import Tuple, Dict, Any
from PIL import Image
import numpy as np

from image_processing.quantization import quantize_image, reconstruct_image
from image_processing.quantum_lookup import get_quantum_lut


def perform_image_addition(
    img_a: Image.Image,
    img_b: Image.Image
) -> Tuple[Image.Image, Dict[str, np.ndarray]]:
    """
    Perform 4-bit quantum addition of Image A and Image B.
    
    Returns:
      reconstructed_image: 8-bit RGB PIL Image
      metadata: Dictionary containing 4-bit sum and carry channels
    """
    # 1. Classical extraction & 4-bit quantization
    r_a, g_a, b_a = quantize_image(img_a)
    r_b, g_b, b_b = quantize_image(img_b)

    # 2. Quantum lookup arithmetic
    qlut = get_quantum_lut()
    r_sum, r_carry = qlut.query_addition(r_a, r_b)
    g_sum, g_carry = qlut.query_addition(g_a, g_b)
    b_sum, b_carry = qlut.query_addition(b_a, b_b)

    # 3. Classical 8-bit image reconstruction
    result_image = reconstruct_image(r_sum, g_sum, b_sum)

    metadata = {
        "r_sum": r_sum,
        "g_sum": g_sum,
        "b_sum": b_sum,
        "r_carry": r_carry,
        "g_carry": g_carry,
        "b_carry": b_carry,
        "r_a_quant": r_a,
        "g_a_quant": g_a,
        "b_a_quant": b_a,
        "r_b_quant": r_b,
        "g_b_quant": g_b,
        "b_b_quant": b_b
    }

    return result_image, metadata

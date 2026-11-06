"""
Image Quality Assessment Metrics Module
=======================================

Implements standard full-reference image quality metrics:
  1. Mean Squared Error (MSE)
  2. Peak Signal-to-Noise Ratio (PSNR)
  3. Structural Similarity Index Measure (SSIM)

Evaluations performed:
  - Original 8-bit Image vs Quantized 8-bit Image (Quantization loss)
  - Quantized Input A vs Quantized Output / Processed
  - Quantized Input A vs Recovered Image ((A + B) - B) (Lossless quantum arithmetic)
"""

import sys
from pathlib import Path
from typing import Dict, Any, Union
from PIL import Image
import numpy as np
import pandas as pd
from skimage.metrics import structural_similarity as ssim_fn

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_IMAGE_METRICS


def calculate_mse(img1: Union[Image.Image, np.ndarray], img2: Union[Image.Image, np.ndarray]) -> float:
    """
    Calculate Mean Squared Error between two RGB images in [0, 255].
    """
    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)
    if arr1.shape != arr2.shape:
        raise ValueError(f"Shape mismatch: {arr1.shape} vs {arr2.shape}")
    mse = np.mean((arr1 - arr2) ** 2)
    return float(mse)


def calculate_psnr(img1: Union[Image.Image, np.ndarray], img2: Union[Image.Image, np.ndarray]) -> float:
    """
    Calculate Peak Signal-to-Noise Ratio (dB). Returns 100.0 dB if MSE == 0.
    """
    mse = calculate_mse(img1, img2)
    if mse == 0.0:
        return 100.0  # Perfect reconstruction indicator
    max_pixel = 255.0
    psnr = 10.0 * np.log10((max_pixel ** 2) / mse)
    return float(psnr)


def calculate_ssim(img1: Union[Image.Image, np.ndarray], img2: Union[Image.Image, np.ndarray]) -> float:
    """
    Calculate Structural Similarity Index (SSIM) across RGB channels.
    """
    arr1 = np.array(img1, dtype=np.uint8)
    arr2 = np.array(img2, dtype=np.uint8)
    if arr1.shape != arr2.shape:
        raise ValueError(f"Shape mismatch: {arr1.shape} vs {arr2.shape}")
    val = ssim_fn(arr1, arr2, channel_axis=2, data_range=255)
    return float(val)


def evaluate_image_pipeline(
    orig_a: Image.Image,
    orig_b: Image.Image,
    quant_a: Image.Image,
    quant_b: Image.Image,
    added_img: Image.Image,
    subbed_img: Image.Image,
    recovered_a: Image.Image
) -> pd.DataFrame:
    """
    Evaluate comprehensive metric table for image processing stages.
    """
    comparisons = [
        ("Original_A_vs_Quantized_A", orig_a, quant_a, "Quantization Loss (8-bit to 4-bit)"),
        ("Original_B_vs_Quantized_B", orig_b, quant_b, "Quantization Loss (8-bit to 4-bit)"),
        ("Quantized_A_vs_Quantum_Sum", quant_a, added_img, "Addition Transformation"),
        ("Quantized_A_vs_Quantum_Diff", quant_a, subbed_img, "Subtraction Transformation"),
        ("Quantized_A_vs_Recovered_A", quant_a, recovered_a, "Lossless Quantum Recovery ((A+B)-B)"),
    ]

    records = []
    for label, im1, im2, description in comparisons:
        mse = calculate_mse(im1, im2)
        psnr = calculate_psnr(im1, im2)
        ssim = calculate_ssim(im1, im2)
        records.append({
            "Comparison": label,
            "Description": description,
            "MSE": round(mse, 4),
            "PSNR_dB": round(psnr, 2),
            "SSIM": round(ssim, 4),
            "Is_Perfect_Reconstruction": (mse == 0.0)
        })

    df = pd.DataFrame(records)
    CSV_IMAGE_METRICS.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_IMAGE_METRICS, index=False)
    print(f"[Image Metrics] Pipeline metrics evaluated and saved to {CSV_IMAGE_METRICS}")
    return df

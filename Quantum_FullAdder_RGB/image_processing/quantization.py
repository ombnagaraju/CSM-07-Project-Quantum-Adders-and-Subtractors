"""
4-Bit Quantization and Reconstruction Module
===========================================

Mathematical Specifications:
----------------------------
Forward Quantization (8-bit to 4-bit):
    q = floor(pixel_value / 16)
    Maps [0, 255] -> [0, 15]

Inverse Reconstruction (4-bit to 8-bit):
    pixel_value = q * 17
    Maps [0, 15] -> [0, 255] (15 * 17 = 255)

Note on Information Loss:
-------------------------
Quantization from 8-bit depth (256 discrete levels) down to 4-bit depth
(16 discrete levels) is inherently lossy. Information loss is quantified
via Mean Squared Error (MSE) and Peak Signal-to-Noise Ratio (PSNR).
Subsequent quantum arithmetic on quantized channels, however, is strictly
bijective and reversible.
"""

from typing import Tuple
from PIL import Image
import numpy as np

from image_processing.rgb_converter import extract_rgb_channels, merge_rgb_channels


def quantize_channel(channel_8bit: np.ndarray) -> np.ndarray:
    """
    Quantize an 8-bit channel [0, 255] into 4-bit depth [0, 15].
    """
    return np.floor_divide(channel_8bit, 16).astype(np.uint8)


def reconstruct_channel(channel_4bit: np.ndarray) -> np.ndarray:
    """
    Reconstruct a 4-bit channel [0, 15] back into 8-bit dynamic range [0, 255].
    """
    # Clip to valid [0, 15] range and scale by 17
    clipped = np.clip(channel_4bit, 0, 15)
    return (clipped * 17).astype(np.uint8)


def quantize_image(image: Image.Image) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract and quantize R, G, B channels of an image into 4-bit NumPy arrays.
    """
    r_8, g_8, b_8 = extract_rgb_channels(image)
    r_4 = quantize_channel(r_8)
    g_4 = quantize_channel(g_8)
    b_4 = quantize_channel(b_8)
    return r_4, g_4, b_4


def reconstruct_image(r_4: np.ndarray, g_4: np.ndarray, b_4: np.ndarray) -> Image.Image:
    """
    Reconstruct an RGB PIL Image from three 4-bit channels.
    """
    r_8 = reconstruct_channel(r_4)
    g_8 = reconstruct_channel(g_4)
    b_8 = reconstruct_channel(b_4)
    return merge_rgb_channels(r_8, g_8, b_8)


def quantize_and_reconstruct(image: Image.Image) -> Image.Image:
    """
    Apply 4-bit quantization and immediately reconstruct to 8-bit for baseline visualization.
    """
    r_4, g_4, b_4 = quantize_image(image)
    return reconstruct_image(r_4, g_4, b_4)

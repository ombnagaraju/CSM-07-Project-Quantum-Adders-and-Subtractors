"""
RGB Channel Conversion and Extraction Module
=============================================

Handles channel decomposition and reassembly between PIL Images and
channel-wise NumPy ndarrays.
"""

from typing import Tuple
from PIL import Image
import numpy as np


def extract_rgb_channels(image: Image.Image) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Decompose an RGB PIL image into three separate 2D uint8 NumPy arrays (R, G, B).
    """
    arr = np.array(image, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"Expected 3-channel RGB image, got shape {arr.shape}")
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    return r, g, b


def merge_rgb_channels(r: np.ndarray, g: np.ndarray, b: np.ndarray) -> Image.Image:
    """
    Combine three 2D uint8 NumPy arrays (R, G, B) into a unified PIL RGB Image.
    """
    if r.shape != g.shape or r.shape != b.shape:
        raise ValueError("All three color channels must possess identical dimensions.")

    stacked = np.stack([r, g, b], axis=-1).astype(np.uint8)
    return Image.fromarray(stacked, mode="RGB")

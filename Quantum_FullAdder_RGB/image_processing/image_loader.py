"""
Image Loader and Preprocessing Module
=====================================

Loads, validates, and standardizes input images in JPG, JPEG, and PNG formats.
Includes utilities for generating synthetic sample images for testing.
"""

from pathlib import Path
from typing import Union, Tuple
from PIL import Image, ImageDraw
import numpy as np


def load_image(image_source: Union[str, Path, bytes, Image.Image]) -> Image.Image:
    """
    Load an image from path, buffer, or PIL object and ensure RGB format.
    """
    if isinstance(image_source, Image.Image):
        img = image_source
    elif isinstance(image_source, (str, Path)):
        p = Path(image_source)
        if not p.exists():
            raise FileNotFoundError(f"Image not found at path: {p}")
        img = Image.open(p)
    elif isinstance(image_source, bytes):
        import io
        img = Image.open(io.BytesIO(image_source))
    else:
        # Buffer-like object (e.g. Streamlit UploadedFile)
        if hasattr(image_source, "seek"):
            image_source.seek(0)
        img = Image.open(image_source)

    # Convert RGBA, Grayscale, or CMYK to standard 24-bit 3-channel RGB
    return img.convert("RGB")


def resize_image(image: Image.Image, target_size: Tuple[int, int] = (64, 64)) -> Image.Image:
    """
    Resize image to a specified common resolution using Lanczos interpolation.
    """
    return image.resize(target_size, Image.Resampling.LANCZOS)


def load_and_preprocess_pair(
    source_a: Union[str, Path, bytes, Image.Image],
    source_b: Union[str, Path, bytes, Image.Image],
    target_size: Tuple[int, int] = (64, 64)
) -> Tuple[Image.Image, Image.Image]:
    """
    Load two images and resize both to a common target resolution.
    """
    img_a = resize_image(load_image(source_a), target_size)
    img_b = resize_image(load_image(source_b), target_size)
    return img_a, img_b


def generate_sample_images(output_dir: Path, size: Tuple[int, int] = (64, 64)) -> Tuple[Path, Path]:
    """
    Generate two high-contrast synthetic RGB images and save them as sample_images.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path_a = output_dir / "image_a.png"
    path_b = output_dir / "image_b.png"

    w, h = size

    # Image A: Red and Blue geometric composition with radial gradient
    img_a = Image.new("RGB", (w, h), color=(30, 40, 80))
    draw_a = ImageDraw.Draw(img_a)
    # Circle in center (Golden / Red)
    draw_a.ellipse([w // 4, h // 4, 3 * w // 4, 3 * h // 4], fill=(220, 80, 50), outline=(255, 200, 100))
    # Horizontal bar
    draw_a.rectangle([0, h // 2 - 4, w, h // 2 + 4], fill=(60, 180, 220))
    img_a.save(path_a)

    # Image B: Green and Cyan diagonal stripes with diamond
    img_b = Image.new("RGB", (w, h), color=(20, 70, 40))
    draw_b = ImageDraw.Draw(img_b)
    # Diamond in center
    draw_b.polygon([(w // 2, 4), (w - 4, h // 2), (w // 2, h - 4), (4, h // 2)], fill=(80, 210, 130), outline=(220, 255, 180))
    # Vertical bar
    draw_b.rectangle([w // 2 - 4, 0, w // 2 + 4, h], fill=(200, 90, 180))
    img_b.save(path_b)

    return path_a, path_b

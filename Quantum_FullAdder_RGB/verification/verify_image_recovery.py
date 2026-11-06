"""
Image Recovery Verification Module
==================================

Verifies that quantum arithmetic image recovery ((A + B) - B) mod 16
recovers the quantized input image with 100% pixel fidelity.

Generates:
  results/csv/image_recovery_verification.csv
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import CSV_IMAGE_RECOVERY, SAMPLE_IMAGES_DIR, DEFAULT_IMAGE_SIZE
from image_processing.image_loader import generate_sample_images, load_and_preprocess_pair
from image_processing.quantization import quantize_and_reconstruct
from image_processing.image_recovery import run_full_recovery_cycle
from image_processing.image_metrics import calculate_mse, calculate_psnr, calculate_ssim


def verify_image_recovery_pipeline() -> pd.DataFrame:
    """
    Execute and record image recovery verification on sample images.
    """
    path_a = SAMPLE_IMAGES_DIR / "image_a.png"
    path_b = SAMPLE_IMAGES_DIR / "image_b.png"

    if not path_a.exists() or not path_b.exists():
        generate_sample_images(SAMPLE_IMAGES_DIR, size=DEFAULT_IMAGE_SIZE)

    img_a, img_b = load_and_preprocess_pair(path_a, path_b, target_size=DEFAULT_IMAGE_SIZE)
    quant_a = quantize_and_reconstruct(img_a)

    recovery_res = run_full_recovery_cycle(img_a, img_b)
    recovered_img = recovery_res["recovered_image"]

    # Calculate metrics between Quantized Input A and Recovered Image
    mse = calculate_mse(quant_a, recovered_img)
    psnr = calculate_psnr(quant_a, recovered_img)
    ssim = calculate_ssim(quant_a, recovered_img)

    status = "PASS" if recovery_res["exact_match"] and mse == 0.0 else "FAIL"

    record = [{
        "Image_Pair": "image_a.png & image_b.png",
        "Resolution": f"{DEFAULT_IMAGE_SIZE[0]}x{DEFAULT_IMAGE_SIZE[1]}",
        "Total_Pixels": recovery_res["total_pixels_evaluated"],
        "Red_Channel_Match": recovery_res["r_match"],
        "Green_Channel_Match": recovery_res["g_match"],
        "Blue_Channel_Match": recovery_res["b_match"],
        "Fidelity_Percentage": recovery_res["fidelity_pct"],
        "Recovery_MSE": mse,
        "Recovery_PSNR_dB": psnr,
        "Recovery_SSIM": ssim,
        "Exact_Reversible_Recovery": recovery_res["exact_match"],
        "Status": status
    }]

    df = pd.DataFrame(record)
    CSV_IMAGE_RECOVERY.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_IMAGE_RECOVERY, index=False)

    print(f"[Verification] Image Recovery: Fidelity={recovery_res['fidelity_pct']}%, MSE={mse}, Status={status}")
    print(f"[Output Saved] {CSV_IMAGE_RECOVERY}")

    if status != "PASS":
        raise ValueError("Image recovery verification failed!")

    return df


if __name__ == "__main__":
    verify_image_recovery_pipeline()

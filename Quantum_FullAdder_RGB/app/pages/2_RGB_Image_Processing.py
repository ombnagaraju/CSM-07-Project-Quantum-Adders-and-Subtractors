"""
Page 3: Quantum RGB Image Processing
====================================
Upload, quantize, process, and recover RGB images via simulated quantum arithmetic.
"""

import sys
from pathlib import Path
import io

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import numpy as np
from PIL import Image

from config import SAMPLE_IMAGES_DIR, DEFAULT_IMAGE_SIZE
from image_processing.image_loader import load_image, resize_image, generate_sample_images
from image_processing.quantization import quantize_and_reconstruct, quantize_image
from image_processing.image_addition import perform_image_addition
from image_processing.image_subtraction import perform_image_subtraction
from image_processing.image_recovery import run_full_recovery_cycle
from image_processing.image_metrics import calculate_mse, calculate_psnr, calculate_ssim

st.set_page_config(page_title="RGB Image Processing - Quantum Adder", page_icon="🖼️", layout="wide")

st.title("🖼️ Reversible Quantum RGB Image Processing")
st.markdown("Channel-wise arithmetic operations performed via verified Qiskit 4-bit quantum adder circuits.")

# Ensure sample images exist
path_a = SAMPLE_IMAGES_DIR / "image_a.png"
path_b = SAMPLE_IMAGES_DIR / "image_b.png"
if not path_a.exists() or not path_b.exists():
    generate_sample_images(SAMPLE_IMAGES_DIR, size=DEFAULT_IMAGE_SIZE)

# Sidebar controls
st.sidebar.header("⚙️ Processing Settings")
resolution_choice = st.sidebar.selectbox("Working Resolution:", ["64x64 (Recommended)", "32x32 (Fast)", "128x128 (Detailed)"], index=0)
res_map = {"32x32 (Fast)": (32, 32), "64x64 (Recommended)": (64, 64), "128x128 (Detailed)": (128, 128)}
target_res = res_map[resolution_choice]

operation = st.sidebar.radio(
    "Arithmetic Operation:",
    [
        "Addition: (A + B) mod 16",
        "Subtraction: (A - B) mod 16",
        "Lossless Recovery: ((A + B) - B) mod 16"
    ]
)

# Upload section
st.subheader("1. Source Images Selection")
col_up1, col_up2 = st.columns(2)

with col_up1:
    file_a = st.file_uploader("Upload Image A (JPG, PNG)", type=["png", "jpg", "jpeg"], key="up_a")
    if file_a is not None:
        try:
            img_a = resize_image(load_image(file_a), target_res)
        except Exception as e:
            st.error(f"Error loading Image A: {e}")
            img_a = resize_image(load_image(path_a), target_res)
    else:
        st.info("Using default Image A (Sample Pattern)")
        img_a = resize_image(load_image(path_a), target_res)
    st.image(img_a, caption=f"Image A ({target_res[0]}x{target_res[1]})", width="stretch")

with col_up2:
    file_b = st.file_uploader("Upload Image B (JPG, PNG)", type=["png", "jpg", "jpeg"], key="up_b")
    if file_b is not None:
        try:
            img_b = resize_image(load_image(file_b), target_res)
        except Exception as e:
            st.error(f"Error loading Image B: {e}")
            img_b = resize_image(load_image(path_b), target_res)
    else:
        st.info("Using default Image B (Sample Pattern)")
        img_b = resize_image(load_image(path_b), target_res)
    st.image(img_b, caption=f"Image B ({target_res[0]}x{target_res[1]})", width="stretch")

st.markdown("---")

# Quantization Info Expander
with st.expander("ℹ️ Understanding 4-Bit Reversible Quantization"):
    st.markdown("""
    **Quantization Process:**
    - Standard digital RGB channels store 8-bit depth (values $0$ to $255$).
    - Each color channel is quantized down to 4-bit depth ($0$ to $15$) using:
      $$q = \\lfloor \\text{pixel\\_value} / 16 \\rfloor$$
    - The quantized pixels are processed through the verified quantum adder circuit lookup table.
    - Output reconstruction scales the 4-bit representation back to the standard display range:
      $$\\text{reconstructed\\_value} = q \\times 17 \\quad (15 \\times 17 = 255)$$
    - *Note:* Quantization from 8-bit to 4-bit introduces irreversible quantization noise (approx. $30$-$35$ dB PSNR),
      but subsequent quantum arithmetic and channel recovery operations on quantized values are strictly **100% reversible and lossless**.
    """)

# Execution Button
if st.button("🚀 Run Quantum Image Processing Pipeline", type="primary"):
    with st.spinner("Processing color channels via simulated quantum arithmetic..."):
        quant_a = quantize_and_reconstruct(img_a)
        quant_b = quantize_and_reconstruct(img_b)

        if "Addition" in operation:
            result_img, meta = perform_image_addition(img_a, img_b)
            op_label = "Quantum Addition Result: (A + B) mod 16"
        elif "Subtraction" in operation:
            result_img, meta = perform_image_subtraction(img_a, img_b)
            op_label = "Quantum Subtraction Result: (A - B) mod 16"
        else:
            rec_res = run_full_recovery_cycle(img_a, img_b)
            result_img = rec_res["recovered_image"]
            op_label = "Quantum Lossless Recovered Image: ((A + B) - B) mod 16"

        # Save to session_state so it persists across reruns (such as clicking download)
        st.session_state["processed_data"] = {
            "quant_a": quant_a,
            "quant_b": quant_b,
            "result_img": result_img,
            "op_label": op_label,
            "operation": operation
        }

# Render persistent results if available
if "processed_data" in st.session_state:
    data = st.session_state["processed_data"]
    quant_a = data["quant_a"]
    quant_b = data["quant_b"]
    result_img = data["result_img"]
    op_label = data["op_label"]
    cur_op = data["operation"]

    st.subheader("2. Processing Results")
    res_col1, res_col2, res_col3 = st.columns(3)
    with res_col1:
        st.image(quant_a, caption="Quantized Input A (4-bit depth)", width="stretch")
    with res_col2:
        st.image(quant_b, caption="Quantized Input B (4-bit depth)", width="stretch")
    with res_col3:
        st.image(result_img, caption=op_label, width="stretch")

    # Download button
    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    byte_im = buf.getvalue()
    st.download_button(
        label="💾 Download Processed Image (PNG)",
        data=byte_im,
        file_name="quantum_processed_rgb.png",
        mime="image/png"
    )

    st.markdown("---")
    st.subheader("3. Image Quality & Fidelity Metrics")

    m_col1, m_col2, m_col3 = st.columns(3)
    if "Recovery" in cur_op:
        rec_mse = calculate_mse(quant_a, result_img)
        rec_psnr = calculate_psnr(quant_a, result_img)
        rec_ssim = calculate_ssim(quant_a, result_img)
        with m_col1:
            st.metric("Recovery MSE", f"{rec_mse:.4f}", delta="0.0 = Lossless")
        with m_col2:
            st.metric("Recovery PSNR", f"{rec_psnr:.2f} dB", delta="100 dB = Exact")
        with m_col3:
            st.metric("Recovery SSIM", f"{rec_ssim:.4f}", delta="1.000 = Identical")

        if rec_mse == 0.0:
            st.success("✅ **Mathematical Reversibility Confirmed**: Quantized Image A was reconstructed with 100.0% pixel-wise accuracy!")
    else:
        trans_mse = calculate_mse(quant_a, result_img)
        trans_psnr = calculate_psnr(quant_a, result_img)
        trans_ssim = calculate_ssim(quant_a, result_img)
        with m_col1:
            st.metric("Transformation MSE", f"{trans_mse:.2f}")
        with m_col2:
            st.metric("Transformation PSNR", f"{trans_psnr:.2f} dB")
        with m_col3:
            st.metric("Transformation SSIM", f"{trans_ssim:.4f}")

    # Channel Breakdown
    st.markdown("---")
    st.subheader("4. Individual RGB Channel Visual Breakdown")
    r_col, g_col, b_col = st.columns(3)
    arr_res = np.array(result_img)

    with r_col:
        st.image(arr_res[:, :, 0], caption="Red Channel", clamp=True, width="stretch")
    with g_col:
        st.image(arr_res[:, :, 1], caption="Green Channel", clamp=True, width="stretch")
    with b_col:
        st.image(arr_res[:, :, 2], caption="Blue Channel", clamp=True, width="stretch")

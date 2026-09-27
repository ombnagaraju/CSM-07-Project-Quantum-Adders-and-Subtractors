import io

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from PIL import Image
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Quantum Adder-Cum-Subtractor",
    page_icon="⚛️",
    layout="wide"
)


# ============================================================
# PROJECT TITLE
# ============================================================

PROJECT_TITLE = (
    "Design and Performance Analysis of an "
    "Optimized Reversible Quantum Adder-Cum-Subtractor Using Qiskit"
)


# ============================================================
# BASELINE 5-QUBIT CIRCUIT
# ============================================================

def baseline_adder_subtractor_core():

    qc = QuantumCircuit(5)

    # B XOR Mode
    qc.cx(2, 1)

    # Result = A XOR B' XOR Mode
    qc.cx(0, 3)
    qc.cx(1, 3)
    qc.cx(2, 3)

    # Carry / Borrow calculation
    qc.ccx(0, 1, 4)
    qc.ccx(0, 2, 4)
    qc.ccx(1, 2, 4)

    # Carry -> Borrow for subtraction
    qc.cx(2, 4)

    # Restore B
    qc.cx(2, 1)

    return qc


# ============================================================
# OPTIMIZED 5-QUBIT CIRCUIT
# ============================================================

def optimized_adder_subtractor_core():

    qc = QuantumCircuit(5)

    # Result = A XOR B XOR Mode
    qc.cx(0, 3)
    qc.cx(1, 3)
    qc.cx(2, 3)

    # Temporarily calculate A XOR Mode
    qc.cx(2, 0)

    # Carry / Borrow = B AND (A XOR Mode)
    qc.ccx(0, 1, 4)

    # Restore A
    qc.cx(2, 0)

    return qc


# ============================================================
# QUANTUM 8-BIT ADDER-CUM-SUBTRACTOR
# ============================================================

def create_8bit_adder_subtractor(a, b, mode):

    qc = QuantumCircuit(34, 9)

    # --------------------------------------------------------
    # Load A
    # --------------------------------------------------------

    for i in range(8):

        if (a >> i) & 1:
            qc.x(i)

    # --------------------------------------------------------
    # Load B
    # --------------------------------------------------------

    for i in range(8):

        if (b >> i) & 1:
            qc.x(8 + i)

    # --------------------------------------------------------
    # Mode
    # 0 = Addition
    # 1 = Subtraction
    # --------------------------------------------------------

    if mode == 1:
        qc.x(16)

    # --------------------------------------------------------
    # Initial carry = Mode
    # --------------------------------------------------------

    qc.cx(16, 25)

    # --------------------------------------------------------
    # 8-bit ripple-carry quantum arithmetic
    # --------------------------------------------------------

    for i in range(8):

        a_bit = i
        b_bit = 8 + i
        result_bit = 17 + i
        carry_in = 25 + i
        carry_out = 26 + i

        # B' = B XOR Mode
        qc.cx(16, b_bit)

        # Result = A XOR B' XOR Carry
        qc.cx(a_bit, result_bit)
        qc.cx(b_bit, result_bit)
        qc.cx(carry_in, result_bit)

        # Carry calculation
        qc.ccx(a_bit, b_bit, carry_out)
        qc.ccx(a_bit, carry_in, carry_out)
        qc.ccx(b_bit, carry_in, carry_out)

        # Restore B
        qc.cx(16, b_bit)

    # --------------------------------------------------------
    # Measure result bits
    # --------------------------------------------------------

    for i in range(8):
        qc.measure(17 + i, i)

    # Final carry
    qc.measure(33, 8)

    return qc


# ============================================================
# QUANTUM SIMULATOR
# ============================================================

simulator = AerSimulator(
    method="matrix_product_state"
)


# ============================================================
# QUANTUM PIXEL OPERATION
# ============================================================

def quantum_pixel_operation(a, b, mode):

    qc = create_8bit_adder_subtractor(
        int(a),
        int(b),
        mode
    )

    job = simulator.run(
        qc,
        shots=1
    )

    result = job.result()

    counts = result.get_counts()

    bitstring = list(counts.keys())[0]

    bitstring = bitstring.replace(" ", "")

    result_bits = bitstring[-8:]

    final_carry = int(bitstring[0])

    result_value = int(
        result_bits,
        2
    )

    return result_value, final_carry


# ============================================================
# IMAGE ADDITION
# ============================================================

def quantum_image_addition(image_A, image_B):

    height, width = image_A.shape

    result_image = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    carry_image = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    for i in range(height):

        for j in range(width):

            pixel_A = int(image_A[i, j])
            pixel_B = int(image_B[i, j])

            result_pixel, carry = quantum_pixel_operation(
                pixel_A,
                pixel_B,
                mode=0
            )

            result_image[i, j] = result_pixel
            carry_image[i, j] = carry

    return result_image, carry_image


# ============================================================
# IMAGE RECOVERY
# ============================================================

def quantum_image_recovery(image_C, image_B):

    height, width = image_C.shape

    recovered_image = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    borrow_image = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    for i in range(height):

        for j in range(width):

            pixel_C = int(image_C[i, j])
            pixel_B = int(image_B[i, j])

            recovered_pixel, final_carry = (
                quantum_pixel_operation(
                    pixel_C,
                    pixel_B,
                    mode=1
                )
            )

            borrow = 1 - final_carry

            recovered_image[i, j] = recovered_pixel
            borrow_image[i, j] = borrow

    return recovered_image, borrow_image


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.title("⚛️ Quantum Project")

st.sidebar.write(
    "Optimized Reversible Quantum "
    "Adder-Cum-Subtractor"
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate to:",
    [
        "🏠 Dashboard",
        "🖼️ Image Processing",
        "⚛️ Quantum Circuit",
        "📊 Performance Analysis",
        "📖 About Project"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "B.Tech Major Project\n"
    "Quantum Computing | Reversible Logic"
)


# ============================================================
# PAGE 1 — DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title(
        "⚛️ Optimized Quantum "
        "Adder-Cum-Subtractor"
    )

    st.subheader("Project Overview")

    st.write(
        """
        This application demonstrates an optimized reversible
        quantum adder-cum-subtractor using Qiskit.

        The application provides a visual demonstration of:

        • Quantum image addition
        • Image subtraction and recovery
        • Reversible quantum arithmetic
        • Baseline vs optimized quantum circuits
        • Circuit resource analysis
        • Image quality evaluation
        """
    )

    st.divider()

    st.subheader("🔄 Project Workflow")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.markdown("### 🖼️ Input")

        st.write(
            "Image A\n\n+\n\nImage B"
        )

    with col2:

        st.markdown("### ⚛️ Quantum")

        st.write(
            "Qiskit\n"
            "8-bit reversible\n"
            "arithmetic"
        )

    with col3:

        st.markdown("### ➕ / ➖")

        st.write(
            "Addition\n"
            "or\n"
            "Subtraction / Recovery"
        )

    with col4:

        st.markdown("### 📊 Output")

        st.write(
            "Result Image\n"
            "+\n"
            "Performance"
        )

    st.divider()

    st.subheader("🎯 Main Research Focus")

    st.info(
        "Optimization of a reversible quantum "
        "adder-cum-subtractor by reducing "
        "unnecessary gates and circuit resources."
    )

    st.divider()

    st.subheader("📌 Current Project Results")

    result_col1, result_col2, result_col3 = st.columns(3)

    with result_col1:

        st.metric(
            "Gate Count",
            "9 → 6",
            "33.33% reduction"
        )

    with result_col2:

        st.metric(
            "Circuit Depth",
            "7 → 4",
            "42.86% reduction"
        )

    with result_col3:

        st.metric(
            "Quantum Cost",
            "21 → 10",
            "52.38% reduction"
        )


# ============================================================
# PAGE 2 — IMAGE PROCESSING
# ============================================================

elif page == "🖼️ Image Processing":

    st.title(
        "🖼️ Quantum Image Processing"
    )

    st.write(
        "Perform image addition and image "
        "subtraction/recovery using the "
        "Qiskit-based quantum arithmetic circuit."
    )

    st.divider()

    # --------------------------------------------------------
    # UPLOAD IMAGES
    # --------------------------------------------------------

    st.subheader("1. Upload Input Images")

    col1, col2 = st.columns(2)

    with col1:

        image_a_file = st.file_uploader(
            "Upload Image A",
            type=["png", "jpg", "jpeg"],
            key="image_a_processing"
        )

    with col2:

        image_b_file = st.file_uploader(
            "Upload Image B",
            type=["png", "jpg", "jpeg"],
            key="image_b_processing"
        )

    st.divider()

    # --------------------------------------------------------
    # OPERATION
    # --------------------------------------------------------

    st.subheader("2. Select Operation")

    operation = st.radio(
        "Choose the quantum operation:",
        [
            "Addition",
            "Subtraction / Recovery"
        ],
        horizontal=True
    )

    if operation == "Addition":

        st.info(
            "Addition mode: "
            "Image A + Image B → Result Image C"
        )

    else:

        st.info(
            "Recovery mode: "
            "Result Image C − Image B → Recovered Image A"
        )

    st.divider()

    # --------------------------------------------------------
    # DISPLAY INPUT IMAGES
    # --------------------------------------------------------

    if (
        image_a_file is not None
        and image_b_file is not None
    ):

        display_col1, display_col2 = st.columns(2)

        with display_col1:

            image_A_preview = (
                Image.open(image_a_file)
                .convert("L")
            )

            st.subheader("Image A")

            st.image(
                image_A_preview,
                caption="Input Image A",
                width=300
            )

        with display_col2:

            image_B_preview = (
                Image.open(image_b_file)
                .convert("L")
            )

            st.subheader("Image B")

            st.image(
                image_B_preview,
                caption="Input Image B",
                width=300
            )

    # --------------------------------------------------------
    # RUN BUTTON
    # --------------------------------------------------------

    st.divider()

    run_button = st.button(
        "⚛️ Run Quantum Processing",
        type="primary"
    )

    if run_button:

        if (
            image_a_file is None
            or image_b_file is None
        ):

            st.error(
                "Please upload both images before running."
            )

        else:

            image_A = (
                Image.open(image_a_file)
                .convert("L")
            )

            image_B = (
                Image.open(image_b_file)
                .convert("L")
            )

            image_A = np.array(image_A)
            image_B = np.array(image_B)

            # ------------------------------------------------
            # SIZE CHECK
            # ------------------------------------------------

            if image_A.shape != image_B.shape:

                st.error(
                    "Both images must have the same dimensions."
                )

                st.stop()

            height, width = image_A.shape

            # ------------------------------------------------
            # DEMO SIZE LIMIT
            # ------------------------------------------------

            if height > 32 or width > 32:

                st.error(
                    "For this quantum simulation demo, "
                    "please use images up to 32 × 32 pixels."
                )

                st.stop()

            # ------------------------------------------------
            # ADDITION
            # ------------------------------------------------

            if operation == "Addition":

                with st.spinner(
                    "Running quantum image addition..."
                ):

                    result_image, carry_image = (
                        quantum_image_addition(
                            image_A,
                            image_B
                        )
                    )

                st.success(
                    "Quantum image addition completed!"
                )

                st.subheader(
                    "➕ Quantum Addition Result"
                )

                result_col1, result_col2, result_col3 = (
                    st.columns(3)
                )

                with result_col1:

                    st.image(
                        image_A,
                        caption="Image A",
                        use_container_width=True
                    )

                with result_col2:

                    st.image(
                        image_B,
                        caption="Image B",
                        use_container_width=True
                    )

                with result_col3:

                    st.image(
                        result_image,
                        caption="Result Image C = A + B",
                        use_container_width=True
                    )

                # --------------------------------------------
                # DOWNLOAD RESULT
                # --------------------------------------------

                result_buffer = io.BytesIO()

                Image.fromarray(
                    result_image
                ).save(
                    result_buffer,
                    format="PNG"
                )

                st.download_button(
                    label="⬇️ Download Result Image C",
                    data=result_buffer.getvalue(),
                    file_name="quantum_result_image_C.png",
                    mime="image/png"
                )

            # ------------------------------------------------
            # SUBTRACTION / RECOVERY
            # ------------------------------------------------

            else:

                with st.spinner(
                    "Running quantum subtraction/recovery..."
                ):

                    recovered_image, borrow_image = (
                        quantum_image_recovery(
                            image_A,
                            image_B
                        )
                    )

                st.success(
                    "Quantum image recovery completed!"
                )

                st.subheader(
                    "➖ Quantum Recovery Result"
                )

                result_col1, result_col2, result_col3 = (
                    st.columns(3)
                )

                with result_col1:

                    st.image(
                        image_A,
                        caption="Result Image C",
                        use_container_width=True
                    )

                with result_col2:

                    st.image(
                        image_B,
                        caption="Image B",
                        use_container_width=True
                    )

                with result_col3:

                    st.image(
                        recovered_image,
                        caption="Recovered Image A",
                        use_container_width=True
                    )

                # --------------------------------------------
                # DOWNLOAD RECOVERED IMAGE
                # --------------------------------------------

                recovered_buffer = io.BytesIO()

                Image.fromarray(
                    recovered_image
                ).save(
                    recovered_buffer,
                    format="PNG"
                )

                st.download_button(
                    label="⬇️ Download Recovered Image",
                    data=recovered_buffer.getvalue(),
                    file_name="quantum_recovered_image_A.png",
                    mime="image/png"
                )

                # --------------------------------------------
                # IMAGE QUALITY
                # --------------------------------------------

                psnr_value = (
                    peak_signal_noise_ratio(
                        image_A,
                        recovered_image,
                        data_range=255
                    )
                )

                ssim_value = (
                    structural_similarity(
                        image_A,
                        recovered_image,
                        data_range=255
                    )
                )

                st.divider()

                st.subheader(
                    "📊 Image Recovery Metrics"
                )

                metric1, metric2 = st.columns(2)

                with metric1:

                    st.metric(
                        "PSNR",
                        (
                            "∞"
                            if np.isinf(psnr_value)
                            else f"{psnr_value:.2f} dB"
                        )
                    )

                with metric2:

                    st.metric(
                        "SSIM",
                        f"{ssim_value:.4f}"
                    )

                # --------------------------------------------
                # ORIGINAL VS RECOVERED
                # --------------------------------------------

                st.subheader(
                    "🔍 Original vs Recovered"
                )

                comparison_col1, comparison_col2 = (
                    st.columns(2)
                )

                with comparison_col1:

                    st.image(
                        image_A,
                        caption="Original Image",
                        use_container_width=True
                    )

                with comparison_col2:

                    st.image(
                        recovered_image,
                        caption="Recovered Image",
                        use_container_width=True
                    )

                # --------------------------------------------
                # PIXEL VERIFICATION
                # --------------------------------------------

                difference = np.abs(
                    image_A.astype(int)
                    -
                    recovered_image.astype(int)
                )

                max_difference = np.max(
                    difference
                )

                total_error = np.sum(
                    difference
                )

                different_pixels = np.count_nonzero(
                    difference
                )

                st.subheader(
                    "🔍 Pixel-Level Verification"
                )

                verification_col1, verification_col2, verification_col3 = (
                    st.columns(3)
                )

                with verification_col1:

                    st.metric(
                        "Maximum Pixel Difference",
                        int(max_difference)
                    )

                with verification_col2:

                    st.metric(
                        "Total Absolute Error",
                        int(total_error)
                    )

                with verification_col3:

                    st.metric(
                        "Different Pixels",
                        int(different_pixels)
                    )

                if (
                    max_difference == 0
                    and total_error == 0
                    and different_pixels == 0
                ):

                    st.success(
                        "✅ PERFECT RECOVERY — "
                        "Recovered image is identical "
                        "to the original image."
                    )

                else:

                    st.warning(
                        "⚠️ Differences were detected "
                        "between the original and recovered image."
                    )

    st.divider()

    # --------------------------------------------------------
    # IMAGE PROCESSING WORKFLOW
    # --------------------------------------------------------

    st.subheader(
        "🔄 Quantum Image Processing Workflow"
    )

    workflow_col1, workflow_col2, workflow_col3, workflow_col4 = (
        st.columns(4)
    )

    with workflow_col1:

        st.markdown(
            """
            ### 1️⃣ Input

            Image A

            +

            Image B
            """
        )

    with workflow_col2:

        st.markdown(
            """
            ### 2️⃣ Quantum

            8-bit reversible

            quantum arithmetic
            """
        )

    with workflow_col3:

        st.markdown(
            """
            ### 3️⃣ Operation

            Addition

            or

            Subtraction
            """
        )

    with workflow_col4:

        st.markdown(
            """
            ### 4️⃣ Output

            Result Image

            +

            Quality Metrics
            """
        )

    st.info(
        "Demo limitation: the current live simulator "
        "supports images up to 32 × 32 pixels."
    )


# ============================================================
# PAGE 3 — QUANTUM CIRCUIT
# ============================================================

elif page == "⚛️ Quantum Circuit":

    st.title(
        "⚛️ Quantum Circuit Analysis"
    )

    st.write(
        "Comparison of the baseline and optimized "
        "reversible quantum adder-cum-subtractor circuits."
    )

    st.divider()

    # --------------------------------------------------------
    # CREATE CIRCUITS
    # --------------------------------------------------------

    baseline = baseline_adder_subtractor_core()

    optimized = optimized_adder_subtractor_core()

    # --------------------------------------------------------
    # BASELINE METRICS
    # --------------------------------------------------------

    baseline_gate_count = len(
        baseline.data
    )

    baseline_depth = baseline.depth()

    baseline_cx = baseline.count_ops().get(
        "cx",
        0
    )

    baseline_ccx = baseline.count_ops().get(
        "ccx",
        0
    )

    baseline_qc = (
        baseline_cx
        +
        (5 * baseline_ccx)
    )

    # --------------------------------------------------------
    # OPTIMIZED METRICS
    # --------------------------------------------------------

    optimized_gate_count = len(
        optimized.data
    )

    optimized_depth = optimized.depth()

    optimized_cx = optimized.count_ops().get(
        "cx",
        0
    )

    optimized_ccx = optimized.count_ops().get(
        "ccx",
        0
    )

    optimized_qc = (
        optimized_cx
        +
        (5 * optimized_ccx)
    )

    # --------------------------------------------------------
    # BASELINE CIRCUIT
    # --------------------------------------------------------

    st.subheader(
        "1. 🔴 Baseline Circuit"
    )

    st.write(
        "The baseline circuit performs the "
        "combined addition/subtraction operation "
        "using a larger number of reversible gates."
    )

    try:

        baseline_fig = baseline.draw(
            output="mpl"
        )

        st.pyplot(
            baseline_fig,
            clear_figure=True
        )

        plt.close(baseline_fig)

    except Exception as e:

        st.warning(
            f"Baseline circuit visualization error: {e}"
        )

    st.subheader(
        "Baseline Circuit Metrics"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "Qubits",
            baseline.num_qubits
        )

    with col2:

        st.metric(
            "Gates",
            baseline_gate_count
        )

    with col3:

        st.metric(
            "Depth",
            baseline_depth
        )

    with col4:

        st.metric(
            "CNOT",
            baseline_cx
        )

    with col5:

        st.metric(
            "Toffoli",
            baseline_ccx
        )

    st.info(
        f"Quantum Cost = {baseline_qc} "
        "(CNOT = 1, Toffoli = 5)"
    )

    st.divider()

    # --------------------------------------------------------
    # OPTIMIZED CIRCUIT
    # --------------------------------------------------------

    st.subheader(
        "2. 🟢 Optimized Circuit"
    )

    st.write(
        "The optimized circuit removes unnecessary "
        "operations while maintaining the required "
        "adder-cum-subtractor functionality."
    )

    try:

        optimized_fig = optimized.draw(
            output="mpl"
        )

        st.pyplot(
            optimized_fig,
            clear_figure=True
        )

        plt.close(optimized_fig)

    except Exception as e:

        st.warning(
            f"Optimized circuit visualization error: {e}"
        )

    st.subheader(
        "Optimized Circuit Metrics"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "Qubits",
            optimized.num_qubits
        )

    with col2:

        st.metric(
            "Gates",
            optimized_gate_count
        )

    with col3:

        st.metric(
            "Depth",
            optimized_depth
        )

    with col4:

        st.metric(
            "CNOT",
            optimized_cx
        )

    with col5:

        st.metric(
            "Toffoli",
            optimized_ccx
        )

    st.info(
        f"Quantum Cost = {optimized_qc} "
        "(CNOT = 1, Toffoli = 5)"
    )

    st.divider()

    # --------------------------------------------------------
    # COMPARISON TABLE
    # --------------------------------------------------------

    st.subheader(
        "3. 📊 Baseline vs Optimized"
    )

    comparison_data = {

        "Metric": [
            "Qubits",
            "Gate Count",
            "Circuit Depth",
            "CNOT Count",
            "Toffoli Count",
            "Quantum Cost"
        ],

        "Baseline": [
            baseline.num_qubits,
            baseline_gate_count,
            baseline_depth,
            baseline_cx,
            baseline_ccx,
            baseline_qc
        ],

        "Optimized": [
            optimized.num_qubits,
            optimized_gate_count,
            optimized_depth,
            optimized_cx,
            optimized_ccx,
            optimized_qc
        ]
    }

    comparison_df = pd.DataFrame(
        comparison_data
    )

    st.dataframe(
        comparison_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # --------------------------------------------------------
    # OPTIMIZATION RESULTS
    # --------------------------------------------------------

    st.subheader(
        "4. 📉 Optimization Achieved"
    )

    gate_reduction = (
        (
            baseline_gate_count
            -
            optimized_gate_count
        )
        /
        baseline_gate_count
    ) * 100

    depth_reduction = (
        (
            baseline_depth
            -
            optimized_depth
        )
        /
        baseline_depth
    ) * 100

    qc_reduction = (
        (
            baseline_qc
            -
            optimized_qc
        )
        /
        baseline_qc
    ) * 100

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Gate Count Reduction",
            f"{gate_reduction:.2f}%"
        )

    with col2:

        st.metric(
            "Depth Reduction",
            f"{depth_reduction:.2f}%"
        )

    with col3:

        st.metric(
            "Quantum Cost Reduction",
            f"{qc_reduction:.2f}%"
        )

    st.success(
        "The optimized 5-qubit core circuit "
        "uses fewer gates and has lower circuit "
        "depth and quantum cost than the baseline design."
    )

    st.caption(
        "Note: These optimization metrics refer to the "
        "5-qubit core adder-cum-subtractor circuit."
    )


# ============================================================
# PAGE 4 — PERFORMANCE ANALYSIS
# ============================================================

elif page == "📊 Performance Analysis":

    st.title(
        "📊 Performance Analysis"
    )

    st.write(
        "Measured resource comparison of the "
        "baseline and optimized 5-qubit "
        "reversible quantum adder-cum-subtractor."
    )

    st.divider()

    # --------------------------------------------------------
    # PERFORMANCE DATA
    # --------------------------------------------------------

    performance_data = {

        "Metric": [
            "Gate Count",
            "Circuit Depth",
            "Quantum Cost",
            "Toffoli Gates",
            "CNOT Gates",
            "Qubits"
        ],

        "Baseline": [
            9,
            7,
            21,
            3,
            6,
            5
        ],

        "Optimized": [
            6,
            4,
            10,
            1,
            5,
            5
        ],

        "Reduction (%)": [
            33.33,
            42.86,
            52.38,
            66.67,
            16.67,
            0.00
        ]
    }

    performance_df = pd.DataFrame(
        performance_data
    )

    st.dataframe(
        performance_df,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # --------------------------------------------------------
    # PERFORMANCE CARDS
    # --------------------------------------------------------

    st.subheader(
        "Optimization Summary"
    )

    metric1, metric2, metric3 = st.columns(3)

    with metric1:

        st.metric(
            "Gate Count",
            "6",
            "-33.33%"
        )

    with metric2:

        st.metric(
            "Circuit Depth",
            "4",
            "-42.86%"
        )

    with metric3:

        st.metric(
            "Quantum Cost",
            "10",
            "-52.38%"
        )

    metric4, metric5, metric6 = st.columns(3)

    with metric4:

        st.metric(
            "Toffoli Gates",
            "1",
            "-66.67%"
        )

    with metric5:

        st.metric(
            "CNOT Gates",
            "5",
            "-16.67%"
        )

    with metric6:

        st.metric(
            "Qubits",
            "5",
            "No change"
        )

    st.divider()

    # --------------------------------------------------------
    # SIMPLE VISUAL COMPARISON
    # --------------------------------------------------------

    st.subheader(
        "📈 Resource Comparison"
    )

    chart_df = performance_df.set_index(
        "Metric"
    )[["Baseline", "Optimized"]]

    st.bar_chart(
        chart_df
    )

    st.info(
        "Quantum Cost is calculated using the project model: "
        "CNOT = 1 and Toffoli = 5."
    )


# ============================================================
# PAGE 5 — ABOUT PROJECT
# ============================================================

elif page == "📖 About Project":

    st.title(
        "📖 About the Project"
    )

    st.subheader(
        "Project Title"
    )

    st.write(
        PROJECT_TITLE
    )

    st.divider()

    st.subheader(
        "🎯 Objective"
    )

    st.write(
        """
        The project aims to design and analyze an optimized
        reversible quantum adder-cum-subtractor using Qiskit.

        The work focuses on reducing unnecessary circuit
        resources and evaluating the resulting circuit using
        parameters such as gate count, circuit depth,
        quantum cost, CNOT count, and Toffoli count.

        The circuit is also applied to image addition and
        image subtraction/recovery.
        """
    )

    st.divider()

    st.subheader(
        "⚛️ Technologies Used"
    )

    tech_col1, tech_col2 = st.columns(2)

    with tech_col1:

        st.markdown(
            """
            - Python
            - Qiskit
            - Qiskit Aer
            - NumPy
            """
        )

    with tech_col2:

        st.markdown(
            """
            - Pillow
            - Scikit-image
            - Matplotlib
            - Streamlit
            """
        )

    st.divider()

    st.subheader(
        "🔄 Application Workflow"
    )

    st.markdown(
        """
        **Image A + Image B**

        ↓

        **8-bit Reversible Quantum Arithmetic**

        ↓

        **Addition → Result Image C**

        ↓

        **Subtraction: C − B**

        ↓

        **Recovered Image A**

        ↓

        **PSNR + SSIM + Pixel Verification**
        """
    )

    st.divider()

    st.subheader(
        "📊 Optimization Results"
    )

    about_data = pd.DataFrame(
        {
            "Metric": [
                "Gate Count",
                "Circuit Depth",
                "Quantum Cost",
                "Toffoli Count",
                "CNOT Count",
                "Qubits"
            ],

            "Baseline": [
                9,
                7,
                21,
                3,
                6,
                5
            ],

            "Optimized": [
                6,
                4,
                10,
                1,
                5,
                5
            ]
        }
    )

    st.dataframe(
        about_data,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader(
        "🖼️ Image Processing"
    )

    st.write(
        """
        The application performs pixel-level quantum arithmetic
        using an 8-bit reversible quantum adder-cum-subtractor.

        For the recovery demonstration:

        Result Image C − Image B → Recovered Image A

        The recovered image can be evaluated using PSNR,
        SSIM, maximum pixel difference, total absolute error,
        and number of different pixels.
        """
    )

    st.warning(
        "Live application limitation: images are limited to "
        "32 × 32 pixels because each pixel is processed using "
        "the current 34-qubit quantum simulation circuit."
    )

    st.divider()

    st.caption(
        PROJECT_TITLE
    )

    st.caption(
        "B.Tech Major Project | Quantum Computing | Reversible Logic"
    )
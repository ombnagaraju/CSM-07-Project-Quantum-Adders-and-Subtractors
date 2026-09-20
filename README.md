# Project Overview

## Project Title

**Design and Performance Analysis of an Optimized Reversible Quantum Adder-Cum-Subtractor Using Qiskit**

## Overview

This project focuses on the design, implementation, optimization, and performance analysis of a **reversible quantum adder-cum-subtractor using Qiskit**.

The project is based on the study of existing research in reversible arithmetic, quantum full adders, reversible adders/subtractors, and image-processing applications.

The main objective is to develop a quantum arithmetic circuit that can perform both **addition and subtraction** while preserving reversibility and analyzing the resources required by the circuit.

The project also extends the quantum arithmetic circuit to a practical **image-processing application**.

Two input images, **Image A** and **Image B**, are provided to the system. The images are processed pixel by pixel. The pixel values are converted into binary representation and processed using the proposed quantum arithmetic circuit.

The addition operation is:

```text
A + B = C

## Main Workflow

```text
             User
              │
       ┌──────┴──────┐
       ↓             ↓
    Image A       Image B
       │             │
       └──────┬──────┘
              ↓
       Pixel Extraction
              ↓
       Decimal → Binary
              ↓
      Quantum Full Adder
              ↓
          A + B = C
              ↓
        Output Image C
              ↓
       Quantum Subtractor
              ↑
          Image B
              ↓
          C - B = A
              ↓
      Recovered Image A
              ↓
       Compare Results
```

## Key Features

* User can provide input images.
* Pixel-level image processing.
* Binary representation of pixel values.
* Quantum full-adder implementation.
* Quantum subtractor implementation.
* Addition of two images.
* Generation of an output image.
* Recovery of the original image using subtraction.
* Comparison between original and recovered images.
* Quantum circuit simulation using Qiskit.

---

# Technologies Used

| Technology           | Purpose                                     |
| -------------------- | ------------------------------------------- |
| **Python**           | Main programming language                   |
| **Qiskit**           | Creation and simulation of quantum circuits |
| **Quantum Gates**    | Implementation of reversible arithmetic     |
| **Pillow (PIL)**     | Reading and processing images               |
| **NumPy**            | Pixel-array and numerical operations        |
| **Jupyter Notebook** | Experimentation and testing                 |
| **Matplotlib**       | Displaying images and circuit results       |
| **Git & GitHub**     | Version control and project management      |

## Quantum Technologies

The project uses fundamental reversible/quantum gates such as:

* **X Gate**
* **CNOT Gate**
* **Toffoli / CCNOT Gate**
* **SWAP Gate**

These gates are used to construct the quantum arithmetic circuits.

---

# Project Structure

```text
Quantum-Image-Recovery/
│
├── README.md
│
├── requirements.txt
│
├── quantum_adder_subtractor.py
│
├── quantum_full_adder.py
│
├── quantum_subtractor.py
│
├── image_processing.py
│
├── image_addition.py
│
├── image_recovery.py
│
├── utils.py
│
├── images/
│   ├── input/
│   │   ├── image_A.png
│   │   └── image_B.png
│   │
│   └── output/
│       ├── image_C.png
│       └── recovered_A.png
│
├── notebooks/
│   ├── 01_quantum_gates.ipynb
│   ├── 02_full_adder.ipynb
│   ├── 03_adder_subtractor.ipynb
│   └── 04_image_recovery.ipynb
│
└── results/
    ├── circuits/
    └── comparison/
```

## Description of Important Files

### `quantum_adder_subtractor.py`

Contains the main quantum binary adder-subtractor implementation.

```text
Input:
A, B, Control

       ↓

Quantum Adder/Subtractor

       ↓

Output:
Sum / Difference
```

### `quantum_full_adder.py`

Contains the quantum full-adder circuit.

It handles:

```text
A + B + Carry-in
```

and produces:

```text
Sum + Carry-out
```

### `quantum_subtractor.py`

Contains the reversible subtraction operation.

```text
A - B
```

### `image_processing.py`

Handles the image-related operations:

```text
Image
  ↓
Read image
  ↓
Convert to grayscale
  ↓
Extract pixels
  ↓
Pixel matrix
```

### `image_addition.py`

Performs pixel-wise addition:

```text
Pixel A + Pixel B
        ↓
   Quantum Adder
        ↓
     Pixel C
```

The pixels are combined to generate **Output Image C**.

### `image_recovery.py`

Performs the recovery operation:

```text
Output Image C - Image B
              ↓
       Quantum Subtractor
              ↓
       Recovered Image A
```

### `utils.py`

Contains supporting functions such as:

* Decimal-to-binary conversion
* Binary-to-decimal conversion
* Pixel validation
* Image comparison
* Result calculations

### `images/input/`

Stores the images supplied by the user.

```text
image_A.png
image_B.png
```

### `images/output/`

Stores generated results.

```text
image_C.png
recovered_A.png
```

### `notebooks/`

Contains separate experiments for learning, testing, and demonstrating each stage of the project.

### `results/`

Stores quantum circuit diagrams, simulation results, and image-comparison results.

---

# Overall Project Architecture

```text
┌───────────────────────────────┐
│          USER INPUT           │
│       Image A + Image B       │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│       IMAGE PROCESSING        │
│   Read → Resize → Grayscale   │
│        → Extract Pixels       │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│     BINARY CONVERSION         │
│       Pixel → Binary          │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│      QUANTUM ARITHMETIC       │
│                               │
│  Quantum Full Adder           │
│  Quantum Subtractor           │
│  CNOT / CCNOT / SWAP          │
└───────────────┬───────────────┘
                ↓
          A + B = C
                ↓
┌───────────────────────────────┐
│        OUTPUT IMAGE C         │
└───────────────┬───────────────┘
                ↓
          C - B = A
                ↓
┌───────────────────────────────┐
│       RECOVERED IMAGE A       │
└───────────────┬───────────────┘
                ↓
┌───────────────────────────────┐
│          VERIFICATION         │
│ Original A ↔ Recovered A      │
└───────────────────────────────┘
```

## Project Contribution

The **quantum adder/subtractor** forms the foundation of the project based on the reference work. The proposed extension is to use the reversible arithmetic circuit for **pixel-level image processing and image recovery**, with user-provided images as inputs.

The project therefore demonstrates both:

1. **Quantum arithmetic implementation**, and
2. **A practical image-processing application of that arithmetic.**

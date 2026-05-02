#!/bin/bash
# YOLO Vision Pipeline - Ubuntu/WSL Setup Script
# This script sets up the environment for RKNN model conversion

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  YOLO Vision Pipeline RKNN - Ubuntu/WSL Setup                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "This script will set up the Python environment for:"
echo "  1. RKNN model conversion from ONNX"
echo "  2. INT8 quantization"
echo ""

# Choose a fast working directory on the WSL filesystem
WORKDIR="${RKNN_WORKDIR:-$HOME/rknn-workdir}"
if [[ "$PWD" == /mnt/* ]]; then
    echo "Detected Windows-mounted path: $PWD"
    echo "Using WSL workdir for faster IO: $WORKDIR"
    mkdir -p "$WORKDIR"
fi

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv

echo "✅ System packages installed"
echo ""

# Create virtual environment
ENV_NAME="rknn-env"
ENV_DIR="$WORKDIR/$ENV_NAME"
echo "Creating Python virtual environment: $ENV_DIR"

if [ -d "$ENV_DIR" ]; then
    echo "Environment already exists, skipping creation"
else
    python3 -m venv "$ENV_DIR"
fi

source "$ENV_DIR/bin/activate"

echo "✅ Virtual environment created and activated"
echo ""

# Prepare third-party directory
echo "Preparing to download RKNN Toolkit2..."
THIRD_PARTY_DIR="$WORKDIR/3rdparty"
mkdir -p "$THIRD_PARTY_DIR"
cd "$THIRD_PARTY_DIR"

if [ ! -d "rknn-toolkit2" ]; then
    echo "Cloning RKNN Toolkit2 (sparse checkout)..."
    git clone --depth 1 --filter=blob:none --sparse https://github.com/airockchip/rknn-toolkit2.git
    cd rknn-toolkit2
    git sparse-checkout set rknn-toolkit2/packages/x86_64
else
    echo "RKNN Toolkit2 already downloaded"
    cd rknn-toolkit2
    git sparse-checkout set rknn-toolkit2/packages/x86_64
fi

echo "✅ RKNN Toolkit2 ready"
echo ""

# Install RKNN dependencies
echo "Installing RKNN Toolkit2 dependencies..."
cd rknn-toolkit2/packages/x86_64

if [ -f "requirements_cp310-2.3.2.txt" ]; then
    pip install -r requirements_cp310-2.3.2.txt
else
    echo "WARNING: requirements_cp310-2.3.2.txt not found"
    echo "Please check RKNN Toolkit2 version"
fi

echo "Installing RKNN Toolkit2 wheel..."
pip install rknn_toolkit2-2.3.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl 2>/dev/null || \
pip install rknn_toolkit2*.whl

echo "✅ RKNN Toolkit2 installed"
echo ""

# Downgrade onnx for compatibility
echo "Installing compatible ONNX version..."
pip install onnx==1.14.1

echo "Installing PyYAML..."
pip install pyyaml

echo "✅ ONNX installed"
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "Next steps:"
echo "  1. Activate the environment (in the future):"
echo "     source $ENV_DIR/bin/activate"
echo ""
echo "  2. Prepare calibration dataset:"
echo "     python src/dataset_tools.py prepare_calibration ..."
echo ""
echo "  3. Copy your ONNX model to models/ directory"
echo ""
echo "  4. Convert to RKNN:"
echo "     python src/export/2_onnx_to_rknn.py"
echo ""

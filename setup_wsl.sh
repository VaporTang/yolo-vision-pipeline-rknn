#!/bin/bash
# YOLO Vision Pipeline - Ubuntu/WSL Setup Script
# This script sets up the environment for RKNN model conversion

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  YOLO Vision Pipeline RKNN - Ubuntu/WSL Setup               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "This script will set up the Python environment for:"
echo "  1. RKNN model conversion from ONNX"
echo "  2. INT8 quantization"
echo ""

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv

echo "✅ System packages installed"
echo ""

# Create virtual environment
ENV_NAME="rknn-env"
echo "Creating Python virtual environment: $ENV_NAME"

if [ -d "$ENV_NAME" ]; then
    echo "Environment already exists, skipping creation"
else
    python3 -m venv $ENV_NAME
fi

source $ENV_NAME/bin/activate

echo "✅ Virtual environment created and activated"
echo ""

# Prepare third-party directory
echo "Preparing to download RKNN Toolkit2..."
mkdir -p 3rdparty
cd 3rdparty

if [ ! -d "rknn-toolkit2" ]; then
    echo "Cloning RKNN Toolkit2..."
    git clone https://github.com/airockchip/rknn-toolkit2.git
else
    echo "RKNN Toolkit2 already downloaded"
fi

echo "✅ RKNN Toolkit2 ready"
echo ""

# Install RKNN dependencies
echo "Installing RKNN Toolkit2 dependencies..."
cd rknn-toolkit2/rknn-toolkit2/packages/x86_64

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

echo "✅ ONNX installed"
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "Next steps:"
echo "  1. Activate the environment (in the future):"
echo "     source $ENV_NAME/bin/activate"
echo ""
echo "  2. Prepare calibration dataset:"
echo "     python src/dataset_tools.py prepare_calibration ..."
echo ""
echo "  3. Copy your ONNX model to models/ directory"
echo ""
echo "  4. Convert to RKNN:"
echo "     python src/export/2_onnx_to_rknn.py"
echo ""

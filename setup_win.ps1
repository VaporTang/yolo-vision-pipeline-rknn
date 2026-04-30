# YOLO Vision Pipeline - Windows Setup Script
# This script sets up the Conda environment for YOLOv8 training and ONNX export

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  YOLO Vision Pipeline RKNN - Windows Setup                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host ""
Write-Host "This script will set up the Conda environment for:" -ForegroundColor Yellow
Write-Host "  1. YOLOv8 model training"
Write-Host "  2. ONNX format export"
Write-Host "  3. Dataset processing"
Write-Host ""

# Check if Conda is installed
Write-Host "Checking Conda installation..." -ForegroundColor Cyan
$condaPath = Get-Command conda -ErrorAction SilentlyContinue
if (-not $condaPath) {
    Write-Host "ERROR: Conda not found. Please install Miniconda or Anaconda first." -ForegroundColor Red
    Write-Host "Download from: https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Conda found" -ForegroundColor Green
Write-Host ""

# Create Conda environment
$envName = "rknn-yolov8"
Write-Host "Creating Conda environment: $envName" -ForegroundColor Cyan

conda create -n $envName python=3.10 -y

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create Conda environment" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Environment created" -ForegroundColor Green
Write-Host ""

# Activate environment
Write-Host "Activating environment..." -ForegroundColor Cyan
conda activate $envName

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to activate environment" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Environment activated" -ForegroundColor Green
Write-Host ""

# Install PyTorch
Write-Host "Installing PyTorch with CUDA support..." -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install PyTorch" -ForegroundColor Red
    exit 1
}

Write-Host "✅ PyTorch installed" -ForegroundColor Green
Write-Host ""

# Clone and install Rockchip YOLO
Write-Host "Setting up Rockchip-customized YOLOv8..." -ForegroundColor Cyan

if (-not (Test-Path "3rdparty/ultralytics_yolov8" -PathType Container)) {
    Write-Host "  Cloning ultralytics_yolov8..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path "3rdparty" | Out-Null
    Set-Location "3rdparty"
    git clone https://github.com/airockchip/ultralytics_yolov8.git
    Set-Location ..
}
else {
    Write-Host "  ultralytics_yolov8 already exists" -ForegroundColor Yellow
}

Set-Location "3rdparty/ultralytics_yolov8"
Write-Host "  Installing as development package..." -ForegroundColor Cyan
pip install -e .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install ultralytics" -ForegroundColor Red
    exit 1
}

cd ../..
Write-Host "✅ Rockchip YOLOv8 installed" -ForegroundColor Green
Write-Host ""

# Install additional requirements
Write-Host "Installing additional requirements..." -ForegroundColor Cyan
pip install -r requirements_win.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some packages may have failed to install" -ForegroundColor Yellow
}

Write-Host "✅ Requirements installed" -ForegroundColor Green
Write-Host ""

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Setup Complete!                                            ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Activate the environment (next time):"
Write-Host "     conda activate $envName" -ForegroundColor Cyan
Write-Host ""
Write-Host "  2. Prepare your dataset (update configs/data.yaml first)"
Write-Host "     python src/dataset_tools.py prepare_calibration ..." -ForegroundColor Cyan
Write-Host ""
Write-Host "  3. Train a model:"
Write-Host "     python src/train.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. Export to ONNX:"
Write-Host "     `$env:PYTHONPATH = `\".\`"" -ForegroundColor Cyan
Write-Host "     python src/export/1_pt_to_onnx.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "  5. Convert to RKNN (on WSL/Ubuntu):"
Write-Host "     python src/export/2_onnx_to_rknn.py" -ForegroundColor Cyan

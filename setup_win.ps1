# YOLO Vision Pipeline - Windows Setup Script
# 此脚本用于配置 YOLOv8 训练和 ONNX 导出的 Conda 环境

$ErrorActionPreference = 'Stop'

# 获取脚本当前所在目录，确保所有路径操作的绝对安全
$ScriptDir = $PSScriptRoot
if ([string]::IsNullOrEmpty($ScriptDir)) { $ScriptDir = (Get-Location).Path }

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  YOLO Vision Pipeline RKNN - Windows Setup                   ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`nThis script will set up three Conda environments for:" -ForegroundColor Yellow
Write-Host "  1. YOLOv8 model training with the official Ultralytics repo (source install)"
Write-Host "  2. ONNX export with the Rockchip-customized Ultralytics repo"
Write-Host "  3. X-AnyLabeling with GPU acceleration (CUDA 12)`n"

# Helpers
function Fail($msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

function CheckCommand($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Fail "$name not found. $hint"
    }
}

# 1. 检查必要命令
Write-Host "Checking required commands..." -ForegroundColor Cyan
CheckCommand conda "Please install Miniconda or Anaconda: https://docs.conda.io/en/latest/miniconda.html"
CheckCommand git "Please install Git (https://git-scm.com/)"
Write-Host "✅ Required commands present`n" -ForegroundColor Green

# 1.5 接受 Conda 服务条款
Write-Host "Accepting Conda Terms of Service..." -ForegroundColor Cyan
& conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>$null
& conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>$null
& conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2 2>$null
Write-Host "✅ Terms of Service accepted`n" -ForegroundColor Green

# 2. 创建 Conda 环境（若已存在则跳过）
$trainEnvName = "rknn-yolov8-train"
$exportEnvName = "rknn-yolov8-export"
$labelEnvName = "x-anylabeling-cu12"
$thirdPartyDir = Join-Path $ScriptDir "3rdparty"

function EnsureCondaEnv($name, $pythonVersion) {
    Write-Host "Preparing Conda environment: $name" -ForegroundColor Cyan

    $envList = & conda env list 2>$null
    $envExists = $false
    if ($envList) {
        $envExists = [bool]($envList | Select-String -Pattern "\b$name\b" -Quiet)
    }

    if (-not $envExists) {
        Write-Host "Creating Conda environment: $name" -ForegroundColor Cyan
        & conda create -n $name python=$pythonVersion pip -y
        if ($LASTEXITCODE -ne 0) { Fail "Failed to create Conda environment '$name' (exit $LASTEXITCODE)" }
        Write-Host "✅ Environment created`n" -ForegroundColor Green
    }
    else {
        Write-Host "Conda environment '$name' already exists. Skipping creation.`n" -ForegroundColor Yellow
    }
}

function InstallSharedDeps($name) {
    Write-Host "Installing PyTorch with CUDA support into '$name'..." -ForegroundColor Cyan
    & conda run -n $name --no-capture-output pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install PyTorch in '$name' (exit $LASTEXITCODE)" }

    $reqFile = Join-Path $ScriptDir "requirements_win.txt"
    if (-not (Test-Path $reqFile -PathType Leaf)) {
        Fail "requirements_win.txt not found at $reqFile"
    }

    Write-Host "Installing shared Python dependencies into '$name'..." -ForegroundColor Cyan
    & conda run -n $name --no-capture-output pip install -r $reqFile
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install shared requirements in '$name' (exit $LASTEXITCODE)" }
}

EnsureCondaEnv $trainEnvName "3.10"
EnsureCondaEnv $exportEnvName "3.10"
EnsureCondaEnv $labelEnvName "3.12"

InstallSharedDeps $trainEnvName
InstallSharedDeps $exportEnvName

# 为 X-AnyLabeling 环境创建激活后脚本以配置 CUDA 库路径
function SetupCondaActivationHook($envName) {
    Write-Host "Setting up activation hook for '$envName'..." -ForegroundColor Cyan
    
    # 获取 conda 环境路径
    $envPath = & conda run -n $envName --no-capture-output python -c "import sys; print(sys.prefix)"
    
    # 创建激活脚本目录
    $activateDir = Join-Path $envPath "etc" "conda" "activate.d"
    if (-not (Test-Path $activateDir)) {
        New-Item -ItemType Directory -Force -Path $activateDir | Out-Null
    }
    
    # 创建 PowerShell 激活脚本
    $psActivateScript = Join-Path $activateDir "cuda-path.ps1"
    $psContent = @"
# Automatically add CUDA library paths to PATH
`$env:PATH = "`$env:CONDA_PREFIX\Library\bin;" + `$env:PATH
`$env:PATH = "`$env:CONDA_PREFIX\bin;" + `$env:PATH
"@
    Set-Content -Path $psActivateScript -Value $psContent -Encoding UTF8
    
    # 创建 CMD 激活脚本
    $cmdActivateScript = Join-Path $activateDir "cuda-path.bat"
    $cmdContent = @"
@echo off
set "PATH=%CONDA_PREFIX%\Library\bin;%PATH%"
set "PATH=%CONDA_PREFIX%\bin;%PATH%"
"@
    Set-Content -Path $cmdActivateScript -Value $cmdContent -Encoding UTF8
    
    Write-Host "✅ Activation hooks created`n" -ForegroundColor Green
}

SetupCondaActivationHook $labelEnvName

# 3. 克隆并安装官方 YOLO（训练环境）
Write-Host "Setting up official Ultralytics YOLO for '$trainEnvName'..." -ForegroundColor Cyan
$officialYoloDir = Join-Path $thirdPartyDir "ultralytics"

if (-not (Test-Path $officialYoloDir -PathType Container)) {
    Write-Host "  Cloning ultralytics..." -ForegroundColor Cyan
    if (-not (Test-Path $thirdPartyDir)) { New-Item -ItemType Directory -Force -Path $thirdPartyDir | Out-Null }
    Push-Location $thirdPartyDir
    try {
        & git clone https://github.com/ultralytics/ultralytics.git
        if ($LASTEXITCODE -ne 0) { Fail "Failed to clone official Ultralytics repository. Check your network." }
    }
    finally { Pop-Location }
}
else {
    Write-Host "  ultralytics already exists" -ForegroundColor Yellow
}

if (-not (Test-Path $officialYoloDir -PathType Container)) { Fail "Expected repository folder $officialYoloDir not found after clone." }

Push-Location $officialYoloDir
try {
    Write-Host "  Installing as development package..." -ForegroundColor Cyan
    & conda run -n $trainEnvName --no-capture-output pip install -e .
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install official Ultralytics in '$trainEnvName' (exit $LASTEXITCODE)" }
}
finally { Pop-Location }

Write-Host "✅ Official YOLO installed`n" -ForegroundColor Green

# 4. 克隆并安装 Rockchip 定制版 YOLO（导出环境）
Write-Host "Setting up Rockchip-customized YOLOv8..." -ForegroundColor Cyan
$yoloDir = Join-Path $thirdPartyDir "ultralytics_yolov8"

if (-not (Test-Path $yoloDir -PathType Container)) {
    Write-Host "  Cloning ultralytics_yolov8..." -ForegroundColor Cyan
    if (-not (Test-Path $thirdPartyDir)) { New-Item -ItemType Directory -Force -Path $thirdPartyDir | Out-Null }
    Push-Location $thirdPartyDir
    try {
        & git clone https://github.com/airockchip/ultralytics_yolov8.git
        if ($LASTEXITCODE -ne 0) { Fail "Failed to clone repository. Check your network." }
    }
    finally { Pop-Location }
}
else {
    Write-Host "  ultralytics_yolov8 already exists" -ForegroundColor Yellow
}

# 明确进入 YOLO 目录执行本地安装
if (-not (Test-Path $yoloDir -PathType Container)) { Fail "Expected repository folder $yoloDir not found after clone." }

Push-Location $yoloDir
try {
    Write-Host "  Installing as development package..." -ForegroundColor Cyan
    & conda run -n $exportEnvName --no-capture-output pip install -e .
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install Rockchip Ultralytics in '$exportEnvName' (exit $LASTEXITCODE)" }
}
finally { Pop-Location }

Write-Host "✅ Rockchip YOLOv8 installed`n" -ForegroundColor Green

# 5. 克隆并安装 X-AnyLabeling（标注环境）
Write-Host "Setting up X-AnyLabeling with CUDA 12 GPU support..." -ForegroundColor Cyan
$xAnyLabelingDir = Join-Path $thirdPartyDir "x-anylabeling"

if (-not (Test-Path $xAnyLabelingDir -PathType Container)) {
    Write-Host "  Cloning X-AnyLabeling..." -ForegroundColor Cyan
    if (-not (Test-Path $thirdPartyDir)) { New-Item -ItemType Directory -Force -Path $thirdPartyDir | Out-Null }
    Push-Location $thirdPartyDir
    try {
        & git clone https://github.com/CVHub520/X-AnyLabeling.git x-anylabeling
        if ($LASTEXITCODE -ne 0) { Fail "Failed to clone X-AnyLabeling repository. Check your network." }
    }
    finally { Pop-Location }
}
else {
    Write-Host "  x-anylabeling already exists" -ForegroundColor Yellow
}

if (-not (Test-Path $xAnyLabelingDir -PathType Container)) { Fail "Expected repository folder $xAnyLabelingDir not found after clone." }

Push-Location $xAnyLabelingDir
try {
    Write-Host "  Installing X-AnyLabeling with GPU extras..." -ForegroundColor Cyan
    & conda run -n $labelEnvName --no-capture-output pip install -e ".[gpu]"
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install X-AnyLabeling in '$labelEnvName' (exit $LASTEXITCODE)" }

    Write-Host "  Installing NVIDIA CUDA packages (cublas and cudnn)..." -ForegroundColor Cyan
    & conda run -n $labelEnvName --no-capture-output pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
    if ($LASTEXITCODE -ne 0) { Fail "Failed to install NVIDIA CUDA packages in '$labelEnvName' (exit $LASTEXITCODE)" }
}
finally { Pop-Location }

Write-Host "✅ X-AnyLabeling installed`n" -ForegroundColor Green

# 6. 完成提示
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Setup Complete!                                             ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Activate the training environment (official YOLO):"
Write-Host "     conda activate $trainEnvName" -ForegroundColor Cyan
Write-Host "`n  2. Activate the export environment (Rockchip YOLO):"
Write-Host "     conda activate $exportEnvName" -ForegroundColor Cyan
Write-Host "`n  3. Activate the labeling environment (X-AnyLabeling GPU cu12):"
Write-Host "     conda activate $labelEnvName" -ForegroundColor Cyan
Write-Host "`n  4. Prepare your dataset (update configs/data.yaml first)"
Write-Host "     python src/dataset_tools.py prepare_calibration ..." -ForegroundColor Cyan
Write-Host "`n  5. Train a model (training env):"
Write-Host "     python src/train.py" -ForegroundColor Cyan
Write-Host "`n  6. Export to ONNX (export env):"
Write-Host '     $env:PYTHONPATH = ".\"' -ForegroundColor Cyan
Write-Host "     python src/export/1_pt_to_onnx.py" -ForegroundColor Cyan
Write-Host "`n  7. Convert to RKNN (on WSL/Ubuntu):"
Write-Host "     python src/export/2_onnx_to_rknn.py" -ForegroundColor Cyan

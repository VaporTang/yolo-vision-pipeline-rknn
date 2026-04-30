# Windows batch-like script for common tasks
# Usage: scripts\commands.bat [command] [options]

@echo off
setlocal enabledelayedexpansion

set PYTHON=python
set CONDA_ENV=rknn-yolov8

if "%1"=="" (
    call :print_usage
    exit /b 0
)

set COMMAND=%1
shift

if /i "%COMMAND%"=="train" (
    call :train_model %*
) else if /i "%COMMAND%"=="export" (
    call :export_model %*
) else if /i "%COMMAND%"=="prepare-calibration" (
    call :prepare_calib %*
) else if /i "%COMMAND%"=="help" (
    call :print_help %1
) else (
    echo Unknown command: %COMMAND%
    call :print_usage
    exit /b 1
)
exit /b 0

:print_usage
echo YOLO Vision Pipeline - Common Commands
echo.
echo Usage: scripts\commands.bat [command] [options]
echo.
echo Commands:
echo   train               Start training with default config
echo   export              Export model to ONNX
echo   prepare-calibration Prepare calibration dataset
echo   help                Show help for a command
echo.
echo Examples:
echo   scripts\commands.bat train --epochs 200
echo   scripts\commands.bat export
echo   scripts\commands.bat prepare-calibration --num-images 30
exit /b 0

:train_model
echo Starting training...
set CMD=%PYTHON% src\train.py
:train_loop
if "%1"=="" goto :train_run
if "%1"=="--epochs" (
    set CMD=!CMD! --epochs %2
    shift
    shift
    goto :train_loop
)
if "%1"=="--batch" (
    set CMD=!CMD! --batch %2
    shift
    shift
    goto :train_loop
)
shift
goto :train_loop
:train_run
%CMD%
exit /b %errorlevel%

:export_model
echo Exporting model to ONNX...
set CMD=%PYTHON% src\export\1_pt_to_onnx.py
:export_loop
if "%1"=="" goto :export_run
if "%1"=="--simplify" (
    set CMD=!CMD! --simplify
    shift
    goto :export_loop
)
shift
goto :export_loop
:export_run
set PYTHONPATH=.
%CMD%
exit /b %errorlevel%

:print_help
exit /b 0

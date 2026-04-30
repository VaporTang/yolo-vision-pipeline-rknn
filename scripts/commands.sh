#!/bin/bash
# Makefile-like script for common tasks
# Usage: bash scripts/commands.sh [command]

set -e

PYTHON=${PYTHON:-python}
CONDA_ENV=${CONDA_ENV:-rknn-yolov8}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    cat << EOF
YOLO Vision Pipeline - Common Commands

Usage: bash scripts/commands.sh [command] [options]

Commands:
  train               Start training with default config
  export              Export model to ONNX
  prepare-calibration Prepare calibration dataset
  convert             Convert ONNX to RKNN
  check-overlaps      Check for overlapping boxes
  split-dataset       Split dataset into train/valid
  filter-classes      Remove specified classes

Options vary by command. Use 'command help' for details.

Examples:
  bash scripts/commands.sh train --epochs 200
  bash scripts/commands.sh export
  bash scripts/commands.sh prepare-calibration --num-images 30
  bash scripts/commands.sh convert --platform rk3568

EOF
}

print_help() {
    case $1 in
        train)
            echo "Train a model"
            echo "Usage: bash scripts/commands.sh train [options]"
            echo "Options:"
            echo "  --epochs N        Number of epochs (default: 300)"
            echo "  --batch N         Batch size (default: auto)"
            echo "  --model NAME      Model variant (default: yolov8l.pt)"
            echo "  --device N        GPU device (default: 0)"
            ;;
        export)
            echo "Export model to ONNX"
            echo "Usage: bash scripts/commands.sh export [options]"
            echo "Options:"
            echo "  --input FILE      Input .pt file (default: models/best.pt)"
            echo "  --output FILE     Output .onnx file (default: models/best.onnx)"
            echo "  --simplify        Use onnxsim to simplify model"
            ;;
        prepare-calibration)
            echo "Prepare calibration dataset for quantization"
            echo "Usage: bash scripts/commands.sh prepare-calibration [options]"
            echo "Options:"
            echo "  --image-dir DIR   Source images directory"
            echo "  --num-images N    Number of images to select (default: 20)"
            echo "  --output FILE     Output dataset.txt file"
            ;;
        convert)
            echo "Convert ONNX model to RKNN"
            echo "Usage: bash scripts/commands.sh convert [options]"
            echo "Options:"
            echo "  --input FILE      Input ONNX file (default: models/best.onnx)"
            echo "  --output FILE     Output RKNN file (default: models/best.rknn)"
            echo "  --platform NAME   Target platform (rk3588, rk3568, etc.)"
            echo "  --no-quant        Skip quantization"
            ;;
        *)
            print_usage
            ;;
    esac
}

# Commands
train_model() {
    echo -e "${GREEN}Starting training...${NC}"
    
    # Build python command
    cmd="$PYTHON src/train.py"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --epochs) cmd="$cmd --epochs $2"; shift 2 ;;
            --batch) cmd="$cmd --batch $2"; shift 2 ;;
            --model) cmd="$cmd --model $2"; shift 2 ;;
            --device) cmd="$cmd --device $2"; shift 2 ;;
            *) shift ;;
        esac
    done
    
    eval $cmd
}

export_model() {
    echo -e "${GREEN}Exporting model to ONNX...${NC}"
    
    cmd="$PYTHON src/export/1_pt_to_onnx.py"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --input) cmd="$cmd --input $2"; shift 2 ;;
            --output) cmd="$cmd --output $2"; shift 2 ;;
            --simplify) cmd="$cmd --simplify"; shift ;;
            *) shift ;;
        esac
    done
    
    eval $cmd
}

prepare_calib() {
    echo -e "${GREEN}Preparing calibration dataset...${NC}"
    
    cmd="$PYTHON src/dataset_tools.py prepare_calibration"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --image-dir) cmd="$cmd --image-dir $2"; shift 2 ;;
            --output) cmd="$cmd --output $2"; shift 2 ;;
            --num-images) cmd="$cmd --num-images $2"; shift 2 ;;
            *) shift ;;
        esac
    done
    
    eval $cmd
}

convert_model() {
    echo -e "${GREEN}Converting ONNX to RKNN...${NC}"
    
    cmd="$PYTHON src/export/2_onnx_to_rknn.py"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --input) cmd="$cmd --input $2"; shift 2 ;;
            --output) cmd="$cmd --output $2"; shift 2 ;;
            --platform) cmd="$cmd --platform $2"; shift 2 ;;
            --no-quant) cmd="$cmd --no-quant"; shift ;;
            *) shift ;;
        esac
    done
    
    eval $cmd
}

# Main
if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

COMMAND=$1
shift

case $COMMAND in
    train)
        train_model "$@"
        ;;
    export)
        export_model "$@"
        ;;
    prepare-calibration|prepare_calibration)
        prepare_calib "$@"
        ;;
    convert)
        convert_model "$@"
        ;;
    help)
        if [ $# -eq 0 ]; then
            print_usage
        else
            print_help "$1"
        fi
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        print_usage
        exit 1
        ;;
esac

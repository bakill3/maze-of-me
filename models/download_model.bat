#!/bin/bash
set -e

MODEL_DIR="models"
MODEL_NAME="Phi-3-mini-4k-instruct-q4.gguf"
MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_DIR/$MODEL_NAME" ]; then
    echo "Model already exists: $MODEL_DIR/$MODEL_NAME"
else
    echo "Downloading model from $MODEL_URL ..."
    curl -L "$MODEL_URL" -o "$MODEL_DIR/$MODEL_NAME"
    echo "Model downloaded to $MODEL_DIR/$MODEL_NAME"
fi

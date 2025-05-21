#!/bin/bash
set -e

MODEL_NAME="Phi-3-mini-4k-instruct-q4.gguf"
MODEL_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

if [ -f "$MODEL_NAME" ]; then
    echo "Model already exists: $MODEL_NAME"
else
    echo "Downloading model from $MODEL_URL ..."
    curl -L "$MODEL_URL" -o "$MODEL_NAME"
    echo "Model downloaded to $MODEL_NAME"
fi

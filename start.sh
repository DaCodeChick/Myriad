#!/bin/bash

# ==========================================
# CONFIGURATION VARIABLES
# ==========================================
# Model Paths
TEXT_MODEL="$HOME/Downloads/L3-8B-Stheno-v3.2-Q5_K_M.gguf"
VISION_MODEL="$HOME/Downloads/ggml-model-Q5_K_M.gguf"
VISION_PROJ="$HOME/Downloads/mmproj-model-f16.gguf"

# Hardware Acceleration (--usecublas for NVIDIA, --usevulkan for AMD)
HW_FLAG="--usecublas"
GPU_LAYERS="99"

# Network Ports
TEXT_PORT="5001"
VISION_PORT="5002"
# ==========================================

echo "🚀 Booting Project Myriad Ecosystem..."

# Create logs directory if it doesn't exist
mkdir -p logs

trap "kill 0" SIGINT

echo "🧠 Booting Text Brain on Port $TEXT_PORT (Max GPU / 8K Context)..."
koboldcpp "$TEXT_MODEL" $HW_FLAG --gpulayers $GPU_LAYERS --contextsize 8192 --port $TEXT_PORT > logs/text.log 2>&1 &

echo "👁️ Booting Vision Eyes on Port $VISION_PORT (Partial GPU / 2K Context)..."
# Using 15 layers and 2048 context to save VRAM for the main text model
koboldcpp "$VISION_MODEL" --mmproj "$VISION_PROJ" $HW_FLAG --gpulayers 15 --contextsize 2048 --port $VISION_PORT > logs/vision.log 2>&1 &

echo "⏳ Waiting 25 seconds for both models to load into VRAM..."
# Increased sleep time to ensure the vision server finishes loading before Python tries to connect!
sleep 25

echo "🤖 Starting Myriad Python Core..."
echo "   (Autonomy engine runs integrated in the main process if AUTONOMY_ENABLED=true)"
uv run python main.py 

echo "✅ System shutting down..."

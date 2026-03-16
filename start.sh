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

# ... (keep your variables at the top) ...

echo "🚀 Booting Project Myriad Ecosystem..."

# Create logs directory if it doesn't exist
mkdir -p logs

trap "kill 0" SIGINT

echo "🧠 Booting Text Brain on Port $TEXT_PORT (Max GPU / 8K Context)..."
koboldcpp "$TEXT_MODEL" $HW_FLAG --gpulayers $GPU_LAYERS --contextsize 8192 --port $TEXT_PORT > /dev/null 2>&1 &

echo "👁️ Booting Vision Eyes on Port $VISION_PORT (Partial GPU / 2K Context)..."
# We drop Moondream's context to 2048, and lower its GPU layers to 15 to save VRAM!
koboldcpp "$VISION_MODEL" --mmproj "$VISION_PROJ" $HW_FLAG --gpulayers 15 --contextsize 2048 --port $VISION_PORT > /dev/null 2>&1 &

echo "⏳ Waiting 15 seconds for the models to load..."
sleep 15

echo "🤖 Starting Myriad Python Core..."
echo "   (Autonomy engine runs integrated in the main process if AUTONOMY_ENABLED=true)"
uv run python main.py 

echo "✅ System shutting down..."

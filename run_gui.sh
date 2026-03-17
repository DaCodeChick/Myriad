#!/bin/bash
# Myriad GUI Launcher
# Starts the Myriad Control Panel GUI

cd "$(dirname "$0")"
uv run python myriad_gui.py

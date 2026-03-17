#!/usr/bin/env python3
"""
Myriad Control Panel - GUI for monitoring and controlling Project Myriad

Features:
- Start/Stop brain and vision servers
- Edit .env configuration with live validation
- Unified log output from all components
- Real-time status monitoring
"""

import sys
import os
import subprocess
import signal
from pathlib import Path
from typing import Optional, Dict

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QTextEdit,
    QLabel,
    QSpinBox,
    QComboBox,
    QFormLayout,
    QSplitter,
    QMessageBox,
)
from PySide6.QtCore import Qt, QProcess, QTimer, Signal
from PySide6.QtGui import QTextCursor, QFont


class EnvConfigWidget(QWidget):
    """Widget for editing .env configuration"""

    config_changed = Signal()

    def __init__(self, env_path: str):
        super().__init__()
        self.env_path = env_path
        self.config_widgets: Dict[str, QWidget] = {}
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """Initialize the configuration UI"""
        layout = QVBoxLayout()

        # Discord Configuration
        discord_group = QGroupBox("Discord Configuration")
        discord_layout = QFormLayout()

        self.discord_token = QLineEdit()
        self.discord_token.setEchoMode(QLineEdit.EchoMode.Password)
        discord_layout.addRow("Discord Token:", self.discord_token)

        self.whitelisted_bots = QLineEdit()
        self.whitelisted_bots.setPlaceholderText("Comma-separated bot IDs")
        discord_layout.addRow("Whitelisted Bot IDs:", self.whitelisted_bots)

        discord_group.setLayout(discord_layout)
        layout.addWidget(discord_group)

        # LLM Configuration
        llm_group = QGroupBox("LLM Configuration")
        llm_layout = QFormLayout()

        self.llm_provider = QComboBox()
        self.llm_provider.addItems(["local", "gemini"])
        llm_layout.addRow("LLM Provider:", self.llm_provider)

        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        llm_layout.addRow("LLM API Key:", self.llm_api_key)

        self.llm_base_url = QLineEdit()
        llm_layout.addRow("LLM Base URL:", self.llm_base_url)

        self.llm_model = QLineEdit()
        llm_layout.addRow("LLM Model:", self.llm_model)

        self.gemini_api_key = QLineEdit()
        self.gemini_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        llm_layout.addRow("Gemini API Key:", self.gemini_api_key)

        self.gemini_model = QLineEdit()
        llm_layout.addRow("Gemini Model:", self.gemini_model)

        llm_group.setLayout(llm_layout)
        layout.addWidget(llm_group)

        # Vision Configuration
        vision_group = QGroupBox("Vision Configuration")
        vision_layout = QFormLayout()

        self.vision_enabled = QCheckBox()
        vision_layout.addRow("Vision Enabled:", self.vision_enabled)

        self.vision_api_key = QLineEdit()
        vision_layout.addRow("Vision API Key:", self.vision_api_key)

        self.vision_base_url = QLineEdit()
        vision_layout.addRow("Vision Base URL:", self.vision_base_url)

        self.vision_model = QLineEdit()
        vision_layout.addRow("Vision Model:", self.vision_model)

        vision_group.setLayout(vision_layout)
        layout.addWidget(vision_group)

        # Memory Configuration
        memory_group = QGroupBox("Memory Configuration")
        memory_layout = QFormLayout()

        self.short_term_limit = QSpinBox()
        self.short_term_limit.setRange(1, 100)
        memory_layout.addRow("Short Term Memory Limit:", self.short_term_limit)

        self.vector_memory_enabled = QCheckBox()
        memory_layout.addRow("Vector Memory Enabled:", self.vector_memory_enabled)

        self.embedding_model = QLineEdit()
        memory_layout.addRow("Embedding Model:", self.embedding_model)

        self.semantic_recall_limit = QSpinBox()
        self.semantic_recall_limit.setRange(1, 50)
        memory_layout.addRow("Semantic Recall Limit:", self.semantic_recall_limit)

        memory_group.setLayout(memory_layout)
        layout.addWidget(memory_group)

        # Tools Configuration
        tools_group = QGroupBox("Tools Configuration")
        tools_layout = QFormLayout()

        self.tools_enabled = QCheckBox()
        tools_layout.addRow("Tools Enabled:", self.tools_enabled)

        self.max_tool_iterations = QSpinBox()
        self.max_tool_iterations.setRange(1, 20)
        tools_layout.addRow("Max Tool Iterations:", self.max_tool_iterations)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # Logging Configuration
        logging_group = QGroupBox("Logging Configuration")
        logging_layout = QFormLayout()

        self.brain_console_logging = QCheckBox()
        logging_layout.addRow("Brain Console Logging:", self.brain_console_logging)

        self.brain_file_logging = QCheckBox()
        logging_layout.addRow("Brain File Logging:", self.brain_file_logging)

        self.eyes_console_logging = QCheckBox()
        logging_layout.addRow("Eyes Console Logging:", self.eyes_console_logging)

        self.eyes_file_logging = QCheckBox()
        logging_layout.addRow("Eyes File Logging:", self.eyes_file_logging)

        logging_group.setLayout(logging_layout)
        layout.addWidget(logging_group)

        # Save/Reload buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Save Configuration")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)

        reload_btn = QPushButton("🔄 Reload Configuration")
        reload_btn.clicked.connect(self.load_config)
        button_layout.addWidget(reload_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        self.setLayout(layout)

    def load_config(self):
        """Load configuration from .env file"""
        if not os.path.exists(self.env_path):
            QMessageBox.warning(
                self, "Warning", f".env file not found: {self.env_path}"
            )
            return

        config = {}
        with open(self.env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

        # Load values into widgets
        self.discord_token.setText(config.get("DISCORD_TOKEN", ""))
        self.whitelisted_bots.setText(config.get("WHITELISTED_BOT_IDS", ""))

        self.llm_provider.setCurrentText(config.get("LLM_PROVIDER", "local"))
        self.llm_api_key.setText(config.get("LLM_API_KEY", ""))
        self.llm_base_url.setText(
            config.get("LLM_BASE_URL", "http://localhost:5001/v1")
        )
        self.llm_model.setText(config.get("LLM_MODEL", "gpt-4"))
        self.gemini_api_key.setText(config.get("GEMINI_API_KEY", ""))
        self.gemini_model.setText(config.get("GEMINI_MODEL", "gemini-1.5-pro"))

        self.vision_enabled.setChecked(
            config.get("VISION_ENABLED", "false").lower() == "true"
        )
        self.vision_api_key.setText(config.get("VISION_API_KEY", "not-needed"))
        self.vision_base_url.setText(
            config.get("VISION_BASE_URL", "http://localhost:5002/v1")
        )
        self.vision_model.setText(config.get("VISION_MODEL", "vision-model"))

        self.short_term_limit.setValue(int(config.get("SHORT_TERM_MEMORY_LIMIT", "10")))
        self.vector_memory_enabled.setChecked(
            config.get("VECTOR_MEMORY_ENABLED", "true").lower() == "true"
        )
        self.embedding_model.setText(
            config.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        )
        self.semantic_recall_limit.setValue(
            int(config.get("SEMANTIC_RECALL_LIMIT", "5"))
        )

        self.tools_enabled.setChecked(
            config.get("TOOLS_ENABLED", "true").lower() == "true"
        )
        self.max_tool_iterations.setValue(int(config.get("MAX_TOOL_ITERATIONS", "5")))

        self.brain_console_logging.setChecked(
            config.get("ENABLE_BRAIN_CONSOLE_LOGGING", "false").lower() == "true"
        )
        self.brain_file_logging.setChecked(
            config.get("ENABLE_BRAIN_FILE_LOGGING", "false").lower() == "true"
        )
        self.eyes_console_logging.setChecked(
            config.get("ENABLE_EYES_CONSOLE_LOGGING", "false").lower() == "true"
        )
        self.eyes_file_logging.setChecked(
            config.get("ENABLE_EYES_FILE_LOGGING", "false").lower() == "true"
        )

    def save_config(self):
        """Save configuration to .env file"""
        lines = []

        # Read original file to preserve comments and structure
        if os.path.exists(self.env_path):
            with open(self.env_path, "r") as f:
                original_lines = f.readlines()
        else:
            original_lines = []

        # Build config dict from widgets
        config = {
            "DISCORD_TOKEN": self.discord_token.text(),
            "WHITELISTED_BOT_IDS": self.whitelisted_bots.text(),
            "LLM_PROVIDER": self.llm_provider.currentText(),
            "LLM_API_KEY": self.llm_api_key.text(),
            "LLM_BASE_URL": self.llm_base_url.text(),
            "LLM_MODEL": self.llm_model.text(),
            "GEMINI_API_KEY": self.gemini_api_key.text(),
            "GEMINI_MODEL": self.gemini_model.text(),
            "VISION_ENABLED": "true" if self.vision_enabled.isChecked() else "false",
            "VISION_API_KEY": self.vision_api_key.text(),
            "VISION_BASE_URL": self.vision_base_url.text(),
            "VISION_MODEL": self.vision_model.text(),
            "SHORT_TERM_MEMORY_LIMIT": str(self.short_term_limit.value()),
            "VECTOR_MEMORY_ENABLED": "true"
            if self.vector_memory_enabled.isChecked()
            else "false",
            "EMBEDDING_MODEL": self.embedding_model.text(),
            "SEMANTIC_RECALL_LIMIT": str(self.semantic_recall_limit.value()),
            "TOOLS_ENABLED": "true" if self.tools_enabled.isChecked() else "false",
            "MAX_TOOL_ITERATIONS": str(self.max_tool_iterations.value()),
            "ENABLE_BRAIN_CONSOLE_LOGGING": "true"
            if self.brain_console_logging.isChecked()
            else "false",
            "ENABLE_BRAIN_FILE_LOGGING": "true"
            if self.brain_file_logging.isChecked()
            else "false",
            "ENABLE_EYES_CONSOLE_LOGGING": "true"
            if self.eyes_console_logging.isChecked()
            else "false",
            "ENABLE_EYES_FILE_LOGGING": "true"
            if self.eyes_file_logging.isChecked()
            else "false",
        }

        # Process original lines, updating values
        for line in original_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in config:
                    lines.append(f"{key}={config[key]}\n")
                    del config[key]  # Remove from dict so we don't duplicate
                else:
                    lines.append(line)  # Keep original line
            else:
                lines.append(line)  # Keep comments and empty lines

        # Add any new config values that weren't in original file
        if config:
            lines.append("\n# Added by Myriad GUI\n")
            for key, value in config.items():
                lines.append(f"{key}={value}\n")

        # Write back to file
        with open(self.env_path, "w") as f:
            f.writelines(lines)

        self.config_changed.emit()
        QMessageBox.information(self, "Success", "Configuration saved successfully!")


class ProcessControlWidget(QWidget):
    """Widget for controlling brain and vision processes"""

    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.brain_process: Optional[QProcess] = None
        self.vision_process: Optional[QProcess] = None
        self.myriad_process: Optional[QProcess] = None
        self.init_ui()

    def init_ui(self):
        """Initialize the process control UI"""
        layout = QHBoxLayout()

        # Brain Server Control
        self.brain_toggle = QPushButton("▶️ Brain")
        self.brain_toggle.setCheckable(True)
        self.brain_toggle.setStyleSheet(
            "QPushButton:checked { background-color: #2d5016; }"
        )
        self.brain_toggle.clicked.connect(self.toggle_brain)
        layout.addWidget(self.brain_toggle)

        # Vision Server Control
        self.vision_toggle = QPushButton("▶️ Vision")
        self.vision_toggle.setCheckable(True)
        self.vision_toggle.setStyleSheet(
            "QPushButton:checked { background-color: #2d5016; }"
        )
        self.vision_toggle.clicked.connect(self.toggle_vision)
        layout.addWidget(self.vision_toggle)

        # Myriad Core Control
        self.myriad_toggle = QPushButton("▶️ Myriad")
        self.myriad_toggle.setCheckable(True)
        self.myriad_toggle.setStyleSheet(
            "QPushButton:checked { background-color: #2d5016; }"
        )
        self.myriad_toggle.clicked.connect(self.toggle_myriad)
        layout.addWidget(self.myriad_toggle)

        # All Control (toggle)
        self.all_toggle = QPushButton("▶️ All")
        self.all_toggle.setCheckable(True)
        self.all_toggle.setStyleSheet(
            "QPushButton:checked { background-color: #2d5016; }"
        )
        self.all_toggle.clicked.connect(self.toggle_all)
        layout.addWidget(self.all_toggle)

        self.setLayout(layout)

    def toggle_brain(self, checked):
        """Toggle brain server on/off"""
        if checked:
            self.start_brain()
        else:
            self.stop_brain()

    def toggle_vision(self, checked):
        """Toggle vision server on/off"""
        if checked:
            self.start_vision()
        else:
            self.stop_vision()

    def toggle_myriad(self, checked):
        """Toggle Myriad core on/off"""
        if checked:
            self.start_myriad()
        else:
            self.stop_myriad()

    def toggle_all(self, checked):
        """Toggle all processes on/off"""
        if checked:
            self.start_all()
        else:
            self.stop_all()

    def start_brain(self):
        """Start the brain server (koboldcpp)"""
        if (
            self.brain_process
            and self.brain_process.state() == QProcess.ProcessState.Running
        ):
            QMessageBox.warning(self, "Warning", "Brain server is already running")
            return

        # Read configuration from start.sh
        script_path = Path(__file__).parent / "start.sh"
        if not script_path.exists():
            QMessageBox.critical(self, "Error", "start.sh not found")
            return

        # Parse start.sh to get configuration
        with open(script_path, "r") as f:
            script_content = f.read()

        # Extract variables (simplified parsing)
        import re

        text_model_match = re.search(r'TEXT_MODEL="([^"]+)"', script_content)
        hw_flag_match = re.search(r'HW_FLAG="([^"]+)"', script_content)
        gpu_layers_match = re.search(r'GPU_LAYERS="([^"]+)"', script_content)
        text_port_match = re.search(r'TEXT_PORT="([^"]+)"', script_content)

        if not all(
            [text_model_match, hw_flag_match, gpu_layers_match, text_port_match]
        ):
            QMessageBox.critical(
                self, "Error", "Could not parse start.sh configuration"
            )
            return

        text_model = os.path.expandvars(text_model_match.group(1))
        hw_flag = hw_flag_match.group(1)
        gpu_layers = gpu_layers_match.group(1)
        text_port = text_port_match.group(1)

        # Start koboldcpp
        self.brain_process = QProcess(self)
        self.brain_process.readyReadStandardOutput.connect(
            lambda: self.handle_brain_output()
        )
        self.brain_process.readyReadStandardError.connect(
            lambda: self.handle_brain_error()
        )
        self.brain_process.finished.connect(self.brain_finished)

        cmd = [
            "koboldcpp",
            text_model,
            hw_flag,
            "--gpulayers",
            gpu_layers,
            "--contextsize",
            "8192",
            "--port",
            text_port,
        ]

        self.brain_process.start(cmd[0], cmd[1:])

        if self.brain_process.waitForStarted():
            self.brain_toggle.setText("⏹️ Brain")
            self.brain_toggle.setChecked(True)
        else:
            QMessageBox.critical(self, "Error", "Failed to start brain server")

    def stop_brain(self):
        """Stop the brain server"""
        if (
            self.brain_process
            and self.brain_process.state() == QProcess.ProcessState.Running
        ):
            self.brain_process.terminate()
            if not self.brain_process.waitForFinished(3000):
                self.brain_process.kill()

    def brain_finished(self):
        """Handle brain process finished"""
        self.brain_toggle.setText("▶️ Brain")
        self.brain_toggle.setChecked(False)
        self.update_all_button_state()

    def start_vision(self):
        """Start the vision server (koboldcpp with vision)"""
        if (
            self.vision_process
            and self.vision_process.state() == QProcess.ProcessState.Running
        ):
            QMessageBox.warning(self, "Warning", "Vision server is already running")
            return

        # Parse start.sh for vision configuration
        script_path = Path(__file__).parent / "start.sh"
        with open(script_path, "r") as f:
            script_content = f.read()

        import re

        vision_model_match = re.search(r'VISION_MODEL="([^"]+)"', script_content)
        vision_proj_match = re.search(r'VISION_PROJ="([^"]+)"', script_content)
        hw_flag_match = re.search(r'HW_FLAG="([^"]+)"', script_content)
        vision_port_match = re.search(r'VISION_PORT="([^"]+)"', script_content)

        if not all(
            [vision_model_match, vision_proj_match, hw_flag_match, vision_port_match]
        ):
            QMessageBox.critical(
                self, "Error", "Could not parse vision configuration from start.sh"
            )
            return

        vision_model = os.path.expandvars(vision_model_match.group(1))
        vision_proj = os.path.expandvars(vision_proj_match.group(1))
        hw_flag = hw_flag_match.group(1)
        vision_port = vision_port_match.group(1)

        self.vision_process = QProcess(self)
        self.vision_process.readyReadStandardOutput.connect(
            lambda: self.handle_vision_output()
        )
        self.vision_process.readyReadStandardError.connect(
            lambda: self.handle_vision_error()
        )
        self.vision_process.finished.connect(self.vision_finished)

        cmd = [
            "koboldcpp",
            vision_model,
            "--mmproj",
            vision_proj,
            hw_flag,
            "--gpulayers",
            "0",
            "--contextsize",
            "2048",
            "--port",
            vision_port,
        ]

        self.vision_process.start(cmd[0], cmd[1:])

        if self.vision_process.waitForStarted():
            self.vision_toggle.setText("⏹️ Vision")
            self.vision_toggle.setChecked(True)
        else:
            QMessageBox.critical(self, "Error", "Failed to start vision server")

    def stop_vision(self):
        """Stop the vision server"""
        if (
            self.vision_process
            and self.vision_process.state() == QProcess.ProcessState.Running
        ):
            self.vision_process.terminate()
            if not self.vision_process.waitForFinished(3000):
                self.vision_process.kill()

    def vision_finished(self):
        """Handle vision process finished"""
        self.vision_toggle.setText("▶️ Vision")
        self.vision_toggle.setChecked(False)
        self.update_all_button_state()

    def start_myriad(self):
        """Start the Myriad core process"""
        if (
            self.myriad_process
            and self.myriad_process.state() == QProcess.ProcessState.Running
        ):
            QMessageBox.warning(self, "Warning", "Myriad is already running")
            return

        self.myriad_process = QProcess(self)
        self.myriad_process.readyReadStandardOutput.connect(
            lambda: self.handle_myriad_output()
        )
        self.myriad_process.readyReadStandardError.connect(
            lambda: self.handle_myriad_error()
        )
        self.myriad_process.finished.connect(self.myriad_finished)

        # Use uv run to execute in the correct environment
        self.myriad_process.start("uv", ["run", "python", "main.py"])

        if self.myriad_process.waitForStarted():
            self.myriad_toggle.setText("⏹️ Myriad")
            self.myriad_toggle.setChecked(True)
        else:
            QMessageBox.critical(self, "Error", "Failed to start Myriad")

    def stop_myriad(self):
        """Stop the Myriad core process"""
        if (
            self.myriad_process
            and self.myriad_process.state() == QProcess.ProcessState.Running
        ):
            self.myriad_process.terminate()
            if not self.myriad_process.waitForFinished(3000):
                self.myriad_process.kill()

    def myriad_finished(self):
        """Handle Myriad process finished"""
        self.myriad_toggle.setText("▶️ Myriad")
        self.myriad_toggle.setChecked(False)
        self.update_all_button_state()

    def update_all_button_state(self):
        """Update the All button state based on individual process states"""
        # Check if all processes are stopped
        all_stopped = (
            not self.brain_toggle.isChecked()
            and not self.vision_toggle.isChecked()
            and not self.myriad_toggle.isChecked()
        )

        if all_stopped:
            self.all_toggle.setText("▶️ All")
            self.all_toggle.setChecked(False)

    def start_all(self):
        """Start all processes"""
        self.start_brain()
        # Wait a bit before starting vision and myriad
        QTimer.singleShot(2000, self.start_vision)
        QTimer.singleShot(15000, self.start_myriad)
        # Update all toggle button
        self.all_toggle.setText("⏹️ All")
        self.all_toggle.setChecked(True)

    def stop_all(self):
        """Stop all processes"""
        self.stop_myriad()
        self.stop_vision()
        self.stop_brain()
        # Update all toggle button
        self.all_toggle.setText("▶️ All")
        self.all_toggle.setChecked(False)

    def handle_brain_output(self):
        """Handle brain process stdout"""
        if self.brain_process:
            data = self.brain_process.readAllStandardOutput().data().decode()
            if self.parent_window:
                self.parent_window.append_log(f"[BRAIN] {data}")

    def handle_brain_error(self):
        """Handle brain process stderr"""
        if self.brain_process:
            data = self.brain_process.readAllStandardError().data().decode()
            if self.parent_window:
                self.parent_window.append_log(f"[BRAIN ERROR] {data}")

    def handle_vision_output(self):
        """Handle vision process stdout"""
        if self.vision_process:
            data = self.vision_process.readAllStandardOutput().data().decode()
            if self.parent_window:
                self.parent_window.append_log(f"[VISION] {data}")

    def handle_vision_error(self):
        """Handle vision process stderr"""
        if self.vision_process:
            data = self.vision_process.readAllStandardError().data().decode()
            if self.parent_window:
                self.parent_window.append_log(f"[VISION ERROR] {data}")

    def handle_myriad_output(self):
        """Handle Myriad process stdout"""
        if self.myriad_process:
            data = self.myriad_process.readAllStandardOutput().data().decode()
            if self.parent_window:
                self.parent_window.append_log(f"[MYRIAD] {data}")

    def handle_myriad_error(self):
        """Handle Myriad process stderr"""
        if self.myriad_process:
            data = self.myriad_process.readAllStandardError().data().decode()
            if self.parent_window:
                self.parent_window.append_log(f"[MYRIAD ERROR] {data}")


class LogViewerWidget(QWidget):
    """Widget for viewing unified logs"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the log viewer UI"""
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()

        clear_btn = QPushButton("🗑️ Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()

        self.autoscroll_checkbox = QCheckBox("Auto-scroll")
        self.autoscroll_checkbox.setChecked(True)
        toolbar.addWidget(self.autoscroll_checkbox)

        layout.addLayout(toolbar)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Monospace", 9))
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def append_log(self, text: str):
        """Append text to the log viewer"""
        self.log_text.append(text.rstrip())
        if self.autoscroll_checkbox.isChecked():
            self.log_text.moveCursor(QTextCursor.End)

    def clear_logs(self):
        """Clear all logs"""
        self.log_text.clear()


class MyriadControlPanel(QMainWindow):
    """Main control panel window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Myriad Control Panel")
        self.setGeometry(100, 100, 1200, 800)
        self.init_ui()

    def init_ui(self):
        """Initialize the main UI"""
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Create horizontal splitter for main content
        splitter = QSplitter(Qt.Horizontal)

        # Left side: Process control at top (fixed), config scrollable below
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        left_widget.setLayout(left_layout)

        # Process Control (compact bar at very top)
        process_group = QGroupBox("Process Control")
        process_group_layout = QVBoxLayout()
        process_group_layout.setContentsMargins(5, 5, 5, 5)
        self.process_control = ProcessControlWidget(self)
        process_group_layout.addWidget(self.process_control)
        process_group.setLayout(process_group_layout)
        left_layout.addWidget(process_group)

        # Separator line
        from PySide6.QtWidgets import QFrame

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(line)

        # Configuration (scrollable)
        from PySide6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        env_path = Path(__file__).parent / ".env"
        self.config_widget = EnvConfigWidget(str(env_path))
        scroll.setWidget(self.config_widget)

        left_layout.addWidget(scroll)

        # Right side: Log viewer
        self.log_viewer = LogViewerWidget()

        splitter.addWidget(left_widget)
        splitter.addWidget(self.log_viewer)
        splitter.setSizes([500, 700])

        main_layout.addWidget(splitter)

    def append_log(self, text: str):
        """Append text to log viewer (called by ProcessControlWidget)"""
        self.log_viewer.append_log(text)

    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Stop all running processes and exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.process_control.stop_all()
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Myriad Control Panel")

    window = MyriadControlPanel()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

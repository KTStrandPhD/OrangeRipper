import os
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QFileDialog, QDialogButtonBox
)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OrangeRipper - Settings")
        self.resize(500, 250)
        
        self.config_path = "config.json"
        self.config = self.load_config()

        self.init_ui()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config_to_file(self):
        # Update config dictionary with current form values
        rip_conf = self.config.setdefault("ripping", {})
        rip_conf["output_dir"] = self.input_dir.text().strip() or "output"
        rip_conf["audio_format"] = self.combo_format.currentText()
        rip_conf["encoding_quality"] = self.combo_quality.currentText()

        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)

        rip_conf = self.config.get("ripping", {})
        current_dir = rip_conf.get("output_dir", "output")
        current_format = rip_conf.get("audio_format", "FLAC")
        current_quality = rip_conf.get("encoding_quality", "Best (--best)")

        # --- Destination Folder Selection ---
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Destination Folder:"))
        self.input_dir = QLineEdit(current_dir)
        dir_layout.addWidget(self.input_dir)
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_folder)
        dir_layout.addWidget(btn_browse)
        layout.addLayout(dir_layout)

        # --- Audio Output Format ---
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Audio Format:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["FLAC", "MP3", "WAV"])
        self.combo_format.setCurrentText(current_format)
        format_layout.addWidget(self.combo_format)
        layout.addLayout(format_layout)

        # --- Encoding Quality ---
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Encoding Quality:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems([
            "320 kbps (Best MP3)",
            "192 kbps (Standard MP3)",
            "128 kbps (Fast MP3)",
            "Level 8 (Max FLAC)",
            "Level 5 (Default FLAC)",
            "Level 0 (Fast FLAC)"
        ])
        self.combo_quality.setCurrentText(current_quality)
        quality_layout.addWidget(self.combo_quality)
        layout.addLayout(quality_layout)

        # --- Dialog Buttons ---
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.input_dir.text())
        if dir_path:
            self.input_dir.setText(dir_path)

    def accept_settings(self):
        self.save_config_to_file()
        self.accept()

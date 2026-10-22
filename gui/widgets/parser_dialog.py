from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, 
    QPushButton, QHBoxLayout, QMessageBox
)
from services.parser import TracklistParser

class ParserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Tracklist Parser")
        self.resize(500, 400)

        self.parsed_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Instructions
        label_instructions = QLabel(
            "Paste raw tracklist text below (e.g., Artist - Album followed by track numbers):\n"
            "Example:\n"
            "Artist Name - Album Title\n"
            "1. Track One (3:45)\n"
            "2. Track Two"
        )
        layout.addWidget(label_instructions)

        # Text Editor for Pasting
        self.text_input = QTextEdit()
        layout.addWidget(self.text_input)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        self.btn_parse = QPushButton("Parse and Apply")
        self.btn_parse.clicked.connect(self.process_text)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_parse)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def process_text(self):
        raw_text = self.text_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "Warning", "Please paste some text to parse.")
            return

        try:
            # Utilize your existing TracklistParser backend service
            self.parsed_data = TracklistParser.parse_text_block(raw_text)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse text: {str(e)}")

    get_parsed_metadata = lambda self: self.parsed_data

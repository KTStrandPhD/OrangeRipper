from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QDialogButtonBox, QMessageBox
)

class ManualSearchDialog(QDialog):
    """Dialog allowing users to manually specify search terms or a direct Discogs Release ID."""
    def __init__(self, parent=None, initial_artist="", initial_album=""):
        super().__init__(parent)
        self.setWindowTitle("OrangeRipper - Manual Metadata Search")
        self.resize(450, 280)

        self.query_data = None
        self.initial_artist = initial_artist
        self.initial_album = initial_album

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        instructions = QLabel(
            "<b>Automated CD lookup found no matches.</b><br>"
            "Please enter search criteria or a direct Discogs Release ID (e.g. 3068011):"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Artist Field
        artist_layout = QHBoxLayout()
        artist_layout.addWidget(QLabel("Artist:"))
        self.input_artist = QLineEdit(self.initial_artist)
        artist_layout.addWidget(self.input_artist)
        layout.addLayout(artist_layout)

        # Album Field
        album_layout = QHBoxLayout()
        album_layout.addWidget(QLabel("Album:"))
        self.input_album = QLineEdit(self.initial_album)
        album_layout.addWidget(self.input_album)
        layout.addLayout(album_layout)

        # Catalog Number Field
        catno_layout = QHBoxLayout()
        catno_layout.addWidget(QLabel("Catalog No:"))
        self.input_catno = QLineEdit()
        catno_layout.addWidget(self.input_catno)
        layout.addLayout(catno_layout)

        # Discogs Release ID Field
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Discogs ID:"))
        self.input_release_id = QLineEdit()
        self.input_release_id.setPlaceholderText("e.g. 3068011")
        id_layout.addWidget(self.input_release_id)
        layout.addLayout(id_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_search = QPushButton("Search Discogs")
        self.btn_search.setStyleSheet("font-weight: bold; background-color: #4a6fa5; color: white; padding: 6px;")
        self.btn_search.clicked.connect(self.process_search)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_search)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def process_search(self):
        artist = self.input_artist.text().strip()
        album = self.input_album.text().strip()
        catno = self.input_catno.text().strip()
        raw_id = self.input_release_id.text().strip()

        release_id = int(raw_id) if raw_id.isdigit() else None

        if not artist and not album and not catno and not release_id:
            QMessageBox.warning(self, "Warning", "Please provide at least an artist, album title, catalog number, or Release ID.")
            return

        self.query_data = {
            "artist": artist if artist else None,
            "album": album if album else None,
            "catno": catno if catno else None,
            "release_id": release_id
        }
        self.accept()

    def get_query_data(self):
        return self.query_data

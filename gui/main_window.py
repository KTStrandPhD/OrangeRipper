import os
import json
import requests
import platform
import ctypes
from PyQt6.QtGui import QPixmap, QImage, QAction, QIcon
from PyQt6.QtCore import Qt, QCoreApplication, QTimer, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QGroupBox, QMessageBox, QTextEdit, QProgressBar, QDialog, QGraphicsOpacityEffect
)
from ripperCore.ripper import CDRipper
from services.metadata_manager import MetadataManager
from gui.widgets.metadata_table import MetadataTable
from gui.widgets.parser_dialog import ParserDialog
from gui.widgets.settings_dialog import SettingsDialog
from gui.workers import RipWorker

def load_config():
    config_path = "config.json"
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    # Sanitize ripping output directory for Windows if it carries a Linux path
    rip_conf = config.setdefault("ripping", {})
    out_dir = rip_conf.get("output_dir", "output")
    if platform.system() == "Windows" and (out_dir.startswith("/home/") or (out_dir.startswith("/") and not os.path.exists(out_dir))):
        rip_conf["output_dir"] = os.path.join(os.path.expanduser("~"), "Music")

    return config

class MetadataWorker(QThread):
    """Background worker thread to handle CD scanning and metadata lookups without freezing the GUI."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)

    def __init__(self, meta_manager, drive_path, user_query=None):
        super().__init__()
        self.meta_manager = meta_manager
        self.drive_path = drive_path
        self.user_query = user_query

    def run(self):
        try:
            self.progress.emit("Scanning CD drive and reading TOC...")
            ripper = CDRipper(device_path=self.drive_path)
            disc_info = ripper.get_disc_info()

            if not disc_info:
                self.finished.emit({"success": False, "message": "No physical CD detected or drive is empty."})
                return

            discid = disc_info["discid"]
            self.progress.emit(f"Found DiscID {discid}. Looking up metadata...")

            # Fetch metadata via manager (handles MusicBrainz -> Discogs -> AcoustID + sample rip)
            result = self.meta_manager.fetch_metadata_for_cd(
                discid=discid,
                user_query=self.user_query
            )
            
            self.finished.emit({"success": True, "discid": discid, "result": result})
        except Exception as e:
            self.finished.emit({"success": False, "message": str(e)})


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OrangeRipper - CD Ripping Utility")
        self.resize(800, 600)

        # --- Menu Bar ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        settings_action = file_menu.addAction("Settings...")
        settings_action.triggered.connect(self.open_settings)

        donate_action = QAction("Donate / Support", self)
        donate_action.triggered.connect(self.show_donate_dialog)
        file_menu.addAction(donate_action)

        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About OrangeRipper")
        about_action.triggered.connect(self.show_about)

        self.worker = None
        self.meta_worker = None
        self.last_discid = None  # Track state to detect changes/removal

        self.init_ui()

        # Set Application Icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "app.ico")
        if not os.path.exists(icon_path):
            icon_path = "assets/app.ico" # Fallback relative path
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # --- Automatic Disc Polling Timer ---
        self.disc_timer = QTimer(self)
        self.disc_timer.setInterval(3000)  # Check every 3 seconds
        self.disc_timer.timeout.connect(self.check_disc_status)
        self.disc_timer.start()

        # Load configuration keys
        config = load_config()
        self.discogs_token = config.get("discogs", {}).get("user_token")
        self.acoustid_key = config.get("acoustid", {}).get("api_key")
        self.meta_manager = MetadataManager(discogs_token=self.discogs_token, acoustid_key=self.acoustid_key)

    def clear_metadata(self):
        """Resets all metadata fields, artwork, and the track table."""
        self.input_artist.clear()
        self.input_album.clear()
        self.input_year.clear()
        self.current_cover_url = None
        self.art_label.setText("No Cover Art")
        self.art_label.setPixmap(QPixmap())
        self.track_table.setRowCount(0)

    def toggle_select_all(self):
        """Flips the select state of all tracks in the table."""
        self.select_all_toggled = not self.select_all_toggled
        self.track_table.set_all_checked(self.select_all_toggled)

    def get_optical_drive(self):
        """Returns the correct optical drive path depending on the operating system."""
        if platform.system() == "Windows":
            return f"{self.detect_windows_cd_drive()}:"
        return "/dev/sr0"

    def detect_windows_cd_drive(self):
        """Dynamically scans logical drives to find the actual physical CD-ROM drive, ignoring virtual ISOs."""
        if platform.system() != "Windows":
            return "D"
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            cd_drives = []
            
            for letter in range(26):
                if bitmask & (1 << letter):
                    d_letter = chr(65 + letter)
                    drive_path = f"{d_letter}:\\"
                    
                    # DRIVE_CDROM value is 5 in the Windows API
                    if ctypes.windll.kernel32.GetDriveTypeW(drive_path) == 5:
                        # Check volume label to avoid virtual Windows installer ISOs (like CCOCOMA)
                        volume_name = ctypes.create_unicode_buffer(261)
                        ctypes.windll.kernel32.GetVolumeInformationW(
                            drive_path, volume_name, ctypes.sizeof(volume_name), None, None, None, None, 0
                        )
                        label = volume_name.value.upper()
                        
                        # If it's an installer ISO, skip it if possible
                        if "CCOCOMA" in label or "WIN" in label:
                            continue
                            
                        cd_drives.append(d_letter)
            
            # If we found a clean physical drive, return it (e.g., 'E')
            if cd_drives:
                return cd_drives[-1]  # Usually the physical drive is the higher letter
                
        except Exception:
            pass
            
        # Hard fallback to 'E' based on your VM layout if dynamic check hits a snag
        return "E"

    def check_disc_status(self):
        """Periodically checks if a CD is present or changed in the drive."""
        try:
            drive_path = self.get_optical_drive()
            
            if platform.system() != "Windows" and not os.path.exists(drive_path):
                self.status_label.setText("CD Drive not detected. Please Connect Drive")
                self.last_discid = None
                return

            ripper = CDRipper(device_path=drive_path)
            disc_info = ripper.get_disc_info()
            current_discid = disc_info.get("discid") if disc_info else None

            # Case 1: A disc was present, but now it's removed
            if self.last_discid is not None and current_discid is None:
                self.clear_metadata()
                self.status_label.setText("Status: Disc removed. Drive is empty.")
                self.last_discid = None

            # Case 2: A new disc was inserted
            elif current_discid is not None and current_discid != self.last_discid:
                self.last_discid = current_discid
                self.scan_cd()

        except Exception as e:
            self.status_label.setText("CD Drive not detected. Please Connect Drive")
            self.last_discid = None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Control Panel ---
        top_layout = QHBoxLayout()
        drive_display = self.get_optical_drive()
        self.btn_scan = QPushButton(f"Scan CD Drive ({drive_display})")
        self.btn_scan.clicked.connect(self.scan_cd)
        top_layout.addWidget(self.btn_scan)

        # Add Manual Paste Parser Button
        self.btn_parser = QPushButton("Paste Tracklist (Manual)")
        self.btn_parser.clicked.connect(self.open_parser_dialog)
        top_layout.addWidget(self.btn_parser)
        
        main_layout.addLayout(top_layout)

        # --- Metadata Info Group with Cover Art ---
        meta_group = QGroupBox("Album Metadata")
        meta_outer_layout = QHBoxLayout(meta_group)

        # Left side: Cover Art Thumbnail
        self.art_label = QLabel("No Cover Art")
        self.art_label.setFixedSize(140, 140)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet("border: 1px solid #555; background-color: #222; color: #888;")
        meta_outer_layout.addWidget(self.art_label)

        # Right side: Text Fields
        meta_text_layout = QVBoxLayout()

        artist_layout = QHBoxLayout()
        artist_layout.addWidget(QLabel("Artist:"))
        self.input_artist = QLineEdit()
        artist_layout.addWidget(self.input_artist)
        meta_text_layout.addLayout(artist_layout)

        album_layout = QHBoxLayout()
        album_layout.addWidget(QLabel("Album:"))
        self.input_album = QLineEdit()
        album_layout.addWidget(self.input_album)
        meta_text_layout.addLayout(album_layout)

        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("Year:"))
        self.input_year = QLineEdit()
        year_layout.addWidget(self.input_year)
        meta_text_layout.addLayout(year_layout)

        meta_outer_layout.addLayout(meta_text_layout)
        main_layout.addWidget(meta_group)

        # --- Tracklist Section ---
        track_header_layout = QHBoxLayout()
        track_header_layout.addWidget(QLabel("<b>Tracks to Rip:</b>"))
        
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setFixedWidth(140)
        self.btn_select_all.setStyleSheet(
            "font-weight: bold; background-color: #4a6fa5; color: white; padding: 5px; border-radius: 4px;"
        )
        self.select_all_toggled = True
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        track_header_layout.addWidget(self.btn_select_all)

        main_layout.addLayout(track_header_layout)

        # --- Tracklist Table ---
        self.track_table = MetadataTable()
        main_layout.addWidget(self.track_table)

        # --- Bottom Rip Action Panel ---
        rip_layout = QHBoxLayout()
        self.btn_rip = QPushButton("Start Ripping")
        self.btn_rip.setStyleSheet("font-weight: bold; background-color: #2e8b57; color: white; padding: 8px;")
        self.btn_rip.clicked.connect(self.start_ripping)
        rip_layout.addWidget(self.btn_rip)

        # Red Stop Button with Opacity Effect (Faint & disabled by default when idle)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setStyleSheet("font-weight: bold; background-color: #cd5c5c; color: white; padding: 8px;")
        
        self.stop_opacity = QGraphicsOpacityEffect(self.btn_stop)
        self.btn_stop.setGraphicsEffect(self.stop_opacity)
        self.stop_opacity.setOpacity(0.3)  # Faint muted placeholder state when idle
        self.btn_stop.setEnabled(False)
        
        self.btn_stop.clicked.connect(self.stop_ripping)
        rip_layout.addWidget(self.btn_stop)

        main_layout.addLayout(rip_layout)

        # --- Progress & Status ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Status: Ready to scan CD or paste tracklist.")
        main_layout.addWidget(self.status_label)

        # --- Output Location Display ---
        self.output_label = QLabel()
        self.update_output_display()
        main_layout.addWidget(self.output_label)

    def update_output_display(self):
        config = load_config()
        out_dir = config.get("ripping", {}).get("output_dir", "output")
        abs_path = os.path.abspath(out_dir)
        self.output_label.setText(f"📁 Output Location: {abs_path}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_output_display()
            self.status_label.setText("Status: Settings updated successfully.")

    def show_about(self):
        QMessageBox.information(self, "About OrangeRipper", "OrangeRipper v1.0\nA PyQt6 CD Ripping & Encoding Utility for Linux & Windows.")

    def load_cover_art(self, url):
        if not url:
            self.art_label.setText("No Cover Art")
            self.art_label.setPixmap(QPixmap())
            return

        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                image = QImage()
                image.loadFromData(response.content)
                pixmap = QPixmap.fromImage(image)
                self.art_label.setPixmap(pixmap.scaled(
                    self.art_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.art_label.setText("No Art Found")
                self.art_label.setPixmap(QPixmap())
        except Exception as e:
            print(f"Failed to load cover art: {e}")
            self.art_label.setText("No Art Found")
            self.art_label.setPixmap(QPixmap())

    def open_parser_dialog(self):
        dialog = ParserDialog(self)
        if dialog.exec() == ParserDialog.DialogCode.Accepted:
            data = dialog.get_parsed_metadata()
            if data:
                self.input_artist.setText(data.get("artist", ""))
                self.input_album.setText(data.get("album", ""))
                self.input_year.setText("")
                
                tracks = data.get("tracks", [])
                self.track_table.load_tracklist(tracks)
                
                self.status_label.setText(f"Status: Loaded metadata successfully via Manual Text Parser ({len(tracks)} tracks).")

    def scan_cd(self):
        drive_path = self.get_optical_drive()
        
        if platform.system() != "Windows" and not os.path.exists(drive_path):
            self.clear_metadata()
            self.status_label.setText("CD Drive not detected. Please Connect Drive")
            QMessageBox.warning(self, "Drive Warning", "CD Drive not detected. Please connect a drive.")
            return

        self.clear_metadata()
        self.status_label.setText(f"Status: Scanning CD drive ({drive_path}) and querying databases...")
        
        # Disable controls during asynchronous scan
        self.btn_scan.setEnabled(False)
        self.btn_parser.setEnabled(False)

        current_artist = self.input_artist.text().strip()
        current_album = self.input_album.text().strip()
        query = {"artist": current_artist, "album": current_album} if (current_artist or current_album) else None

        # Launch background metadata worker thread
        self.meta_worker = MetadataWorker(self.meta_manager, drive_path, user_query=query)
        self.meta_worker.progress.connect(self.on_meta_progress)
        self.meta_worker.finished.connect(self.on_meta_finished)
        self.meta_worker.start()

    def on_meta_progress(self, message):
        self.status_label.setText(f"Status: {message}")

    def on_meta_finished(self, response):
        self.btn_scan.setEnabled(True)
        self.btn_parser.setEnabled(True)

        if not response.get("success"):
            msg = response.get("message", "Unknown error during scan.")
            self.status_label.setText(f"Status: {msg}")
            if "No physical CD" in msg:
                QMessageBox.warning(self, "Drive Warning", msg)
            else:
                QMessageBox.critical(self, "Error", f"CD Drive not detected or error occurred: {msg}")
            return

        discid = response.get("discid")
        self.last_discid = discid
        result = response.get("result", {})
        data = result.get("data")

        if data:
            self.input_artist.setText(data.get("artist", ""))
            self.input_album.setText(data.get("title", ""))
            self.input_year.setText(str(data.get("year", "")))
            
            self.current_cover_url = data.get("cover_art_url")
            self.load_cover_art(self.current_cover_url)
            
            tracks = data.get("tracklist", []) or data.get("tracks", [])
            self.track_table.load_tracklist(tracks)
            
            self.status_label.setText(f"Status: Loaded metadata successfully via {result.get('source', 'Unknown')}.")
        else:
            QMessageBox.information(self, "Not Found", "No automated match found. Switch to manual parsing.")
            self.status_label.setText("Status: Metadata lookup returned no match.")

    def start_ripping(self):
        artist = self.input_artist.text().strip()
        album = self.input_album.text().strip()
        year = self.input_year.text().strip()
        tracks = self.track_table.get_updated_tracklist()

        if not tracks:
            QMessageBox.warning(self, "Warning", "No tracks loaded to rip! Scan a CD or paste a tracklist first.")
            return

        config = load_config()
        rip_conf = config.get("ripping", {})
        output_dir = rip_conf.get("output_dir", "output")
        audio_format = rip_conf.get("audio_format", "FLAC")
        quality = rip_conf.get("encoding_quality", "Best (--best)")

        metadata = {
            "artist": artist if artist else "Unknown Artist",
            "title": album if album else "Unknown Album",
            "year": year,
            "tracks": tracks,
            "cover_art_url": getattr(self, "current_cover_url", None),
            "output_dir": output_dir,
            "audio_format": audio_format,
            "encoding_quality": quality
        }

        self.btn_scan.setEnabled(False)
        self.btn_parser.setEnabled(False)
        self.btn_rip.setEnabled(False)
        self.btn_rip.setText("Ripping in Progress...")
        
        # Make Stop button fully opaque and active during ripping
        self.stop_opacity.setOpacity(1.0)
        self.btn_stop.setEnabled(True)
        
        self.progress_bar.setValue(0)

        drive_path = self.get_optical_drive()
        self.worker = RipWorker(device_path=drive_path, metadata=metadata)
        self.worker.progress.connect(self.on_rip_progress)
        self.worker.finished.connect(self.on_rip_finished)
        self.worker.start()

    def stop_ripping(self):
        """Triggers cancellation of the active ripping worker."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Status: Cancelling rip...")
            self.stop_opacity.setOpacity(0.3)
            self.btn_stop.setEnabled(False)

    def on_rip_progress(self, pct, message):
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"Status: {message}")

    def on_rip_finished(self, success, message):
        self.btn_scan.setEnabled(True)
        self.btn_parser.setEnabled(True)
        self.btn_rip.setEnabled(True)
        self.btn_rip.setText("Start Ripping")
        
        # Return Stop button to faint and inactive when finished
        self.stop_opacity.setOpacity(0.3)
        self.btn_stop.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Status: Ripping complete.")
        else:
            self.status_label.setText(f"Status: {message}")

    def show_donate_dialog(self):
        """Displays a popup dialog with donation links and info."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Support OrangeRipper")
        dialog.setFixedSize(600, 360)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(
            "<h3>Support OrangeRipper Development</h3>"
            "<p>OrangeRipper is free, open-source software. If it makes your "
            "CD ripping workflow smoother, consider fueling future updates or buying me a coffee!</p>"
            "<p>Written for <a href='https://www.instagram.com/orangerecordsfargo/'>Orange Records</a> by Kyle T Strand - <a href='mailto:kyletstrand@gmail.com'>kyletstrand@gmail.com</a></p>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        links_label = QLabel(
            '<b>Ways to support:</b>'
            '<ul>'
            '<li><a href="https://ko-fi.com/kyletstrand">Ko-fi (Buy me a coffee)</a></li>'
            '</ul>'
        )
        links_label.setOpenExternalLinks(True)
        layout.addWidget(links_label)

        close_btn = QPushButton("Close", dialog)
        close_btn.setStyleSheet("padding: 6px; font-weight: bold;")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

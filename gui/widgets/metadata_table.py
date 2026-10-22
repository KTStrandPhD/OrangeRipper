from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt

def format_duration(raw_duration) -> str:
  """Converts milliseconds (int/str) or seconds into a clean MM:SS string."""
  if not raw_duration:
      return "0:00"
  
  try:
      # If it's coming from MusicBrainz as milliseconds (e.g., 564000)
      ms = int(raw_duration)
      total_seconds = ms // 1000
      minutes = total_seconds // 60
      seconds = total_seconds % 60
      return f"{minutes}:{seconds:02d}"
  except (ValueError, TypeError):
      # If it's already a formatted string or something else, return as-is
      return str(raw_duration)

class MetadataTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Select", "Track #", "Title", "Duration"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

    def load_tracklist(self, tracks):
        """Populates the table with tracks, defaulting checkboxes to checked."""
        self.setRowCount(len(tracks))
        for row, trk in enumerate(tracks):
            # 1. Checkbox item
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)
            self.setItem(row, 0, chk_item)

            # 2. Track Number
            num_item = QTableWidgetItem(str(trk.get("track_number", row + 1)))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 1, num_item)

            # 3. Track Title
            title_item = QTableWidgetItem(str(trk.get("title", "")))
            self.setItem(row, 2, title_item)

            # 4. Duration
            #duration_item = QTableWidgetItem(str(trk.get("duration", "")))
            raw_dur = trk.get("duration", "")
            duration_item = QTableWidgetItem(format_duration(raw_dur))
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(row, 3, duration_item)

    def set_all_checked(self, checked=True):
        """Toggles all track checkboxes on or off."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                item.setCheckState(state)

    def get_updated_tracklist(self):
        """Retrieves only the tracks that have their checkboxes checked."""
        tracks = []
        for row in range(self.rowCount()):
            chk_item = self.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                try:
                    num = int(self.item(row, 1).text())
                except Exception:
                    num = row + 1
                
                title = self.item(row, 2).text()
                duration = self.item(row, 3).text()

                tracks.append({
                    "track_number": num,
                    "title": title,
                    "duration": duration
                })
        return tracks

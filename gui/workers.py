from PyQt6.QtCore import QThread, pyqtSignal
import os
import sys
import time
import subprocess
import requests
from mutagen.flac import FLAC, Picture
from ripperCore.ripper import CDRipper

def get_binary_path(binary_name):
    """Returns the correct path to a binary whether running from source or PyInstaller bundle."""
    if os.name == 'nt' and not binary_name.endswith('.exe'):
        binary_name += '.exe'

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        bundled_path = os.path.join(base_path, 'bin', binary_name)
        if os.path.exists(bundled_path):
            return bundled_path

    local_path = os.path.join(os.path.abspath("."), "bin", binary_name)
    if os.path.exists(local_path):
        return local_path

    return binary_name

class RipWorker(QThread):
    progress = pyqtSignal(int, str)       # (percentage, status_message)
    track_finished = pyqtSignal(int, str) # (track_number, track_title)
    finished = pyqtSignal(bool, str)      # (success_bool, message)

    def __init__(self, device_path, metadata):
        super().__init__()
        self.device_path = device_path
        self.metadata = metadata
        self._is_cancelled = False
        self.current_process = None

    def cancel(self):
        """Signals the worker to stop and forcefully kills any active subprocess."""
        self._is_cancelled = True
        if self.current_process:
            try:
                self.current_process.kill()
            except Exception:
                pass

    def run(self):
        try:
            artist = self.metadata.get("artist", "Unknown Artist")
            album = self.metadata.get("title", "Unknown Album")
            year = self.metadata.get("year", "")
            tracks = self.metadata.get("tracks", [])
            cover_url = self.metadata.get("cover_art_url")
            base_output_dir = self.metadata.get("output_dir", "output")
            audio_format = self.metadata.get("audio_format", "FLAC")
            quality_setting = self.metadata.get("encoding_quality", "Best (--best)")

            total_tracks = len(tracks)
            if total_tracks == 0:
                self.finished.emit(False, "No tracks found to rip.")
                return

            safe_artist = "".join(c if c.isalnum() or c in " .-_" else "_" for c in artist).strip()
            safe_album = "".join(c if c.isalnum() or c in " .-_" else "_" for c in album).strip()
            
            album_output_path = os.path.join(base_output_dir, safe_artist, safe_album)
            os.makedirs(album_output_path, exist_ok=True)

            cover_art_data = None
            if cover_url:
                for attempt in range(1, 4):
                    try:
                        res = requests.get(cover_url, timeout=5)
                        if res.status_code == 200:
                            cover_art_data = res.content
                            break
                    except Exception as e:
                        print(f"Cover art download attempt {attempt}/3 failed: {e}")
                    
                    if attempt < 3:
                        time.sleep(1)
                
                if not cover_art_data:
                    print("Failed to download cover art after 3 attempts.")

            self.progress.emit(0, f"Preparing to rip '{album}' by {artist}...")
            ripper = CDRipper(device_path=self.device_path)

            # Define creation flags to suppress terminal windows on Windows
            creation_flags = 0x08000000 if sys.platform == "win32" else 0

            for index, trk in enumerate(tracks):
                if self._is_cancelled:
                    self.finished.emit(False, "Ripping cancelled by user.")
                    return

                track_num = trk.get("track_number", index + 1)
                title = trk.get("title", f"Track {track_num}")
                
                pct = int((index / total_tracks) * 100)
                self.progress.emit(pct, f"Ripping Track {track_num}: {title}...")

                raw_track_str = f"{track_num:02d} - {title}"
                safe_track_name = "".join(c if c.isalnum() or c in " .-_" else "_" for c in raw_track_str).strip()
                wav_path = os.path.join(album_output_path, f"temp_{track_num}.wav")

                # --- 1. Extract WAV via CDRipper (platform-agnostic backend) ---
                success = ripper.rip_track(track_num, wav_path)
                if not success or self._is_cancelled:
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                    msg = "Ripping cancelled by user." if self._is_cancelled else f"Failed to extract track {track_num}."
                    self.finished.emit(False, msg)
                    return

                # --- 2. Encode to Target Format (FLAC, MP3, or WAV) ---
                if audio_format == "FLAC":
                    final_path = os.path.join(album_output_path, f"{safe_track_name}.flac")
                    
                    flac_flag = "--best"
                    if "Level 5" in quality_setting:
                        flac_flag = "-5"
                    elif "Level 0" in quality_setting:
                        flac_flag = "--fast"
                    elif "Level 8" in quality_setting:
                        flac_flag = "--best"

                    flac_bin = get_binary_path("flac")
                    cmd_encode = [flac_bin, flac_flag, wav_path, "-o", final_path, "--silent"]
                    
                    # Spawn subprocess with window suppression flags
                    self.current_process = subprocess.Popen(
                        cmd_encode, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        creationflags=creation_flags
                    )

                    while self.current_process.poll() is None:
                        if self._is_cancelled:
                            self.current_process.kill()
                            if os.path.exists(wav_path):
                                os.remove(wav_path)
                            self.finished.emit(False, "Ripping cancelled by user.")
                            return
                        self.msleep(50)

                    if os.path.exists(wav_path):
                        os.remove(wav_path)

                    if self.current_process.returncode != 0 and not self._is_cancelled:
                        self.finished.emit(False, f"Failed to encode track {track_num} to FLAC.")
                        return

                    self.apply_flac_tags(final_path, artist, album, track_num, title, year, cover_art_data)

                elif audio_format == "MP3":
                    final_path = os.path.join(album_output_path, f"{safe_track_name}.mp3")
                    
                    lame_args = ["-b", "320"]
                    if "192 kbps" in quality_setting:
                        lame_args = ["-b", "192"]
                    elif "128 kbps" in quality_setting:
                        lame_args = ["-b", "128"]

                    lame_bin = get_binary_path("lame")
                    cmd_encode = [lame_bin] + lame_args + [wav_path, final_path, "--silent"]
                    
                    # Spawn subprocess with window suppression flags
                    self.current_process = subprocess.Popen(
                        cmd_encode, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        creationflags=creation_flags
                    )

                    while self.current_process.poll() is None:
                        if self._is_cancelled:
                            self.current_process.kill()
                            if os.path.exists(wav_path):
                                os.remove(wav_path)
                            self.finished.emit(False, "Ripping cancelled by user.")
                            return
                        self.msleep(50)

                    if os.path.exists(wav_path):
                        os.remove(wav_path)

                    if self.current_process.returncode != 0 and not self._is_cancelled:
                        self.finished.emit(False, f"Failed to encode track {track_num} to MP3.")
                        return

                    self.apply_mp3_tags(final_path, artist, album, track_num, title, year, cover_art_data)

                else:
                    final_path = os.path.join(album_output_path, f"{safe_track_name}.wav")
                    os.rename(wav_path, final_path)

                self.track_finished.emit(track_num, title)

            self.progress.emit(100, "Ripping and encoding completed successfully!")
            self.finished.emit(True, f"Successfully ripped and encoded {total_tracks} tracks to:\n{album_output_path}")

        except Exception as e:
            if not self._is_cancelled:
                self.finished.emit(False, f"An error occurred during ripping: {str(e)}")

    def apply_flac_tags(self, file_path, artist, album, track_num, title, year, cover_data):
        try:
            audio = FLAC(file_path)
        except Exception as e:
            print(f"Failed to load FLAC for tagging: {e}")
            return

        audio["artist"] = artist
        audio["album"] = album
        audio["title"] = title
        audio["tracknumber"] = str(track_num)
        if year:
            audio["date"] = str(year)

        if cover_data:
            try:
                image = Picture()
                image.type = 3
                image.mime = 'image/jpeg'
                image.desc = 'Cover'
                image.data = cover_data
                audio.add_picture(image)
            except Exception as e:
                print(f"Failed to embed cover art into FLAC: {e}")

        audio.save()

    def apply_mp3_tags(self, file_path, artist, album, track_num, title, year, cover_data):
        from mutagen.easyid3 import EasyID3
        from mutagen.id3 import ID3, APIC, error as ID3Error

        try:
            audio = EasyID3(file_path)
        except ID3Error:
            audio = EasyID3()
            audio.save(file_path)
            audio = EasyID3(file_path)

        audio["artist"] = artist
        audio["album"] = album
        audio["title"] = title
        audio["tracknumber"] = str(track_num)
        if year:
            audio["date"] = str(year)
        audio.save()

        if cover_data:
            try:
                audio_id3 = ID3(file_path)
                audio_id3.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=cover_data
                ))
                audio_id3.save(file_path)
            except Exception as e:
                print(f"Failed to embed cover art into MP3: {e}")

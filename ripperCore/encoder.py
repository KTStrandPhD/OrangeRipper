import os
import sys
import subprocess
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, APIC, ID3NoHeaderError
from PIL import Image

class AudioEncoder:
    @staticmethod
    def encode_wav_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "320") -> bool:
        """
        Encodes a WAV file to MP3 using bundled LAME binary, suppressing the console window on Windows.
        """
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            lame_bin = os.path.join(base_path, "bin", "lame.exe" if sys.platform == "win32" else "lame")
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            lame_bin = os.path.join(base_path, "bin", "lame.exe" if sys.platform == "win32" else "lame")
        
        if not os.path.exists(lame_bin):
            lame_bin = "lame"

        cmd = [lame_bin, "-b", str(bitrate), wav_path, mp3_path]
        
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = 0x08000000  # CREATE_NO_WINDOW flag to prevent console flashing

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creation_flags,
                check=True,
                text=True
            )
            return True
        except Exception as e:
            print(f"LAME encoding error: {e}")
            return False


class AudioTagger:
    @staticmethod
    def tag_file(file_path: str, metadata: dict, cover_art_path: str = None):
        """
        Applies metadata tags and embeds cover art based on file extension.
        metadata expected keys: title, artist, album, track_number, year, genre
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".flac":
            AudioTagger._tag_flac(file_path, metadata, cover_art_path)
        elif ext == ".mp3":
            AudioTagger._tag_mp3(file_path, metadata, cover_art_path)
        else:
            raise ValueError(f"Unsupported file format for tagging: {ext}")

    @staticmethod
    def _tag_flac(file_path: str, meta: dict, cover_path: str):
        audio = FLAC(file_path)
        audio["title"] = meta.get("title", "")
        audio["artist"] = meta.get("artist", "")
        audio["album"] = meta.get("album", "")
        audio["tracknumber"] = str(meta.get("track_number", ""))
        audio["date"] = str(meta.get("year", ""))
        audio["genre"] = meta.get("genre", "")

        if cover_path and os.path.exists(cover_path):
            picture = Picture()
            picture.type = 3  # Cover (front)
            with open(cover_path, "rb") as f:
                picture.data = f.read()
            picture.mime = "image/jpeg" if cover_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            audio.add_picture(picture)

        audio.save()

    @staticmethod
    def _tag_mp3(file_path: str, meta: dict, cover_path: str):
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()

        audio["TIT2"] = TIT2(encoding=3, text=meta.get("title", ""))
        audio["TPE1"] = TPE1(encoding=3, text=meta.get("artist", ""))
        audio["TALB"] = TALB(encoding=3, text=meta.get("album", ""))
        audio["TRCK"] = TRCK(encoding=3, text=str(meta.get("track_number", "")))
        audio["TDRC"] = TDRC(encoding=3, text=str(meta.get("year", "")))

        if cover_path and os.path.exists(cover_path):
            with open(cover_path, "rb`") as f:
                img_data = f.read()
            mime = "image/jpeg" if cover_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            audio["APIC"] = APIC(
                encoding=3,
                mime=mime,
                type=3,
                desc=u'Cover',
                data=img_data
            )

        audio.save(file_path)

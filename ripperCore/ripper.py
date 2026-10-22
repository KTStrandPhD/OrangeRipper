import os
import sys
import struct
import subprocess
import discid
from datetime import datetime

class CDRipper:
    def __init__(self, device_path: str = None):
        if device_path:
            self.device_path = device_path
        else:
            if sys.platform == "win32":
                self.device_path = f"{self.detect_windows_cd_drive()}:"
            else:
                self.device_path = "/dev/sr0"

    def detect_windows_cd_drive(self):
        """Dynamically scans logical drives to find the actual physical CD-ROM drive on Windows."""
        if sys.platform != "win32":
            return "D"
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            cd_drives = []
            
            for letter in range(26):
                if bitmask & (1 << letter):
                    d_letter = chr(65 + letter)
                    drive_path = f"{d_letter}:\\"
                    
                    if ctypes.windll.kernel32.GetDriveTypeW(drive_path) == 5:
                        volume_name = ctypes.create_unicode_buffer(261)
                        ctypes.windll.kernel32.GetVolumeInformationW(
                            drive_path, volume_name, ctypes.sizeof(volume_name), None, None, None, None, 0
                        )
                        label = volume_name.value.upper()
                        if "CCOCOMA" in label or "WIN" in label:
                            continue
                        cd_drives.append(d_letter)
            
            if cd_drives:
                return cd_drives[-1]
        except Exception:
            pass
        return "E"

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[OrangeRipper Debug {timestamp}] {message}"
        print(formatted_msg)
        
        try:
            if getattr(sys, 'frozen', False):
                log_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                log_dir = os.path.dirname(base_dir)
                
            log_path = os.path.join(log_dir, "orangeripper_debug.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")

    def get_disc_info(self):
        self._log(f"Attempting to read disc info from device: {self.device_path}")
        try:
            read_path = self.device_path
            if sys.platform == "win32" and len(read_path) == 1:
                read_path = f"{read_path}:"

            disc = discid.read(read_path)
            self._log(f"Successfully read DiscID: {disc.id}")
            
            tracks = []
            for track in disc.tracks:
                tracks.append({
                    "track_number": track.number,
                    "length": track.seconds,
                    "offset": track.offset,
                    "sectors": track.sectors if hasattr(track, 'sectors') else int(track.seconds * 75)
                })

            return {
                "discid": disc.id,
                "submission_url": disc.submission_url,
                "first_track": disc.first_track_num,
                "last_track": disc.last_track_num,
                "tracks": tracks
            }
        except Exception as e:
            self._log(f"ERROR: Failed to read CD TOC from {self.device_path}: {e}")
            return None

    def rip_track(self, track_number: int, output_wav_path: str) -> bool:
        normalized_output_path = os.path.normpath(output_wav_path)
        output_dir = os.path.dirname(normalized_output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        self._log(f"Preparing to rip track {track_number} to {normalized_output_path}")

        disc_info = self.get_disc_info()
        if not disc_info:
            self._log("ABORT: Cannot retrieve disc table of contents.")
            return False

        target_track = None
        for t in disc_info["tracks"]:
            if t["track_number"] == track_number:
                target_track = t
                break

        if not target_track:
            self._log(f"ERROR: Track {track_number} not found on disc TOC.")
            return False

        if sys.platform == "win32":
            return self._rip_track_win32(target_track, normalized_output_path)
        else:
            return self._rip_track_linux(target_track, normalized_output_path)

    def _rip_track_win32(self, track: dict, output_wav_path: str) -> bool:
        import ctypes
        
        clean_drive = self.device_path.rstrip("\\/").rstrip(":")
        device_name = f"\\\\.\\{clean_drive}:"
        
        self._log(f"Opening native Win32 device handle for {device_name} with SCSI Pass-Through Direct (SPTI)")
        
        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        INVALID_HANDLE_VALUE = -1

        handle = ctypes.windll.kernel32.CreateFileW(
            device_name,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )

        if handle == INVALID_HANDLE_VALUE:
            handle = ctypes.windll.kernel32.CreateFileW(
                device_name,
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None
            )

        if handle == INVALID_HANDLE_VALUE:
            err = ctypes.GetLastError()
            self._log(f"ERROR: Failed to open device handle {device_name}. Windows Error Code: {err}")
            return False

        try:
            sector_size = 2352
            start_sector = track["offset"]
            sector_count = track["sectors"]

            class SCSI_PASS_THROUGH_DIRECT(ctypes.Structure):
                _fields_ = [
                    ("Length", ctypes.c_ushort),
                    ("ScsiStatus", ctypes.c_ubyte),
                    ("PathId", ctypes.c_ubyte),
                    ("TargetId", ctypes.c_ubyte),
                    ("Lun", ctypes.c_ubyte),
                    ("CdbLength", ctypes.c_ubyte),
                    ("SenseInfoLength", ctypes.c_ubyte),
                    ("DataIn", ctypes.c_ubyte),
                    ("DataTransferLength", ctypes.c_ulong),
                    ("TimeOutValue", ctypes.c_ulong),
                    ("DataBuffer", ctypes.c_void_p),
                    ("SenseInfoOffset", ctypes.c_ulong),
                    ("Cdb", ctypes.c_ubyte * 16)
                ]

            IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4D014
            
            chunk_sectors = 26
            chunk_size = chunk_sectors * sector_size
            
            out_buffer = ctypes.create_string_buffer(chunk_size)
            bytes_returned = ctypes.c_ulong(0)

            with open(output_wav_path, "wb") as wav_file:
                wav_file.write(b'RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00')
                pcm_data_size = 0

                current_sector = start_sector
                sectors_remaining = sector_count

                while sectors_remaining > 0:
                    batch_sectors = min(sectors_remaining, chunk_sectors)
                    transfer_len = batch_sectors * sector_size

                    cdb = (ctypes.c_ubyte * 16)()
                    cdb[0] = 0xBE
                    cdb[1] = 0x04
                    
                    cdb[2] = (current_sector >> 24) & 0xFF
                    cdb[3] = (current_sector >> 16) & 0xFF
                    cdb[4] = (current_sector >> 8) & 0xFF
                    cdb[5] = current_sector & 0xFF
                    
                    cdb[6] = (batch_sectors >> 16) & 0xFF
                    cdb[7] = (batch_sectors >> 8) & 0xFF
                    cdb[8] = batch_sectors & 0xFF
                    
                    cdb[9] = 0x10 

                    sptd = SCSI_PASS_THROUGH_DIRECT()
                    sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
                    sptd.CdbLength = 10
                    sptd.DataIn = 1
                    sptd.DataTransferLength = transfer_len
                    sptd.TimeOutValue = 10
                    sptd.DataBuffer = ctypes.cast(out_buffer, ctypes.c_void_p)
                    sptd.Cdb = cdb

                    sptd_size = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)

                    success = ctypes.windll.kernel32.DeviceIoControl(
                        handle,
                        IOCTL_SCSI_PASS_THROUGH_DIRECT,
                        ctypes.byref(sptd),
                        sptd_size,
                        ctypes.byref(sptd),
                        sptd_size,
                        ctypes.byref(bytes_returned),
                        None
                    )

                    if not success or sptd.DataTransferLength == 0:
                        err = ctypes.GetLastError()
                        self._log(f"WARNING: SPTI raw read failed at sector {current_sector}. WinError: {err}, ScsiStatus: {sptd.ScsiStatus}")
                        break

                    wav_file.write(out_buffer.raw[:sptd.DataTransferLength])
                    pcm_data_size += sptd.DataTransferLength
                    
                    current_sector += batch_sectors
                    sectors_remaining -= batch_sectors

                wav_file.seek(0)
                file_size = pcm_data_size + 36
                wav_file.write(b'RIFF' + struct.pack('<I', file_size) + b'WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00D\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data' + struct.pack('<I', pcm_data_size))

            self._log(f"SUCCESS: Natively ripped audio track {track['track_number']} via SPTI -> {output_wav_path}")
            return True

        except Exception as ex:
            self._log(f"EXCEPTION during native Win32 SPTI rip: {ex}")
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(handle) 

    def _rip_track_linux(self, track: dict, output_wav_path: str) -> bool:
        binary_name = "cdparanoia"
        cmd = [
            binary_name,
            "-d", self.device_path,
            str(track["track_number"]),
            output_wav_path
        ]
        self._log(f"Executing Linux extraction command: {' '.join(cmd)}")
        
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = 0x08000000  # CREATE_NO_WINDOW

        try:
            subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                creationflags=creation_flags, 
                check=True
            )
            self._log(f"SUCCESS: Linux ripped track {track['track_number']} -> {output_wav_path}")
            return True
        except Exception as e:
            self._log(f"Linux extraction error: {e}")
            return False

    def rip_full_disc(self, output_dir: str) -> list:
        normalized_out_dir = os.path.normpath(output_dir)
        self._log(f"Starting full disc rip. Target output directory: {normalized_out_dir}")
        os.makedirs(normalized_out_dir, exist_ok=True)
        
        disc_info = self.get_disc_info()
        if not disc_info:
            self._log("ABORT: Cannot rip disc because TOC could not be read.")
            return []

        ripped_files = []
        for track in disc_info["tracks"]:
            track_num = track["track_number"]
            filename = os.path.join(normalized_out_dir, f"track_{track_num:02d}.wav")
            
            success = self.rip_track(track_num, filename)
            if success:
                ripped_files.append(filename)
            else:
                self._log(f"NOTICE: Skipping or failing on track {track_num}")

        self._log(f"Full disc rip completed. Successfully extracted {len(ripped_files)} tracks.")
        return ripped_files

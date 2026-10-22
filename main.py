import sys
import os
import json
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def load_and_sanitize_config():
    """Loads config.json and automatically normalizes or repairs invalid cross-platform paths."""
    config_path = "config.json"
    default_output = os.path.join(os.path.expanduser("~"), "Music")
    
    config = {
        "ripping": {
            "output_dir": default_output,
            "audio_format": "MP3",
            "encoding_quality": "320 kbps (Best MP3)"
        },
        "discogs": {"user_token": ""},
        "acoustid": {"api_key": ""}
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    config.update(loaded)
        except Exception as e:
            print(f"Error reading config.json: {e}")

    # Auto-correction for Windows: If output_dir points to a Linux home directory, fix it
    rip_conf = config.get("ripping", {})
    out_dir = rip_conf.get("output_dir", "")
    
    if os.name == "nt" and (out_dir.startswith("/home/") or not os.path.isabs(out_dir)):
        if out_dir.startswith("/home/"):
            rip_conf["output_dir"] = default_output
            print(f"[Notice] Sanitized legacy Linux path in config to Windows path: {default_output}")
            # Save the repaired config back out
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4)
            except Exception:
                pass

    return config

def main():
    # Ensure config is sanitized before starting the UI
    load_and_sanitize_config()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

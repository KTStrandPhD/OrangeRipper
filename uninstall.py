import os
import sys

def remove_start_menu_shortcut():
    """Removes the OrangeRipper shortcut from the Windows Start Menu."""
    # Check both User and Common Start Menu paths
    start_menu_paths = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\OrangeRipper.lnk"),
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\OrangeRipper.lnk")
    ]

    removed = False
    for path in start_menu_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"[-] Removed Start Menu shortcut: {path}")
                removed = True
            except Exception as e:
                print(f"[!] Failed to remove shortcut at {path}: {e}")

    if not removed:
        print("[i] No Start Menu shortcuts found to remove.")

def main():
    print("=== OrangeRipper Windows Uninstaller ===")
    if sys.platform != "win32":
        print("[!] This uninstaller script is intended for Windows environments.")
        return

    remove_start_menu_shortcut()
    print("\n[+] Uninstallation complete! Application shortcuts have been cleaned up.")

if __name__ == "__main__":
    main()

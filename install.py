import os
import sys
import zipfile
import subprocess

def create_windows_shortcut(target_path, shortcut_path, description="", icon_path=None):
    """Creates a Windows shortcut using PowerShell."""
    ps_script = f"""
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{target_path}'
    $Shortcut.Description = '{description}'
    $Shortcut.WorkingDirectory = '{os.path.dirname(target_path)}'
    """
    if icon_path and os.path.exists(icon_path):
        ps_script += f"\n    $Shortcut.IconLocation = '{icon_path}'"
    ps_script += "\n    $Shortcut.Save()"
    
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

def create_linux_desktop_shortcut(project_root):
    """Creates and installs a Linux .desktop launcher in ~/.local/share/applications/."""
    exec_script = os.path.join(project_root, "OrangeRipper")
    icon_path = os.path.join(project_root, "assets", "app.ico")
    
    # Fallback to PNG if available
    png_icon = os.path.join(project_root, "assets", "app.png")
    if os.path.exists(png_icon):
        icon_path = png_icon

    desktop_entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=OrangeRipper
Comment=Cross-Platform CD Ripping & Encoding Utility
Exec={exec_script}
Icon={icon_path}
Terminal=false
Categories=AudioVideo;Audio;AudioVideoEditing;
Path={project_root}
"""

    apps_dir = os.path.expanduser("~/.local/share/applications")
    os.makedirs(apps_dir, exist_ok=True)
    
    desktop_file = os.path.join(apps_dir, "orangeripper.desktop")
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(desktop_entry)

    # Make executable
    os.chmod(desktop_file, 0o755)
    os.chmod(exec_script, 0o755)

    # Refresh desktop entry cache
    subprocess.run(["update-desktop-database", apps_dir], capture_output=True)
    print(f"[✓] Installed Linux desktop shortcut to: {desktop_file}")

def extract_compressed_binaries(bin_dir):
    """Checks for .zip archives in the bin directory and extracts missing executables."""
    for item in os.listdir(bin_dir):
        if item.endswith(".zip"):
            zip_path = os.path.join(bin_dir, item)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for file_info in zip_ref.infolist():
                        extracted_target = os.path.join(bin_dir, file_info.filename)
                        if not os.path.exists(extracted_target):
                            print(f"[+] Decompressing binary artifact: {file_info.filename} from {item}...")
                            zip_ref.extract(file_info, bin_dir)
                            print(f"[✓] Extracted: {extracted_target}")
                        else:
                            print(f"[✓] Executable already present: {file_info.filename}")
            except Exception as e:
                print(f"[!] Error extracting {item}: {e}")

def setup_environment():
    print("Setting up OrangeRipper environment...")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create required directories
    bin_dir = os.path.join(project_root, "bin")
    music_dir = os.path.join(project_root, "Music")
    
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(music_dir, exist_ok=True)
    print(f"[+] Verified directory: {bin_dir}")
    print(f"[+] Verified directory: {music_dir}")

    # Decompress any zipped binaries inside bin/
    extract_compressed_binaries(bin_dir)

    # Check platform-specific shortcuts & dependencies
    if sys.platform == "win32":
        print("\n--- Windows Dependency Check & Shortcut Setup ---")
        
        # Check for executable in dist folder or root
        exe_path = os.path.join(project_root, "dist", "OrangeRipper", "OrangeRipper.exe")
        if not os.path.exists(exe_path):
            exe_path = os.path.join(project_root, "OrangeRipper.exe") # fallback search

        # Verify binaries
        lame_path = os.path.join(bin_dir, "lame.exe")
        ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")

        if os.path.exists(lame_path):
            print("[✓] lame.exe ready in bin/ folder.")
        else:
            print("[!] WARNING: 'lame.exe' not found in bin/.")

        if os.path.exists(ffmpeg_path):
            print("[✓] ffmpeg.exe ready in bin/ folder.")
        else:
            print("[!] WARNING: 'ffmpeg.exe' not found in bin/.")

        # Create Shortcuts if executable exists
        if os.path.exists(exe_path):
            try:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                start_menu = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
                
                desktop_shortcut = os.path.join(desktop, "OrangeRipper.lnk")
                start_shortcut = os.path.join(start_menu, "OrangeRipper.lnk")
                icon_path = os.path.join(project_root, "assets", "app.ico")
                
                create_windows_shortcut(exe_path, desktop_shortcut, "OrangeRipper CD Audio Ripper", icon_path)
                create_windows_shortcut(exe_path, start_shortcut, "OrangeRipper CD Audio Ripper", icon_path)
                
                print("[✓] Successfully created Desktop and Start Menu shortcuts for OrangeRipper!")
            except Exception as e:
                print(f"[!] Could not create shortcuts automatically: {e}")
        else:
            print("[!] OrangeRipper.exe not found yet. Run 'package.bat' first, then re-run 'install.py' to create shortcuts.")
    else:
        print("\n--- Linux Dependency & Shortcut Setup ---")
        create_linux_desktop_shortcut(project_root)
        print("[*] Note: Ensure system CD ripping tools are installed (e.g., sudo apt install cdparanoia or icedax).")

    print("\nSetup verification complete!")

if __name__ == "__main__":
    setup_environment()

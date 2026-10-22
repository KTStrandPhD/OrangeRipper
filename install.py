import os
import sys
import subprocess

def create_shortcut(target_path, shortcut_path, description=""):
    """Creates a Windows shortcut using PowerShell."""
    ps_script = f"""
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{target_path}'
    $Shortcut.Description = '{description}'
    $Shortcut.WorkingDirectory = '{os.path.dirname(target_path)}'
    $Shortcut.Save()
    """
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

def setup_environment():
    print("Setting up OrangeRipper environment...")
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Create required directories
    bin_dir = os.path.join(project_root, "bin")
    music_dir = os.path.join(project_root, "Music")
    
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(music_dir, exist_ok=True)
    print(f"[+] Created/Verified directory: {bin_dir}")
    print(f"[+] Created/Verified directory: {music_dir}")

    # Check for platform-specific dependencies
    if sys.platform == "win32":
        print("\n--- Windows Dependency Check & Shortcut Setup ---")
        
        # Check for executable in dist folder or root
        exe_path = os.path.join(project_root, "dist", "OrangeRipper", "OrangeRipper.exe")
        if not os.path.exists(exe_path):
            exe_path = os.path.join(project_root, "OrangeRipper.exe") # fallback search

        # Check for ffmpeg.exe
        ffmpeg_path = os.path.join(bin_dir, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            print("[✓] ffmpeg.exe found in bin/ folder.")
        else:
            print("[!] WARNING: 'ffmpeg.exe' is missing from the bin/ folder!")
            print("    Please place 'ffmpeg.exe' here: ", bin_dir)

        # Create Shortcuts if executable exists
        if os.path.exists(exe_path):
            try:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                start_menu = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs")
                
                desktop_shortcut = os.path.join(desktop, "OrangeRipper.lnk")
                start_shortcut = os.path.join(start_menu, "OrangeRipper.lnk")
                
                create_shortcut(exe_path, desktop_shortcut, "OrangeRipper CD Audio Ripper")
                create_shortcut(exe_path, start_shortcut, "OrangeRipper CD Audio Ripper")
                
                print("[✓] Successfully created Desktop and Start Menu shortcuts for OrangeRipper!")
            except Exception as e:
                print(f"[!] Could not create shortcuts automatically: {e}")
        else:
            print("[!] OrangeRipper.exe not found yet. Run 'package.bat' first, then re-run 'install.py' to create shortcuts.")
    else:
        print("\n--- Linux Dependency Check ---")
        print("[*] Ensure 'cdparanoia' is installed via your package manager (e.g., sudo apt install cdparanoia).")

    print("\nSetup verification complete!")

if __name__ == "__main__":
    setup_environment()

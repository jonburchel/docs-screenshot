"""
gimp_bridge.py - GIMP Integration Module

Opens processed screenshots in GIMP for final human review.
Detects running GIMP instances and reuses them when possible.
"""

import subprocess
import os
import sys
import time

GIMP_EXE = r"C:\Program Files\GIMP 2\bin\gimp-2.10.exe"


def find_gimp() -> str:
    """Find GIMP executable path."""
    if os.path.exists(GIMP_EXE):
        return GIMP_EXE
    # Try PATH
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        candidate = os.path.join(path_dir, 'gimp-2.10.exe')
        if os.path.exists(candidate):
            return candidate
        candidate = os.path.join(path_dir, 'gimp.exe')
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("GIMP not found. Install from https://www.gimp.org/downloads/")


def is_gimp_running() -> bool:
    """Check if GIMP is already running."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'Get-Process -Name "gimp*" -ErrorAction SilentlyContinue | Select-Object -First 1 Id'],
            capture_output=True, text=True, timeout=5
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def get_gimp_pid() -> int | None:
    """Get PID of running GIMP instance."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', '(Get-Process -Name "gimp*" -ErrorAction SilentlyContinue | Select-Object -First 1).Id'],
            capture_output=True, text=True, timeout=5
        )
        pid_str = result.stdout.strip()
        return int(pid_str) if pid_str else None
    except Exception:
        return None


def open_in_gimp(image_paths: list[str], reuse_window: bool = True) -> bool:
    """
    Open one or more images in GIMP.
    
    Args:
        image_paths: List of absolute paths to image files
        reuse_window: If True, try to open in existing GIMP instance
        
    Returns:
        True if successful
    """
    gimp_exe = find_gimp()
    
    # Normalize paths
    abs_paths = [os.path.abspath(p) for p in image_paths]
    for p in abs_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Image not found: {p}")

    if reuse_window and is_gimp_running():
        return _open_in_existing_gimp(gimp_exe, abs_paths)
    else:
        return _launch_new_gimp(gimp_exe, abs_paths)


def _open_in_existing_gimp(gimp_exe: str, image_paths: list[str]) -> bool:
    """Open images in an already-running GIMP instance using Script-Fu."""
    # Build Script-Fu commands to open each file
    script_parts = []
    for path in image_paths:
        escaped_path = path.replace('\\', '\\\\')
        script_parts.append(
            f'(gimp-file-load RUN-NONINTERACTIVE "{escaped_path}" "{os.path.basename(path)}")'
        )
        script_parts.append('(gimp-display-new (car (gimp-image-list)))')

    script = ' '.join(script_parts)

    try:
        result = subprocess.run(
            [gimp_exe, '-i', '-b', script, '-b', '(gimp-quit 0)'],
            capture_output=True, text=True, timeout=30
        )
        # If batch mode fails (common with existing instance), fall back to simple open
        if result.returncode != 0:
            return _launch_new_gimp(gimp_exe, image_paths)
        return True
    except subprocess.TimeoutExpired:
        # GIMP batch mode can hang; fall back
        return _launch_new_gimp(gimp_exe, image_paths)
    except Exception as e:
        print(f"Warning: Script-Fu approach failed ({e}), launching new GIMP", file=sys.stderr)
        return _launch_new_gimp(gimp_exe, image_paths)


def _launch_new_gimp(gimp_exe: str, image_paths: list[str]) -> bool:
    """Launch a new GIMP instance with images."""
    cmd = [gimp_exe] + image_paths
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        # Give GIMP a moment to start
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error launching GIMP: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python gimp_bridge.py <image_path> [image_path2 ...]")
        sys.exit(1)
    
    paths = sys.argv[1:]
    running = is_gimp_running()
    print(f"GIMP running: {running}")
    print(f"Opening {len(paths)} image(s)...")
    success = open_in_gimp(paths, reuse_window=True)
    print(f"{'Success' if success else 'Failed'}")

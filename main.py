import os
import sys
import time
import re
import threading
from datetime import datetime

# Logging to a file to track hidden errors, and fix standard outputs for PyInstaller
LOG_FILE = os.path.join(os.environ.get('TEMP', 'C:\\'), 'amd_clip_sorter.log')

def log_debug(msg):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass

class DummyOutput:
    def write(self, x): log_debug(x.strip() if x.strip() else x)
    def flush(self): pass
    def isatty(self): return False

if sys.stdout is None:
    sys.stdout = DummyOutput()
if sys.stderr is None:
    sys.stderr = DummyOutput()
else:
    sys.stdout = DummyOutput()
    sys.stderr = DummyOutput()

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- SETTINGS ---
# Automatically finds the current user's Videos folder (no personal name hardcoded)
BASE_DIR = os.path.join(os.environ.get('USERPROFILE', 'C:\\'), 'Videos', 'Radeon ReLive')
# ---------------------

def get_optimal_filename(filepath):
    """
    Creates a clean filename for the clip.
    Format: YYYY-MM-DD_HH-MM-SS - GameName.mp4
    This ensures that Windows automatically sorts the clips chronologically.
    """
    dir_name = os.path.dirname(filepath)
    game_name = os.path.basename(dir_name)

    # If the file is directly in the main folder
    if dir_name.lower().rstrip('\\') == BASE_DIR.lower().rstrip('\\'):
        game_name = "Unknown Game"

    # Get file creation date
    ctime = os.path.getctime(filepath)
    dt = datetime.fromtimestamp(ctime)
    date_str = dt.strftime("%Y-%m-%d_%H-%M-%S")

    ext = os.path.splitext(filepath)[1].lower()
    new_name = f"{date_str} - {game_name}{ext}"
    return os.path.join(dir_name, new_name)

def rename_file_safe(filepath):
    """
    Renames the file once it is no longer locked by AMD (after recording finishes).
    """
    if not filepath.lower().endswith('.mp4'):
        return

    # Skip temp files created by AMD (like out.mp4 or files ending in .tmp)
    if filename.lower() == 'out.mp4' or filename.lower().startswith('~') or '.tmp' in filename.lower():
        return

    # Check if the file already has the correct format (e.g. 2023-10-25_14-30-00 - Game.mp4)
    if re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2} - ", filename):
        return

    # Wait an extra few seconds to give AMD enough time to move the file after writing!
    time.sleep(3)

    new_filepath = get_optimal_filename(filepath)

    # If the new calculated path is the same as the old one or already exists
    if filepath == new_filepath or os.path.exists(new_filepath):
        return

    # Try to rename the file. If AMD is still recording, it throws a PermissionError.
    # We keep trying for about 30 minutes.
    max_retries = 1800
    for _ in range(max_retries):
        try:
            os.rename(filepath, new_filepath)
            log_debug(f"Successfully renamed:\n  Old: {filename}\n  New: {os.path.basename(new_filepath)}\n")
            break
        except PermissionError:
            time.sleep(1) # wait 1 second and retry
        except FileNotFoundError:
            # File might have been deleted or moved
            break
        except Exception as e:
            log_debug(f"Error during renaming: {e}")
            break

def process_existing_files():
    """
    Iterates through all subfolders and renames already existing .mp4 files.
    """
    log_debug("Searching for existing clips...")
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.lower().endswith('.mp4'):
                full_path = os.path.join(root, file)
                # Since existing files are no longer being recorded, we can rename them
                rename_file_safe(full_path)
    log_debug("Finished processing existing clips.\n")

class ClipHandler(FileSystemEventHandler):
    """
    This handler is called when Windows reports a new file created in the ReLive folders.
    """
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.mp4'):
            log_debug(f"New recording detected: {os.path.basename(event.src_path)}")
            # Start in a new thread so the event listener isn't blocked
            # while we wait for AMD to finish the recording.
            threading.Thread(target=rename_file_safe, args=(event.src_path,)).start()

def create_tray_icon_image():
    """Creates a simple red icon for the System Tray to avoid external .ico files."""
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    draw = ImageDraw.Draw(image)
    # Red record button
    draw.ellipse((16, 16, 48, 48), fill=(255, 50, 50))
    return image

def quit_action(icon, item):
    """Called when 'Quit' is clicked in the System Tray."""
    log_debug("Exiting program...")
    icon.stop()
    os._exit(0)

def main():
    if not os.path.exists(BASE_DIR):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"The folder {BASE_DIR} could not be found.\nPlease check the path.", "AMD Sorter Error", 0)
        return

    # 1. Rename existing files in a background thread so the icon appears IMMEDIATELY!
    threading.Thread(target=process_existing_files, daemon=True).start()

    # 2. Watch folder for files recorded in the future
    event_handler = ClipHandler()
    observer = Observer()
    # recursive=True also watches all game subfolders
    observer.schedule(event_handler, BASE_DIR, recursive=True)
    observer.start()

    log_debug(f"Watching folder: {BASE_DIR} for new clips...")
    log_debug("Program is now running in the background (System Tray).")

    # 3. Start System Tray Icon
    menu = pystray.Menu(item('Quit', quit_action))
    icon = pystray.Icon("AMD Clip Sorter", create_tray_icon_image(), "AMD Clip Sorter", menu)
    
    # Runs infinitely until user clicks Quit
    icon.run()

if __name__ == "__main__":
    main()
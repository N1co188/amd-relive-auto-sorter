import os
import sys
import time
import re
import threading
import json
from datetime import datetime

# GUI Imports
import customtkinter as ctk
from tkinter import messagebox

# Logging
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
BASE_DIR = os.path.join(os.environ.get('USERPROFILE', 'C:\\'), 'Videos', 'Radeon ReLive')
CONFIG_DIR = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'AMD_Clip_Sorter')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
# ---------------------

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            log_debug(f"Error loading config: {e}")
    return {"format": "1"}

def save_config(config_data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
    except Exception as e:
        log_debug(f"Error saving config: {e}")

def get_optimal_filename(filepath):
    """
    Creates a clean filename based on the user's selected format in the GUI.
    """
    dir_name = os.path.dirname(filepath)
    folder_name = os.path.basename(dir_name)
    
    # Identify the base Game folder
    # If the file is already inside a Date folder (YYYY-MM-DD), the game folder is one level up
    if re.match(r"^\d{4}-\d{2}-\d{2}$", folder_name):
        game_dir = os.path.dirname(dir_name)
        game_name = os.path.basename(game_dir)
    else:
        game_dir = dir_name
        game_name = folder_name

    # If the game folder corresponds to the main ReLive folder, we don't have a game name
    if game_dir.lower().rstrip('\\') == BASE_DIR.lower().rstrip('\\'):
        game_name = "Unknown"
        game_dir = os.path.join(BASE_DIR, "Unknown")

    # os.path.getmtime is slightly safer for media files in case they were copied
    mtime = os.path.getmtime(filepath)
    dt = datetime.fromtimestamp(mtime)
    
    # Load user preference
    config = load_config()
    fmt = config.get("format", "1")
    sort_by_date = config.get("sort_by_date", False)
    ext = os.path.splitext(filepath)[1].lower()

    if fmt == "1":
        # Format 1 (Default): YYYY-MM-DD_HH-MM-SS - GameName.mp4
        new_name = f"{dt.strftime('%Y-%m-%d_%H-%M-%S')} - {game_name}{ext}"
    elif fmt == "2":
        # Format 2: GameName - YYYY-MM-DD_HH-MM-SS.mp4
        new_name = f"{game_name} - {dt.strftime('%Y-%m-%d_%H-%M-%S')}{ext}"
    elif fmt == "3":
        # Format 3: YYYY-MM-DD - GameName - HH-MM-SS.mp4
        new_name = f"{dt.strftime('%Y-%m-%d')} - {game_name} - {dt.strftime('%H-%M-%S')}{ext}"
    elif fmt == "4":
        # Format 4: GameName_YYYYMMDD_HHMMSS.mp4 (Very compact)
        new_name = f"{game_name}_{dt.strftime('%Y%m%d_%H%M%S')}{ext}"
    else:
        # Fallback
        new_name = f"{dt.strftime('%Y-%m-%d_%H-%M-%S')} - {game_name}{ext}"

    # Determine saving location: either in the Game folder, or in a Date folder inside the Game folder
    if sort_by_date:
        date_folder = dt.strftime('%Y-%m-%d')
        target_dir = os.path.join(game_dir, date_folder)
    else:
        target_dir = game_dir

    return os.path.join(target_dir, new_name)

def rename_file_safe(filepath):
    """
    Renames the file once it is no longer locked by AMD.
    Returns True if renamed, False otherwise.
    """
    if not filepath.lower().endswith('.mp4'):
        return False

    filename = os.path.basename(filepath)

    # Skip temp files created by AMD
    if filename.lower() == 'out.mp4' or filename.lower().startswith('~') or '.tmp' in filename.lower():
        return False

    new_filepath = get_optimal_filename(filepath)

    # Exit if already perfectly named according to the currently selected format
    if filepath == new_filepath or os.path.exists(new_filepath):
        return False

    # Create target directory if it doesn't exist
    target_dir = os.path.dirname(new_filepath)
    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir)
        except Exception as e:
            log_debug(f"Could not create folder {target_dir}: {e}")

    # Give AMD enough time to move the file out of temp status if it's new
    # (If the original file is less than 10 seconds old, we sleep briefly)
    if time.time() - os.path.getctime(filepath) < 10:
        time.sleep(3)

    max_retries = 1800
    for _ in range(max_retries):
        try:
            os.rename(filepath, new_filepath)
            log_debug(f"Successfully renamed/moved:\n  Old: {filepath}\n  New: {new_filepath}\n")
            
            # Clean up empty date folders if we moved the file out
            old_dir = os.path.dirname(filepath)
            if re.match(r"^\d{4}-\d{2}-\d{2}$", os.path.basename(old_dir)):
                if not os.listdir(old_dir):
                    try:
                        os.rmdir(old_dir)
                    except:
                        pass
            
            return True
        except PermissionError:
            time.sleep(1)
        except FileNotFoundError:
            break
        except Exception as e:
            log_debug(f"Error during renaming: {e}")
            break
    return False

def process_existing_files(show_done_message=False):
    """
    Iterates through all subfolders to check for files.
    """
    log_debug("Searching for existing clips to update to actual format...")
    renamed_count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if file.lower().endswith('.mp4'):
                full_path = os.path.join(root, file)
                if rename_file_safe(full_path):
                    renamed_count += 1
    
    log_debug(f"Finished processing existing clips. Renamed {renamed_count} files.\n")
    
    if show_done_message and renamed_count > 0:
        # Create a tiny invisible root just to show the messagebox successfully
        msg_root = ctk.CTk()
        msg_root.withdraw()
        msg_root.attributes('-topmost', True)
        messagebox.showinfo("Success", f"All existing clips have been renamed/moved!\n\n({renamed_count} clips updated)", parent=msg_root)
        msg_root.destroy()


class ClipHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.mp4'):
            log_debug(f"New recording detected: {os.path.basename(event.src_path)}")
            threading.Thread(target=rename_file_safe, args=(event.src_path,)).start()

def create_tray_icon_image():
    """Erstellt ein modernes Tray-Icon (Dunkler Hintergrund mit AMD-rotem Akzent)."""
    # Create with alpha channel for rounded corners if supported by OS, else solid
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Dark base with red outline
    draw.rounded_rectangle((2, 2, 61, 61), radius=12, fill=(25, 25, 25, 255), outline=(229, 9, 20, 255), width=3)
    
    # Inner red circle
    draw.ellipse((16, 16, 48, 48), fill=(229, 9, 20, 255))
    
    # White Play/Camera Triangle in the middle
    draw.polygon([(26, 22), (26, 42), (43, 32)], fill=(255, 255, 255, 255))
    
    return image

# --- GUI CODE (CustomTkinter) ---
def open_settings_window(icon, item):
    """Spawns the GUI in a separate thread so it doesn't block the Tray Icon."""
    threading.Thread(target=_run_ctk_app, daemon=True).start()

def _run_ctk_app():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title(" AMD Clip Sorter Settings")
    
    window_width = 620
    window_height = 480
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
    
    root.resizable(False, False)
    
    # Try to bring window to front
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)
    
    # Very modern header - Transparent, minimalistic, bold
    header_frame = ctk.CTkFrame(root, fg_color="transparent")
    header_frame.pack(fill="x", padx=40, pady=(30, 10))
    
    ctk.CTkLabel(header_frame, text="AMD Clip Sorter", 
                 font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), 
                 text_color="white").pack(anchor="w")
    
    ctk.CTkLabel(header_frame, text="Automate and organize your ReLive recordings.", 
                 font=ctk.CTkFont(family="Segoe UI", size=14), 
                 text_color="gray60").pack(anchor="w", pady=(0, 5))
    
    # Clean Red Accent Line
    accent_line = ctk.CTkFrame(header_frame, fg_color="#e50914", height=2, corner_radius=0)
    accent_line.pack(fill="x", pady=(5, 0))
    
    # Settings Card
    content_frame = ctk.CTkFrame(root, fg_color="#1a1a1a", corner_radius=12, border_width=1, border_color="#2b2b2b")
    content_frame.pack(fill="both", expand=True, padx=40, pady=(15, 30))
    
    # Select Format Field
    format_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    format_frame.pack(fill="x", padx=20, pady=(25, 10))
    
    ctk.CTkLabel(format_frame, text="Filename Layout", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(format_frame, text="Choose how the final clips should be named.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="gray55").pack(anchor="w", pady=(0, 8))
    
    formats = {
        "1": "YYYY-MM-DD_HH-MM-SS - GameName.mp4 (Default)",
        "2": "GameName - YYYY-MM-DD_HH-MM-SS.mp4",
        "3": "YYYY-MM-DD - GameName - HH-MM-SS.mp4",
        "4": "GameName_YYYYMMDD_HHMMSS.mp4"
    }
    
    current_config = load_config()
    current_fmt = current_config.get("format", "1")
    current_sort_by_date = current_config.get("sort_by_date", False)
    
    format_var = ctk.StringVar(value=formats.get(current_fmt, formats["1"]))
    
    cb = ctk.CTkOptionMenu(format_frame, variable=format_var, values=list(formats.values()), 
                           height=40, font=ctk.CTkFont(family="Segoe UI", size=13),
                           fg_color="#282828", button_color="#333", button_hover_color="#e50914",
                           dropdown_fg_color="#282828", dropdown_hover_color="#333",
                           dropdown_font=ctk.CTkFont(family="Segoe UI", size=13), corner_radius=8)
    cb.pack(fill="x")
    
    # Fix Default OptionMenu logic: OptionMenu doesn't close on 2nd click because of Tkinter event looping
    original_clicked = cb._clicked
    cb._last_closed_time = 0
    def _patched_clicked(*args, **kwargs):
        import time
        # If it was closed within the last 0.25 seconds, don't reopen it instantly
        if time.time() - cb._last_closed_time > 0.25:
            original_clicked(*args, **kwargs)
            # When the blocking menu closes, record the time
            cb._last_closed_time = time.time()
    cb._clicked = _patched_clicked
    
    # Toggle Switch Field
    switch_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    switch_frame.pack(fill="x", padx=20, pady=(15, 20))
    
    sort_var = ctk.BooleanVar(value=current_sort_by_date)
    switch = ctk.CTkSwitch(switch_frame, text="Sort into Daily Folders (YYYY-MM-DD)", 
                           variable=sort_var, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                           progress_color="#e50914", button_color="white", button_hover_color="#ebebeb")
    switch.pack(anchor="w")
    ctk.CTkLabel(switch_frame, text="Automatically moves clips into subfolders based on creation date.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="gray55").pack(anchor="w", padx=(45, 0), pady=(0, 5))
    
    # Bottom Bar inside Card
    bottom_frame = ctk.CTkFrame(content_frame, fg_color="transparent", height=60)
    bottom_frame.pack(fill="x", side="bottom", padx=20, pady=20)
    
    def save():
        selected_text = format_var.get()
        selected_key = "1"
        for k, v in formats.items():
            if v == selected_text:
                selected_key = k
                break
        
        save_config({
            "format": selected_key,
            "sort_by_date": sort_var.get()
        })
        root.destroy()
        
        # Apply immediately to existing clips and show success popup!
        threading.Thread(target=process_existing_files, args=(True,), daemon=True).start()
        
    # Modern Save Button Action
    btn = ctk.CTkButton(bottom_frame, text="Save & Apply Changes", command=save, 
                        height=42, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                        fg_color="#e50914", hover_color="#b80710", corner_radius=8)
    btn.pack(side="right", ipadx=10)
    
    root.mainloop()
# --------------------------

def quit_action(icon, item):
    log_debug("Exiting program...")
    icon.stop()
    os._exit(0)

def main():
    if not os.path.exists(BASE_DIR):
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"The folder {BASE_DIR} could not be found.\nPlease check the path.", "AMD Sorter Error", 0)
        return

    # Check background files
    threading.Thread(target=process_existing_files, daemon=True).start()

    # Hardware watcher
    event_handler = ClipHandler()
    observer = Observer()
    observer.schedule(event_handler, BASE_DIR, recursive=True)
    observer.start()

    log_debug(f"Watching folder: {BASE_DIR} for new clips...")

    # Build Tray Menu (Added "Settings" button!)
    menu = pystray.Menu(
        item('Settings', open_settings_window),
        item('Quit', quit_action)
    )
    icon = pystray.Icon("AMD Clip Sorter", create_tray_icon_image(), "AMD Clip Sorter", menu)
    
    icon.run()

if __name__ == "__main__":
    main()
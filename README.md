# AMD Radeon ReLive Clip Sorter & Manager

An automated background tool that smartly renames, sorts, and organizes game clips recorded with AMD Radeon ReLive.

## Features
* **Modern GUI Settings:** A sleek, dark-mode settings panel (built with CustomTkinter) configurable directly from the system tray.
* **Automatic Renaming:** Chooses from multiple naming formats (e.g., `YYYY-MM-DD_HH-MM-SS - GameName.mp4`, `GameName_YYYYMMDD_HHMMSS.mp4`, etc.).
* **Daily Subfolders:** Optional feature to automatically move clips into `YYYY-MM-DD` daily subfolders.
* **Smart Detection:** Automatically locates your `Videos\Radeon ReLive` directory on Windows and ignores temporary AMD `.tmp` or `out.mp4` render files.
* **Background Process:** Sits quietly in the system tray with a custom matching icon.
* **Real-Time Monitoring:** Watches for new clips and safely renames them the exact moment AMD finishes writing the file.

## Requirements
* Windows OS
* Python 3.8+ (if running from source)
* Required Python modules (see `requirements.txt`)

## Building the Executable
You can easily build a standalone Windows `.exe` to run the tool without keeping a console window open, or having Python installed:
1. Run `build.bat` (This installs dependencies via `requirements.txt` and uses `PyInstaller` to create the app).
2. Grab the generated `.exe` from the newly created `dist/` folder.

## Setup Autostart
A helper script (`setup_autostart.bat`) is included to easily add the generated executable to your Windows Startup folder. This makes the program start silently in the system tray every time you boot your PC. 

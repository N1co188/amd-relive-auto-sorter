# AMD Radeon ReLive Clip Sorter

An automated background tool that smartly renames and chronologically sorts game clips recorded with AMD Radeon ReLive.

## Features
* **Automatic Sorting:** Renames `.mp4` clips to the format `YYYY-MM-DD_HH-MM-SS - GameName.mp4`.
* **Zero Configuration:** Automatically locates the user's specific `Videos\Radeon ReLive` directory on Windows.
* **Background Process:** Sits quietly in the system tray.
* **Real-Time Monitoring:** Watches for new clips and safely renames them the exact moment AMD finishes writing the file.

## Requirements
* Windows OS
* Python 3.8+ (if running from source)
* Required Python libraries: `watchdog`, `pystray`, `Pillow`

## Building the Executable
You can easily build a standalone Windows `.exe` to run the tool without keeping a console window open:
1. Run `build.bat` (This installs dependencies via `requirements.txt` and uses `PyInstaller` to create the app).
2. Grab the generated `.exe` from the newly created `dist/` folder.

## Setup Autostart
A helper script (`setup_autostart.bat`) is included to easily add the generated executable to your Windows Startup folder, allowing it to start minimized in the system tray every time you boot your PC. 

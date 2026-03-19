@echo off
echo Installing required libraries...
pip install -r requirements.txt

echo.
echo Building the executable...
pyinstaller --noconsole --onefile --name "AMD_Clip_Sorter" main.py

echo.
echo ========================================================
echo DONE! 
echo Your executable is now ready in the "dist" folder.
echo You can double click "AMD_Clip_Sorter.exe" to run it.
echo ========================================================
pause
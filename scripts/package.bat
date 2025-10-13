@echo off
echo Building writetofillet binary for this platform...
python -m pip install --upgrade pip
python -m pip install pyinstaller -e .
pyinstaller --onefile -n writetofillet src\writetofillet\cli.py
echo Built binaries are in the dist folder.


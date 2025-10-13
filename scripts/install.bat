@echo off
setlocal enabledelayedexpansion
set REPO_NAME=writetofillet
echo Installing %REPO_NAME%...

where scoop >nul 2>&1
if %ERRORLEVEL%==0 (
  echo Detected Scoop. Installing via bucket manifest...
  rem Ensure bucket is added (assumes this repo as a bucket)
  scoop bucket add supermarsx https://github.com/supermarsx/writetofillet >nul 2>&1
  scoop install %REPO_NAME%
  goto :eof
)

where pipx >nul 2>&1
if %ERRORLEVEL%==0 (
  echo Detected pipx. Installing from current repo...
  pipx install .
  goto :eof
)

echo Falling back to pip editable install from current repo...
python -m pip install -e .
echo Installed %REPO_NAME%. Use 'writetofillet --help' to get started.

endlocal


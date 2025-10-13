@echo off
echo Updating writetofillet...
where scoop >nul 2>&1
if %ERRORLEVEL%==0 (
  scoop update
  scoop update writetofillet || scoop install writetofillet
  goto :eof
)
where brew >nul 2>&1
if %ERRORLEVEL%==0 (
  brew upgrade writetofillet || brew install writetofillet
  goto :eof
)
where pipx >nul 2>&1
if %ERRORLEVEL%==0 (
  pipx upgrade writetofillet
)
echo Checking for latest rolling release:
writetofillet --check-updates


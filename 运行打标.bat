@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
python lm_clipboard_tag.py --print-output %*
set rc=%ERRORLEVEL%
if not "%rc%"=="0" (
  echo Error: check terminal output or logs directory
  pause
  exit /b %rc%
)
pause
exit /b 0
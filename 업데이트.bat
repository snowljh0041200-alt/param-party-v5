@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v17.3 시간 표시 수정 =====
git add .
git commit -m "v17.3 time display fix"
git push
pause

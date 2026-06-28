@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v18.1 사냥 참여 버그 수정 =====
git add .
git commit -m "v18.1 hunting join fix"
git push
pause

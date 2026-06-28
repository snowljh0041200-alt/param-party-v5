@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v18.2 사냥 참여 버튼 수정 =====
git add .
git commit -m "v18.2 hunting button fix"
git push
pause

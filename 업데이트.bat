@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v17.1 폼 강제 수정 =====
echo.
git add .
git commit -m "v17.1 force form fix"
git push
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v20.0 정식 클린 프로젝트 =====
git add .
git commit -m "v20.0 official clean project"
git push
pause

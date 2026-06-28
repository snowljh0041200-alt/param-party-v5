@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v18.0 안정화 리빌드 =====
git add .
git commit -m "v18.0 stable rebuild"
git push
pause

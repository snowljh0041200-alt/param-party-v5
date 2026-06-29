@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v27.1 toast test settings"
git push
pause

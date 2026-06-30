@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v42.0 final notification settings"
git push
pause

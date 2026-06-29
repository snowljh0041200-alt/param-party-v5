@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.5 post grid final fix"
git push
pause

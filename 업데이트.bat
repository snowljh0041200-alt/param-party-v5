@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.6 voice mute checkbox final"
git push
pause

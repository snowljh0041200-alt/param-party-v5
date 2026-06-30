@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.4 voice mute respect fix"
git push
pause

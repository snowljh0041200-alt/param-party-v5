@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.5 final boss voice mute spawn fix"
git push
pause

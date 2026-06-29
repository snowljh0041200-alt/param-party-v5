@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v36.2 notice and alert fix"
git push
pause

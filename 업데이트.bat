@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v29.0 promotion ui final"
git push
pause

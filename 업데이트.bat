@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v30.0 final layout"
git push
pause

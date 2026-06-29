@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.1 layout recovery fixed"
git push
pause

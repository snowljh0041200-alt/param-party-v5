@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.6 fixed width final"
git push
pause

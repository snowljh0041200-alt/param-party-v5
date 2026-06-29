@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v28.1 chrome notify cancel fix"
git push
pause

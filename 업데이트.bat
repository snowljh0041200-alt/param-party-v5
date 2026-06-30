@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.6 unified job icons"
git push
pause

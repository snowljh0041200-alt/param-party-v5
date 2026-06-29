@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v23.0 slim premium ui"
git push
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v21.4 ui cleanup"
git push
pause

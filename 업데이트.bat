@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.2 voice settings unified"
git push
pause

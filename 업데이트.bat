@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v28.3 settings choose notify fix"
git push
pause

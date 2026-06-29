@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v22.5 alarm settings premium ui"
git push
pause

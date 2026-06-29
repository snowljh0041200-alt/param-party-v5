@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v34.0 real structure layout"
git push
pause

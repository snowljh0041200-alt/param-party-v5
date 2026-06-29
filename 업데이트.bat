@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v27.0 stable rebuild"
git push
pause

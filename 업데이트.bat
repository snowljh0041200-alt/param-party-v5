@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.4 true two column recover"
git push
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v22.0 practical UI"
git push
pause

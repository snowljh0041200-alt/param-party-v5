@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v25.6 cancel and external remove"
git push
pause

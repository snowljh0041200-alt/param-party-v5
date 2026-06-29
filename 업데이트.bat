@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v26.23 toast only status fix"
git push
pause

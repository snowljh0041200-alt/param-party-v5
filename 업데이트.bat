@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.3 voice seconds countdown fix"
git push
pause

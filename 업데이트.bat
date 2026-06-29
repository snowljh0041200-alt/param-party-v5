@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v37.3 add char fix"
git push
pause

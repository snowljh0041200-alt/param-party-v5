@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.2 force four grid width"
git push
pause

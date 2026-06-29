@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v32.0 flex inlineblock layout"
git push
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.5 hunt place select options fix"
git push
pause

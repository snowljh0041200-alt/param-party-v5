@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v36.8 character management fix"
git push
pause

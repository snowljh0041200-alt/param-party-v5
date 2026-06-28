@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v5.1 design and channel fix"
git push
pause

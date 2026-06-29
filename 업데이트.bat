@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v36.5 online header chat expand"
git push
pause

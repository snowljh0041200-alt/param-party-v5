@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v39.0 design project remaster"
git push
pause

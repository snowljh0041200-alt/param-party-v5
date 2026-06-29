@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v38.0 design remaster css only"
git push
pause

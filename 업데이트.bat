@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v28.7 chrome alerts split fix"
git push
pause

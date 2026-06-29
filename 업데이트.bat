@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.2 restore v40 jusul fire only"
git push
pause

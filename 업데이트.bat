@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v39.2 unique dark gold theme"
git push
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v28.4 toast dedupe fix"
git push
pause

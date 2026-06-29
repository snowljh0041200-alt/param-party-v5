@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v25.1 gate hotfix"
git push
pause

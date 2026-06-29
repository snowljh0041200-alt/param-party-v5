@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v35.0 real tindex layout fix"
git push
pause

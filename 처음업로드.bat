@echo off
chcp 65001 >nul
cd /d "%~dp0"
git init
git branch -M main
git add .
git commit -m "v5 first upload"
git remote add origin https://github.com/snowljh0041200-alt/param-party-v5.git
git push -u origin main
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
git status
git add app.py requirements.txt Procfile render.yaml .gitignore 업데이트.bat 사용법.txt
git commit -m "v6.1 confirmed app update"
git push
pause

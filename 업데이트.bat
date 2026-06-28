@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v17.2 생성화면 빈화면 수정 =====
git add .
git commit -m "v17.2 new page fix"
git push
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.13 알림 기능 수정 =====
echo.
git add .
git commit -m "v13.13 notification fix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v10.2 채팅관리 업데이트 =====
echo.
git add .
git commit -m "v10.2 chat manage"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

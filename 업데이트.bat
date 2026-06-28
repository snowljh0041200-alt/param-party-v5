@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.14 회원 삭제 기능 추가 =====
echo.
git add .
git commit -m "v13.14 user delete"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

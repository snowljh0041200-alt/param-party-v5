@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.8 회원권한 관리자 시스템 업데이트 =====
echo.
git add .
git commit -m "v13.8 role based admin"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

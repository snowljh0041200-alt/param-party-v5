@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.9 관리자 권한 반영 안내 수정 =====
echo.
git add .
git commit -m "v13.9 admin role feedback"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

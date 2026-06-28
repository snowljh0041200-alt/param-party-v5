@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.11 관리자 권한 최종 수정 =====
echo.
git add .
git commit -m "v13.11 admin final fix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

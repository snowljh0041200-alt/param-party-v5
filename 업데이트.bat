@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.10 관리자 초기승인 막힘 수정 =====
echo.
git add .
git commit -m "v13.10 admin bootstrap fix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

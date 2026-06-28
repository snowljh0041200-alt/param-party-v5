@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.1 수정/삭제/파밍수정 버튼 핫픽스 =====
echo.
git add .
git commit -m "v13.1 owner buttons hotfix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

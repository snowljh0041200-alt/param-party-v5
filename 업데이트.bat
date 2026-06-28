@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v12.1 파밍/외부인/수정 버튼 핫픽스 =====
echo.
git add .
git commit -m "v12.1 farming hotfix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.3 600퀘 인원제한/모집완료 업데이트 =====
echo.
git add .
git commit -m "v13.3 quest limit complete"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

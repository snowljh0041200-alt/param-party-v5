@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.15 마감 글 표시 개선 =====
echo.
git add .
git commit -m "v13.15 closed post style"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause

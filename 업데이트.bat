@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== 바클 파티모집 v7 FINAL 업데이트 =====
echo.
git status
echo.
git add app.py requirements.txt Procfile render.yaml .gitignore 업데이트.bat 사용법.txt
git commit -m "v7 final polish"
git push
echo.
echo ===== 완료: GitHub 업로드 후 Render 자동배포를 기다려주세요 =====
pause

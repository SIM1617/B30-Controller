@echo off
setlocal
chcp 65001 >nul
echo ==========================================
echo   B30-Controller - Push to GitHub
echo   User: SIM1617  Repo: B30-Controller
echo ==========================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
)
git --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git not found. Install from https://git-scm.com/download/win
  pause
  exit /b 1
)

cd /d "%~dp0"

if not exist ".git" (
  echo [1/5] git init ...
  git init
  git branch -M main
) else (
  echo [1/5] git repo already exists.
)

echo [2/5] git config ...
git config user.name "SIM1617"
git config user.email "SIM1617@users.noreply.github.com"
git config init.defaultBranch main

echo [3/5] git add ...
git add .

echo [4/5] git commit ...
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "initial: B30 Controller with license + GitHub Pages"
) else (
  echo   nothing new to commit, skipping.
)

echo [5/5] git push ...
echo.
echo   You need a GitHub Personal Access Token (PAT).
echo   Create one at: https://github.com/settings/tokens/new
echo   - Note: B30 push
echo   - Expiration: 90 days
echo   - Check: repo (all)
echo   - Generate token and copy it (ghp_xxxx...)
echo.
set /p GH_TOKEN=Paste your token (ghp_...): 

if "%GH_TOKEN%"=="" (
  echo [ERROR] No token entered.
  echo   Create token at https://github.com/settings/tokens/new
  pause
  exit /b 1
)

git remote remove origin 2>nul
git remote add origin https://SIM1617:%GH_TOKEN%@github.com/SIM1617/B30-Controller.git

echo.
echo Pushing to https://github.com/SIM1617/B30-Controller.git ...
git push -u origin main

if errorlevel 1 (
  echo.
  echo [FAILED] Push failed. Possible reasons:
  echo   - Token wrong or expired
  echo   - Repo B30-Controller not created yet (create at https://github.com/new)
  echo   - No internet
  pause
  exit /b 1
)

echo.
echo ==========================================
echo   SUCCESS! Pushed to GitHub.
echo   Next: enable Pages at
echo   https://github.com/SIM1617/B30-Controller/settings/pages
echo   Source: main / docs  - then Save
echo ==========================================
pause

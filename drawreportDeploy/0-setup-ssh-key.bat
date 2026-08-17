@echo off
REM ONE-TIME SETUP: install your SSH key on the DrawReport server so release.bat can
REM deploy without a password. You will be asked for the server's ROOT PASSWORD once.
REM
REM You only need this on a NEW machine. If release.bat already deploys without asking
REM for a password, the key is installed and you can ignore this file.
setlocal
echo ================================================================
echo  Installing your SSH key on root@5.78.181.152 (DrawReport).
echo  You will be asked for the server's ROOT PASSWORD once.
echo ================================================================
echo.

if not exist "%USERPROFILE%\.ssh\id_ed25519.pub" (
  echo ERROR: no key found at %USERPROFILE%\.ssh\id_ed25519.pub
  echo Create one first, in a terminal:  ssh-keygen -t ed25519
  pause
  exit /b 1
)

set /p PUBKEY=<"%USERPROFILE%\.ssh\id_ed25519.pub"

ssh -o StrictHostKeyChecking=accept-new root@5.78.181.152 "umask 077; mkdir -p ~/.ssh; grep -qxF '%PUBKEY%' ~/.ssh/authorized_keys 2>/dev/null || echo '%PUBKEY%' >> ~/.ssh/authorized_keys; echo KEY_INSTALLED_OK"

echo.
echo If you saw KEY_INSTALLED_OK above, you are done.
echo Test it:  release.bat --deploy-only   (it should NOT ask for a password)
pause

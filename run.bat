@echo off
set ROOT="d:\NewX\OS\Try 5"

echo ============================================
echo  Kill leftover QEMU processes...
echo ============================================
taskkill /F /IM qemu-system-i386.exe >nul 2>&1
taskkill /F /IM qemu-system-x86_64.exe >nul 2>&1

echo.
echo ============================================
echo  Waiting for file handles to release...
echo ============================================
timeout /t 2 /nobreak >nul

python %ROOT%\build.py
if %errorlevel% neq 0 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo ============================================
echo Starting QEMU...
echo ============================================

set RETRY=0
:qemu_start
"D:\NewX\OS\Try 5\Program\QEMU\qemu-system-i386.exe" -drive format=raw,file=build\os-image.img
if %errorlevel% equ 0 goto end

set /a RETRY+=1
if %RETRY% geq 3 (
    echo.
    echo QEMU failed after %RETRY% attempts.
    pause
    exit /b 1
)

echo.
echo QEMU failed (attempt %RETRY%/3), retrying in 3s...
taskkill /F /IM qemu-system-i386.exe >nul 2>&1
timeout /t 3 /nobreak >nul
goto qemu_start

:end
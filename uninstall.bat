@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title gpt-instruct opencode Kaldirma

set "DEST=%USERPROFILE%\.config\opencode\skills\gpt-instruct"
set "OPENCODE_HOME=%USERPROFILE%\.config\opencode"

echo.
echo ============================================================
echo   gpt-instruct  -- Kaldirma / Reset
echo ============================================================
echo   Hedef: %DEST%
echo.

:: Python bul
set "PY="
for %%P in (python python3 py) do (
    where %%P >nul 2>&1
    if !errorlevel! equ 0 (
        %%P --version >nul 2>&1
        if !errorlevel! equ 0 set "PY=%%P" & goto :foundpy
    )
)
:foundpy
if "%PY%"=="" set "PY=python"

if not exist "%DEST%" (
    echo [!] Skill zaten kurulu degil: %DEST%
    echo     Yine de opencode.jsonc / Codex config temizlenebilir.
) else (
    echo [*] Skill bulundu: %DEST%
)

echo.
echo   1. Sadece opencode global instructions temizle
echo   2. Sadece Codex temizle
echo   3. Hepsi - opencode + Codex + skill klasorunu sil - ONERILEN
echo   4. Iptal
set /p CHOICE="Secim [1/2/3/4] (varsayilan 3): "
if "%CHOICE%"=="" set "CHOICE=3"
if "%CHOICE%"=="4" (
    echo Iptal edildi.
    pause
    exit /b 0
)

:: --reset islemi
if "%CHOICE%"=="1" (
    echo [*] opencode reset: %PY% "%DEST%\src\opencode_instruct.py" --reset --target opencode --yes
    if exist "%DEST%\src\opencode_instruct.py" (
        %PY% "%DEST%\src\opencode_instruct.py" --reset --target opencode --yes
    ) else (
        echo [!] Script bulunamadi, manuel temizleme gerekiyor.
        echo     %OPENCODE_HOME%\opencode.jsonc icindeki instructions dizisinden
        echo     "gpt-5.6-sol-v45.md" / "gpt-6-astra-v1.md" satirlarini silin.
    )
    goto :end
)
if "%CHOICE%"=="2" (
    echo [*] Codex reset
    if exist "%DEST%\src\opencode_instruct.py" (
        %PY% "%DEST%\src\opencode_instruct.py" --reset --target codex --yes
    ) else (
        echo [!] Script yok, Codex manuel: ~/.codex/config.toml - model_instructions_file satirini silin
    )
    goto :end
)
if "%CHOICE%"=="3" (
    echo [*] Hepsi temizleniyor...
    if exist "%DEST%\src\opencode_instruct.py" (
        echo     --reset both --yes
        %PY% "%DEST%\src\opencode_instruct.py" --reset --target both --yes
    ) else (
        echo [!] Script yok, configler manuel temizlenecek.
    )
    echo.
    echo [*] Skill klasoru siliniyor: %DEST%
    if exist "%DEST%" (
        rmdir /S /Q "%DEST%"
        if !errorlevel! equ 0 (
            echo [OK] Silindi.
        ) else (
            echo [HATA] Silinemedi, manuel silin.
        )
    )
    for %%F in ("gpt-5.6-sol-v45.md" "gpt-6-astra-v1.md") do (
        if exist "%OPENCODE_HOME%\%%~F" (
            echo     Siliniyor: %OPENCODE_HOME%\%%~F
            del /Q "%OPENCODE_HOME%\%%~F" 2>nul
        )
        if exist "%USERPROFILE%\.codex\%%~F" (
            echo     Siliniyor: %USERPROFILE%\.codex\%%~F
            del /Q "%USERPROFILE%\.codex\%%~F" 2>nul
        )
    )
)

:end
echo.
echo ============================================================
echo   KALDIRMA TAMAMLANDI
echo ============================================================
echo   Kontrol: %PY% "%DEST%\src\opencode_instruct.py" --status
echo   Yedekler: %OPENCODE_HOME%\*.bak_*  ve  %DEST%.bak_*
echo ============================================================
pause
endlocal
exit /b 0
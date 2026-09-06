@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title gpt-instruct opencode Global Kurulum

:: =============================================================
:: gpt-instruct - opencode global installer
:: Kaynak: MDX-Tom/gpt-instruct (codex-instruct.py tabanli)
:: Hedef: %USERPROFILE%\.config\opencode\skills\gpt-instruct
:: =============================================================

set "SRC=%~dp0SKILL_TEMPLATE\gpt-instruct"
set "DEST=%USERPROFILE%\.config\opencode\skills\gpt-instruct"
set "OPENCODE_HOME=%USERPROFILE%\.config\opencode"

echo.
echo ============================================================
echo   gpt-instruct  -- opencode Global Kurulum
echo   Kaynak: MDX-Tom/gpt-instruct  ^|  Lisans: MIT
echo ============================================================
echo.
echo   Kaynak : %SRC%
echo   Hedef  : %DEST%
echo   Config : %OPENCODE_HOME%\opencode.jsonc
echo.

:: --- Python bul ---
set "PY="
for %%P in (python python3 py) do (
    where %%P >nul 2>&1
    if !errorlevel! equ 0 (
        %%P --version >nul 2>&1
        if !errorlevel! equ 0 set "PY=%%P" & goto :foundpy
    )
)
:foundpy
if "%PY%"=="" (
    echo [HATA] Python bulunamadi. Lutfen Python 3.8+ kurun.
    echo        https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [*] Python: %PY%
%PY% --version
if errorlevel 1 (
    echo [HATA] Python calismiyor.
    pause
    exit /b 1
)

:: --- Kaynak kontrol ---
if not exist "%SRC%\SKILL.md" (
    echo [HATA] Kaynak bulunamadi: %SRC%\SKILL.md
    echo        install.bat ile SKILL_TEMPLATE ayni klasorde olmali.
    pause
    exit /b 1
)
if not exist "%SRC%\prompts\gpt-5.6-sol-v45.md" (
    echo [HATA] Prompt eksik: %SRC%\prompts\gpt-5.6-sol-v45.md
    pause
    exit /b 1
)

:: --- Hedef hazirla + yedek ---
if exist "%DEST%" (
    echo.
    echo [!] Mevcut kurulum bulundu: %DEST%
    set "BACKUP=%DEST%.bak_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "BACKUP=!BACKUP: =0!"
    echo     Yedekleniyor: !BACKUP!
    move /Y "%DEST%" "!BACKUP!" >nul
    if !errorlevel! neq 0 (
        echo [HATA] Yedekleme basarisiz. Hedef kilitli olabilir.
        pause
        exit /b 1
    )
    echo     [OK] Yedeklendi.
) else (
    echo [*] Yeni kurulum - yedek gerekmiyor.
)

:: --- Kopyala ---
echo.
echo [*] Skill kopyalaniyor...
mkdir "%DEST%" 2>nul
xcopy /E /I /Y /Q "%SRC%" "%DEST%" >nul
if errorlevel 1 (
    echo [HATA] Kopyalama basarisiz.
    pause
    exit /b 1
)
echo     [OK] %DEST%

:: --- Dogrulama ---
echo.
echo [*] Dogrulama: scripts\verify.py
%PY% "%DEST%\scripts\verify.py"
if errorlevel 1 (
    echo [UYARI] Dogrulama uyari verdi, devam ediliyor...
)

:: --- Secim: kalici global kurulsun mu? ---
echo.
echo ============================================================
echo   Kurulum tipi secin:
echo     1. Sadece skill - trigger ile calisir
echo     2. Skill + opencode global kalici - ONERILEN
echo     3. Skill + opencode + Codex hepsi
echo     4. Sadece skill kalsin, simdi bir sey yazma
echo ============================================================
set /p CHOICE="Secim [1/2/3/4] (varsayilan 2): "
if "%CHOICE%"=="" set "CHOICE=2"

:: Versiyon secimi
echo.
echo   Prompt versiyonu:
echo     1. gpt-5.6-sol-v45  - stable, 5170 B - varsayilan
echo     2. gpt-6-astra-v1   - formal, 7495 B
set /p VCHOICE="Versiyon [1/2] (varsayilan 1): "
if "%VCHOICE%"=="" set "VCHOICE=1"
if "%VCHOICE%"=="2" (
    set "VER=gpt-6-v1"
) else (
    set "VER=gpt-5.6-v45"
)

echo.
echo [*] Secilen: CHOICE=%CHOICE%  VER=%VER%  PY=%PY%

if "%CHOICE%"=="4" goto :done

if "%CHOICE%"=="1" (
    echo [*] Skill kuruldu, kalici global yazilmadi. Trigger ile kullanabilirsiniz.
    goto :done
)

if "%CHOICE%"=="2" (
    echo [*] Kalici opencode global kuruluyor: --target opencode --version %VER%
    %PY% "%DEST%\src\opencode_instruct.py" --apply --target opencode --version %VER%
    if errorlevel 1 (
        echo [HATA] opencode global deploy basarisiz. --dry-run ile test edin.
    ) else (
        echo [OK] opencode.jsonc instructions guncellendi.
    )
    goto :done
)

if "%CHOICE%"=="3" (
    echo [*] Hepsi: --target both --version %VER%
    %PY% "%DEST%\src\opencode_instruct.py" --apply --target both --version %VER%
    if errorlevel 1 (
        echo [UYARI] Bazi hedeflerde hata oldu, loga bakin.
    ) else (
        echo [OK] Codex + opencode guncellendi.
    )
    goto :done
)

:done
echo.
echo ============================================================
echo   KURULUM TAMAMLANDI
echo ============================================================
echo   Skill : %DEST%
echo   Test  : opencode icinde "gpt-instruct deploy et" yaz
echo   veya  : %PY% "%DEST%\src\opencode_instruct.py" --status
echo   Kaldir: uninstall.bat  veya  %PY% "%DEST%\src\opencode_instruct.py" --reset
echo.
echo   NOT: Bu promptlar UNRESTRICTED icerir. Hesap riski size aittir.
echo        Kalici globali kaldirmak icin --reset kullanin.
echo ============================================================
echo.
pause
endlocal
exit /b 0
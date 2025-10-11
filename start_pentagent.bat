@echo off
echo ================================================================================
echo     PENTAGENT - AI Powered Penetration Testing System
echo ================================================================================
echo.
echo [1] Web Interface ile Basla (Tavsiye Edilen)
echo [2] CLI Modu ile Basla
echo [3] Hizli Test (System Check)
echo [4] Web API'yi Basla (Backend)
echo [5] Cikis
echo.

set /p choice="Seciminizi yapin (1-5): "

if "%choice%"=="1" goto web_interface
if "%choice%"=="2" goto cli_mode
if "%choice%"=="3" goto quick_test
if "%choice%"=="4" goto web_api
if "%choice%"=="5" goto end

:web_interface
echo.
echo ================================================================================
echo     WEB INTERFACE BASLATILIYOR...
echo ================================================================================
echo.
echo [1/2] Backend (Web API) baslatiliyor...
start "Pentagent Backend" cmd /k "python web_api.py"
timeout /t 3 /nobreak > nul

echo [2/2] Frontend baslatiliyor...
cd pentagent-frontend
start "Pentagent Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ================================================================================
echo     PENTAGENT BASARILI SEKILDE BASLATILDI!
echo ================================================================================
echo.
echo     Backend:  http://localhost:8000
echo     Frontend: http://localhost:5173
echo.
echo     Tarayicinizda http://localhost:5173 adresini acin
echo.
pause
goto end

:cli_mode
echo.
echo ================================================================================
echo     CLI MODU BASLATILIYOR...
echo ================================================================================
echo.
python main.py
pause
goto end

:quick_test
echo.
echo ================================================================================
echo     HIZLI SISTEM KONTROLU
echo ================================================================================
echo.
python quick_test.py
echo.
pause
goto end

:web_api
echo.
echo ================================================================================
echo     WEB API BASLATILIYOR...
echo ================================================================================
echo.
python web_api.py
pause
goto end

:end
echo.
echo Gule gule!
exit
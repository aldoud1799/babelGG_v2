@echo off
setlocal

REM Launch BabelGG_v2 from this folder, regardless of drive/path.
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

if exist "%PY%" (
	"%PY%" "%ROOT%main.py"
) else (
	echo Python venv not found at "%PY%"
	echo Create .venv first, or run the unpacked app at dist\BabelGG\BabelGG.exe
	exit /b 1
)

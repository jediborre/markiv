@echo off
setlocal

net session >nul 2>&1
if errorlevel 1 (
    echo Se requieren permisos de administrador. Solicitando elevacion...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "SCRIPT_DIR=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%limpiar_tareas_exitosas.ps1" -Install
exit /b %ERRORLEVEL%

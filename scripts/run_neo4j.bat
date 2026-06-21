@echo off
title Neo4j Local Server
echo ===================================================
echo             STARTING LOCAL NEO4J SERVER            
echo ===================================================

REM Search for JDK 17 in common installation directories
for %%P in (
    "C:\Program Files\Microsoft\jdk-17.0.11.9-hotspot"
    "C:\Program Files\Java\jdk-17"
    "C:\Program Files\Eclipse Adoptium\jdk-17.0.11.9-hotspot"
) do (
    if exist "%%~P\bin\java.exe" (
        set "JAVA_HOME=%%~P"
        goto :java_ok
    )
)

REM Wildcard search in common directories
for /d %%D in ("C:\Program Files\Java\jdk-17*") do (
    if exist "%%D\bin\java.exe" (
        set "JAVA_HOME=%%D"
        goto :java_ok
    )
)
for /d %%D in ("C:\Program Files\Microsoft\jdk-17*") do (
    if exist "%%D\bin\java.exe" (
        set "JAVA_HOME=%%D"
        goto :java_ok
    )
)
for /d %%D in ("C:\Program Files\Eclipse Adoptium\jdk-17*") do (
    if exist "%%D\bin\java.exe" (
        set "JAVA_HOME=%%D"
        goto :java_ok
    )
)

REM Loop through all java.exe in PATH, pick the first JDK 17+
for /f "delims=" %%i in ('where java 2^>nul') do (
    for /f "tokens=3" %%v in ('"%%i" -version 2^>^&1 ^| findstr /i "version"') do (
        echo     Checking: %%i  version %%v
        echo %%v | findstr /c:"17." >nul && (
            for %%j in ("%%i") do set "JAVA_BIN_DIR=%%~dpj"
            for %%k in ("!JAVA_BIN_DIR!..") do set "JAVA_HOME=%%~fk"
            goto :java_ok
        )
    )
)

echo [ERR] JDK 17 not found. Neo4j 5.x requires JDK 17+.
echo       Install from: https://adoptium.net/temurin/releases/
pause
exit /b 1

:java_ok
echo [OK] JAVA_HOME: %JAVA_HOME%

echo Starting Neo4j in Console mode...
echo (You can open http://localhost:7474 in your browser)
echo (To stop the server, press Ctrl+C in this window)
echo ---------------------------------------------------

"%~dp0..\neo4j-community-5.26.0\bin\neo4j.bat" console

pause

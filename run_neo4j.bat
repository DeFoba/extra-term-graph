@echo off
title Neo4j Local Server
echo ===================================================
echo             STARTING LOCAL NEO4J SERVER            
echo ===================================================
echo Setting JAVA_HOME to JDK 17...
set "JAVA_HOME=C:\Program Files\Java\jdk-17"

echo Starting Neo4j in Console mode...
echo (You can open http://localhost:7474 in your browser)
echo (To stop the server, press Ctrl+C in this window)
echo ---------------------------------------------------

"%~dp0neo4j-community-5.26.0\bin\neo4j.bat" console

pause

#!/bin/bash
# ===================================================
#         STARTING LOCAL NEO4J SERVER (Linux)
# ===================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NEO4J_DIR="$SCRIPT_DIR/../neo4j-community-5.26.0"

echo "==================================================="
echo "         STARTING LOCAL NEO4J SERVER"
echo "==================================================="

# Check if Neo4j directory exists
if [ ! -d "$NEO4J_DIR" ]; then
    echo "ERROR: Neo4j directory not found at $NEO4J_DIR"
    echo "Download Neo4j Community from: https://neo4j.com/download-center/"
    echo "Extract it to: $SCRIPT_DIR/../neo4j-community-5.26.0/"
    exit 1
fi

# Check Java 17+
if command -v java &> /dev/null; then
    JAVA_VER=$(java -version 2>&1 | head -n1 | awk -F '"' '{print $2}' | cut -d'.' -f1)
    echo "Found Java version: $JAVA_VER"
    if [ "$JAVA_VER" -lt 17 ] 2>/dev/null; then
        echo "WARNING: Neo4j 5.x requires Java 17+. Current: $JAVA_VER"
        echo "Install Java 17: sudo apt install openjdk-17-jdk"
        exit 1
    fi
else
    echo "ERROR: Java not found in PATH."
    echo "Install Java 17: sudo apt install openjdk-17-jdk"
    exit 1
fi

# Make neo4j binary executable
chmod +x "$NEO4J_DIR/bin/neo4j"
chmod +x "$NEO4J_DIR/bin/cypher-shell"

echo "Starting Neo4j in Console mode..."
echo "(You can open http://localhost:7474 in your browser)"
echo "(To stop the server, press Ctrl+C)"
echo "---------------------------------------------------"

"$NEO4J_DIR/bin/neo4j" console

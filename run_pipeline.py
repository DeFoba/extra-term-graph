import os
import argparse
import sys
import socket
import time
import subprocess
import platform

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.corpus import build_corpus
from modules.keywords import extract_and_evaluate_keywords
from modules.summarization import generate_and_evaluate_summaries
from modules.graph import build_and_export_graph

def is_neo4j_responsive(host="127.0.0.1", port=7687):
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False

def ensure_neo4j_running(workspace_dir):
    print("Checking if Neo4j DBMS is running...")
    if is_neo4j_responsive():
        print("  ✓ Neo4j is already running and responsive.")
        return True

    print("  ✗ Neo4j is not running. Attempting to start it automatically...")
    system_os = platform.system().lower()
    
    if system_os == "windows":
        bat_path = os.path.join(workspace_dir, "scripts", "run_neo4j.bat")
        if os.path.exists(bat_path):
            print(f"  → Launching {bat_path} in a new console window...")
            try:
                subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
            except Exception as e:
                print(f"  ERROR launching .bat: {e}")
                return False
        else:
            print(f"  ERROR: {bat_path} not found.")
            return False
    else:
        sh_path = os.path.join(workspace_dir, "scripts", "run_neo4j.sh")
        if os.path.exists(sh_path):
            print(f"  → Launching {sh_path} in background...")
            try:
                os.chmod(sh_path, 0o755)
            except Exception:
                pass
            try:
                subprocess.Popen([sh_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
            except Exception as e:
                print(f"  ERROR launching .sh: {e}")
                return False
        else:
            print(f"  ERROR: {sh_path} not found.")
            return False

    print("  Waiting for Neo4j to start up (up to 30 seconds)...")
    for attempt in range(1, 31):
        time.sleep(2)
        if is_neo4j_responsive():
            print("  ✓ Neo4j started successfully!")
            return True
        print(f"    - Checking Neo4j connection (attempt {attempt}/30)...")
        
    print("  ⚠ Neo4j startup timed out. It might still be starting, or failed to start.")
    return False

def main():
    parser = argparse.ArgumentParser(description="NEW DIPLOM Pipeline Runner")
    parser.add_argument(
        "--step", 
        type=str, 
        default="all", 
        choices=["all", "corpus", "keywords", "summarize", "graph", "web"],
        help="Pipeline step to run: 'corpus' (PDF processing), 'keywords' (TF-IDF & KeyBERT extraction & eval), "
             "'summarize' (Extractive summaries & ROUGE), 'graph' (Construct graph & export CSVs/Cypher), "
             "'web' (Launch web UI for search & analysis), or 'all'."
    )
    parser.add_argument(
        "--jaccard_threshold", 
        type=float, 
        default=0.05, 
        help="Jaccard similarity threshold for paper-paper similarity edges (default: 0.05 for dense network)."
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="mlsa-iai-msu-lab/sci-rus-tiny",
        help="KeyBERT sentence embedding model name (default: mlsa-iai-msu-lab/sci-rus-tiny)."
    )
    parser.add_argument(
        "--max_articles",
        type=int,
        default=None,
        help="Maximum number of articles to process (for testing purposes, default: None)."
    )
    
    args = parser.parse_args()
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    
    env_path = os.path.join(workspace_dir, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            print(f"Auto-configured environment from .env")
        except Exception as e:
            print(f"Warning: Could not parse .env file: {e}")
            
    print("=" * 80)
    print("                      PIPELINE ORCHESTRATOR                      ")
    print("=" * 80)
    print(f"Working Directory: {workspace_dir}")
    print(f"Executing step:    {args.step.upper()}")
    if args.max_articles is not None:
        print(f"Limit articles:    {args.max_articles}")
    print("=" * 80 + "\n")
    
    try:
        if args.step in ["all", "graph", "web"]:
            ensure_neo4j_running(workspace_dir)

        if args.step == "corpus" or args.step == "all":
            print("[Step 1/4] Starting Corpus Construction...")
            build_corpus(workspace_dir, max_articles=args.max_articles)
            print("[Step 1/4] Corpus Construction Completed.\n")
            
        if args.step == "keywords" or args.step == "all":
            print("[Step 2/4] Starting Keyword Extraction and Evaluation...")
            extract_and_evaluate_keywords(workspace_dir, model_name=args.model_name, max_articles=args.max_articles)
            print("[Step 2/4] Keyword Extraction Completed.\n")
            
        if args.step == "summarize" or args.step == "all":
            print("[Step 3/4] Starting Extractive Summarization & ROUGE Evaluation...")
            generate_and_evaluate_summaries(workspace_dir, max_articles=args.max_articles)
            print("[Step 3/4] Summarization Completed.\n")
            
        if args.step == "graph" or args.step == "all":
            print("[Step 4/4] Starting Graph Construction and Ingestion...")
            build_and_export_graph(
                workspace_dir, 
                jaccard_threshold=args.jaccard_threshold,
                max_articles=args.max_articles
            )
            print(f"[Step 4/4] Graph Construction and Database Ingestion Completed.\n")
            
        if args.step == "web" or args.step == "all":
            print("[Web UI] Starting Extra-Term-Graph Web Interface...")
            from modules.web_app import app, load_data
            load_data()
            print("="*60)
            print("  Open in browser: http://localhost:5000")
            print("="*60)
            app.run(host="0.0.0.0", port=5000, debug=False)
            
        print("=" * 80)
        print("                         PIPELINE RUN COMPLETED SUCCESS!                    ")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nERROR: Pipeline execution failed at step '{args.step}': {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

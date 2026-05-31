import os
import argparse
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.corpus import build_corpus
from modules.keywords import extract_and_evaluate_keywords
from modules.summarization import generate_and_evaluate_summaries
from modules.graph import build_and_export_graph

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
        "--semantic_threshold", 
        type=float, 
        default=0.90, 
        help="Cosine similarity threshold for keyword-keyword semantic edges (default: 0.90)."
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
    
    cred_file = None
    for f_name in os.listdir(workspace_dir):
        if f_name.startswith("Neo4j-") and f_name.endswith(".txt"):
            cred_file = os.path.join(workspace_dir, f_name)
            break
            
    if cred_file:
        try:
            with open(cred_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    key = k.strip()
                    val = v.strip()
                    if key == "NEO4J_USERNAME":
                        os.environ["NEO4J_USER"] = val
                    elif key in ["NEO4J_URI", "NEO4J_PASSWORD"]:
                        os.environ[key] = val
            print(f"Auto-configured Neo4j environment from {os.path.basename(cred_file)}")
        except Exception as e:
            print(f"Warning: Could not parse credentials file {cred_file}: {e}")
            
    print("=" * 80)
    print("                      NEW DIPLOM PIPELINE ORCHESTRATOR                      ")
    print("=" * 80)
    print(f"Working Directory: {workspace_dir}")
    print(f"Executing step:    {args.step.upper()}")
    if args.max_articles is not None:
        print(f"Limit articles:    {args.max_articles}")
    print("=" * 80 + "\n")
    
    try:
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
            pubs_rel, _, _ = build_and_export_graph(
                workspace_dir, 
                jaccard_threshold=args.jaccard_threshold,
                
                max_articles=args.max_articles
            )
            print(f"[Step 4/4] Graph Construction Completed.")
            print(f"Generated paper similarity links (Jaccard >= {args.jaccard_threshold}): {pubs_rel}\n")
            
        if args.step == "web":
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

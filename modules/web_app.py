"""
Extra-Term-Graph — Web Interface
Flask server that serves the SPA and provides REST API
for browsing publications, keywords, and relationships.
Reads data from graph_export/ CSV files and corpus.json.
"""

import os
import csv
import json
from flask import Flask, jsonify, send_from_directory

# ─── Paths ───
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_EXPORT_DIR = os.path.join(BASE_DIR, "graph_export")
CORPUS_JSON_PATH = os.path.join(BASE_DIR, "corpus", "corpus.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development

# ─── In-memory data store ───
data_store = {
    "publications": [],
    "keywords": [],
    "rel_pub_keyword": [],
    "rel_pub_pub": [],
}


def load_csv(filename, transform=None):
    """Load a CSV file from graph_export/ and return list of dicts."""
    filepath = os.path.join(GRAPH_EXPORT_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  Warning: {filename} not found at {filepath}")
        return []
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if transform:
                row = transform(row)
            rows.append(row)
    return rows


def load_data():
    """Load all data into memory at startup."""
    print("Loading graph data...")

    # Publications: merge CSV with corpus.json for richer data
    pub_csv = load_csv("publications.csv")
    corpus_data = {}
    if os.path.exists(CORPUS_JSON_PATH):
        with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
            corpus_list = json.load(f)
            for item in corpus_list:
                corpus_data[item["filename"]] = item

    publications = []
    for row in pub_csv:
        pub_id = row.get("id", "")
        corpus_item = corpus_data.get(pub_id, {})
        # Authors: prefer corpus.json list, fallback to CSV string
        authors_list = corpus_item.get("authors", [])
        if not authors_list:
            authors_str = row.get("authors", "")
            authors_list = [a.strip() for a in authors_str.split(";") if a.strip()] if authors_str else []
        publications.append({
            "id": pub_id,
            "title": row.get("title", ""),
            "authors": authors_list,
            "annotation": row.get("annotation", ""),
            "summary_tfidf": row.get("summary_tfidf", ""),
            "summary_keybert": row.get("summary_keybert", ""),
            "keywords_author": corpus_item.get("keywords", []),
            "keywords_tfidf": corpus_item.get("keywords_tfidf", []),
            "keywords_keybert": corpus_item.get("keywords_keybert", []),
        })
    data_store["publications"] = publications

    # Keywords
    data_store["keywords"] = load_csv("keywords.csv")

    # Relationships
    def parse_weight(row):
        try:
            row["weight"] = float(row.get("weight", 1.0))
        except (ValueError, TypeError):
            row["weight"] = 1.0
        return row

    def parse_score(row):
        try:
            row["score"] = float(row.get("score", 0.0))
        except (ValueError, TypeError):
            row["score"] = 0.0
        return row

    data_store["rel_pub_keyword"] = load_csv("rel_pub_keyword.csv", parse_weight)
    data_store["rel_pub_pub"] = load_csv("rel_pub_pub.csv", parse_score)

    print(f"  Publications:     {len(data_store['publications'])}")
    print(f"  Keywords:         {len(data_store['keywords'])}")
    print(f"  Pub-KW rels:      {len(data_store['rel_pub_keyword'])}")
    print(f"  Pub-Pub rels:     {len(data_store['rel_pub_pub'])}")
    print("Data loaded successfully!\n")


# ─── Static file serving ───

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ─── API Endpoints ───

@app.route("/api/publications")
def api_publications():
    return jsonify(data_store["publications"])


@app.route("/api/keywords")
def api_keywords():
    return jsonify(data_store["keywords"])


@app.route("/api/rel_pub_keyword")
def api_rel_pub_keyword():
    return jsonify(data_store["rel_pub_keyword"])


@app.route("/api/rel_pub_pub")
def api_rel_pub_pub():
    return jsonify(data_store["rel_pub_pub"])




@app.route("/api/stats")
def api_stats():
    return jsonify({
        "publications": len(data_store["publications"]),
        "keywords": len(data_store["keywords"]),
        "rel_pub_keyword": len(data_store["rel_pub_keyword"]),
        "rel_pub_pub": len(data_store["rel_pub_pub"]),
    })


# ─── Main ───

if __name__ == "__main__":
    load_data()
    print("=" * 60)
    print("  Extra-Term-Graph Web Interface")
    print("  Open in browser: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)

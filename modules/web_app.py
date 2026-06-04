"""
Extra-Term-Graph — Web Interface
Flask server that serves the SPA and provides REST API
for browsing publications, keywords, and relationships.
ALL search and data retrieval is done via Cypher queries to Neo4j.
"""

import os
import json
from flask import Flask, jsonify, send_from_directory, request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CORPUS_JSON_PATH = os.path.join(BASE_DIR, "corpus", "corpus.json")

app = Flask(__name__, static_folder=STATIC_DIR)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

_driver = None

def _load_env():
    """Load .env file from project root into os.environ."""
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def get_neo4j_config():
    """Return Neo4j connection config from environment."""
    return {
        "uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.environ.get("NEO4J_USER", "neo4j"),
        "password": os.environ.get("NEO4J_PASSWORD", "extra_term_graph_2026"),
    }


def init_driver():
    """Initialize the Neo4j driver (call once at startup)."""
    global _driver
    _load_env()
    cfg = get_neo4j_config()
    try:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(cfg["uri"], auth=(cfg["user"], cfg["password"]))
        _driver.verify_connectivity()
        print(f"  ✓ Connected to Neo4j at {cfg['uri']}")
    except Exception as e:
        print(f"  ✗ Neo4j connection failed: {e}")
        print(f"    → Make sure Neo4j is running (run_neo4j.bat / run_neo4j.sh)")
        _driver = None


def close_driver():
    """Close the Neo4j driver."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def _run_query(cypher, params=None):
    """Execute a Cypher query and return list of record dicts."""
    if _driver is None:
        return None
    try:
        with _driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]
    except Exception as e:
        print(f"  Neo4j query error: {e}")
        return None


def _neo4j_error_response(message="Neo4j is not available"):
    """Return a JSON error response for Neo4j connectivity issues."""
    return jsonify({
        "error": message,
        "hint": "Start Neo4j: run_neo4j.bat (Windows) or ./run_neo4j.sh (Linux)"
    }), 503


_corpus_data = {}

def _load_corpus():
    """Load corpus.json for supplementary author data."""
    global _corpus_data
    if os.path.exists(CORPUS_JSON_PATH):
        try:
            with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
                corpus_list = json.load(f)
                _corpus_data = {item["filename"]: item for item in corpus_list}
            print(f"  ✓ Loaded corpus.json ({len(_corpus_data)} articles)")
        except Exception as e:
            print(f"  ✗ Failed to load corpus.json: {e}")


def _enrich_publication(rec):
    """Add corpus data (authors) to a publication record from Neo4j."""
    pub_id = rec.get("id", "")
    corpus_item = _corpus_data.get(pub_id, {})
    return {
        "id": pub_id,
        "title": rec.get("title", ""),
        "authors": corpus_item.get("authors", []),
        "annotation": rec.get("annotation", ""),
        "summary_tfidf": rec.get("summary_tfidf", ""),
        "summary_keybert": rec.get("summary_keybert", ""),
    }



@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route("/articles/<path:filename>")
def serve_article(filename):
    articles_dir = os.path.join(BASE_DIR, "articles")
    return send_from_directory(articles_dir, filename)



@app.route("/api/neo4j_config")
def api_neo4j_config():
    """Return Neo4j connection params for neovis.js frontend."""
    cfg = get_neo4j_config()
    return jsonify({
        "uri": cfg["uri"],
        "user": cfg["user"],
        "password": cfg["password"],
        "connected": _driver is not None,
    })



@app.route("/api/stats")
def api_stats():
    """Return aggregate counts from Neo4j."""
    records = _run_query("""
        OPTIONAL MATCH (d:Document) WITH count(d) AS pub_count
        OPTIONAL MATCH (k:Keyword) WITH pub_count, count(k) AS kw_count
        OPTIONAL MATCH (:Document)-[r:HAS_KEYWORD]->(:Keyword) WITH pub_count, kw_count, count(r) AS rel_pk
        RETURN pub_count, kw_count, rel_pk
    """)
    if records is None:
        return _neo4j_error_response()
    if records:
        r = records[0]
        return jsonify({
            "publications": r.get("pub_count", 0),
            "keywords": r.get("kw_count", 0),
            "rel_pub_keyword": r.get("rel_pk", 0),
            "rel_pub_pub": 0,
        })
    return jsonify({"publications": 0, "keywords": 0, "rel_pub_keyword": 0, "rel_pub_pub": 0})



@app.route("/api/publications")
def api_publications():
    """
    Search & paginate publications via Cypher.
    Query params: q (search), page (default 1), per_page (default 15)
    Search goes through: title, annotation, AND connected keywords (graph traversal).
    """
    q = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(50, max(1, int(request.args.get("per_page", 15))))
    skip = (page - 1) * per_page

    if q:
        query_lower = q.lower()
        count_records = _run_query("""
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:HAS_KEYWORD]->(k:Keyword)
            WITH d, collect(k) AS keywords
            WHERE toLower(d.title) CONTAINS $query
               OR toLower(d.annotation) CONTAINS $query
               OR any(kw IN keywords WHERE toLower(kw.name) CONTAINS $query)
            RETURN count(DISTINCT d) AS total
        """, {"query": query_lower})

        records = _run_query("""
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:HAS_KEYWORD]->(k:Keyword)
            WITH d, collect(k) AS keywords
            WHERE toLower(d.title) CONTAINS $query
               OR toLower(d.annotation) CONTAINS $query
               OR any(kw IN keywords WHERE toLower(kw.name) CONTAINS $query)
            RETURN DISTINCT d.id AS id, d.title AS title, d.annotation AS annotation,
                   d.summary_tfidf AS summary_tfidf, d.summary_keybert AS summary_keybert
            ORDER BY d.title
            SKIP $skip LIMIT $limit
        """, {"query": query_lower, "skip": skip, "limit": per_page})
    else:
        count_records = _run_query("MATCH (d:Document) RETURN count(d) AS total")
        records = _run_query("""
            MATCH (d:Document)
            RETURN d.id AS id, d.title AS title, d.annotation AS annotation,
                   d.summary_tfidf AS summary_tfidf, d.summary_keybert AS summary_keybert
            ORDER BY d.title
            SKIP $skip LIMIT $limit
        """, {"skip": skip, "limit": per_page})

    if records is None or count_records is None:
        return _neo4j_error_response()

    total = count_records[0].get("total", 0) if count_records else 0

    pub_ids = [r["id"] for r in records]
    kw_records = []
    if pub_ids:
        kw_records = _run_query("""
            MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword)
            WHERE d.id IN $pub_ids
            RETURN d.id AS pub_id, k.id AS keyword_id, k.name AS keyword_name,
                   r.method AS method, r.weight AS weight
        """, {"pub_ids": pub_ids}) or []

    pub_kw_map = {}
    for kr in kw_records:
        pid = kr["pub_id"]
        if pid not in pub_kw_map:
            pub_kw_map[pid] = []
        pub_kw_map[pid].append({
            "keyword_id": kr["keyword_id"],
            "keyword_name": kr["keyword_name"],
            "method": kr["method"],
            "weight": kr["weight"],
        })

    publications = []
    for rec in records:
        pub = _enrich_publication(rec)
        pub["keywords"] = pub_kw_map.get(rec["id"], [])
        publications.append(pub)

    return jsonify({
        "items": publications,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
        "query": q,
    })



@app.route("/api/publications/<path:pub_id>")
def api_publication_detail(pub_id):
    """Get full details for a single publication, including keywords and similar docs."""
    records = _run_query("""
        MATCH (d:Document {id: $pub_id})
        RETURN d.id AS id, d.title AS title, d.annotation AS annotation,
               d.summary_tfidf AS summary_tfidf, d.summary_keybert AS summary_keybert
    """, {"pub_id": pub_id})
    if records is None:
        return _neo4j_error_response()
    if not records:
        return jsonify({"error": "Publication not found"}), 404

    pub = _enrich_publication(records[0])

    kw_records = _run_query("""
        MATCH (d:Document {id: $pub_id})-[r:HAS_KEYWORD]->(k:Keyword)
        RETURN k.id AS keyword_id, k.name AS keyword_name,
               r.method AS method, r.weight AS weight
        ORDER BY r.method, r.weight DESC
    """, {"pub_id": pub_id}) or []

    pub["keywords"] = [{
        "keyword_id": kr["keyword_id"],
        "keyword_name": kr["keyword_name"],
        "method": kr["method"],
        "weight": kr["weight"],
    } for kr in kw_records]

    sim_records = _run_query("""
        MATCH (d1:Document {id: $pub_id})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)
        WHERE d1 <> d2
        RETURN d2.id AS id, d2.title AS title, count(DISTINCT k) AS score, collect(DISTINCT k.name) AS shared
        ORDER BY score DESC
        LIMIT 10
    """, {"pub_id": pub_id}) or []

    pub["similar"] = [{
        "id": sr["id"],
        "title": sr["title"],
        "score": sr["score"],
        "shared": sr["shared"]
    } for sr in sim_records]

    return jsonify(pub)



@app.route("/api/keywords")
def api_keywords():
    """
    Search & paginate keywords via Cypher.
    Query params: q (search), method (author|tfidf|keybert), page, per_page
    """
    q = request.args.get("q", "").strip()
    method = request.args.get("method", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 30))))
    skip = (page - 1) * per_page

    where_clauses = []
    params = {"skip": skip, "limit": per_page}

    if q:
        where_clauses.append("toLower(k.name) CONTAINS $query")
        params["query"] = q.lower()

    if method and method != "all":
        where_clauses.append("r.method = $method")
        params["method"] = method

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_records = _run_query(f"""
        MATCH (k:Keyword)<-[r:HAS_KEYWORD]-(d:Document)
        {where_sql}
        RETURN count(DISTINCT k) AS total
    """, params)

    records = _run_query(f"""
        MATCH (k:Keyword)<-[r:HAS_KEYWORD]-(d:Document)
        {where_sql}
        WITH k, count(DISTINCT d) AS pub_count, collect(DISTINCT r.method) AS methods
        RETURN k.id AS id, k.name AS name, k.methods AS methods_str,
               pub_count, methods
        ORDER BY pub_count DESC
        SKIP $skip LIMIT $limit
    """, params)

    if records is None or count_records is None:
        return _neo4j_error_response()

    total = count_records[0].get("total", 0) if count_records else 0

    return jsonify({
        "items": [{
            "id": r["id"],
            "name": r["name"],
            "methods": r.get("methods_str", ""),
            "pub_count": r.get("pub_count", 0),
        } for r in records],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-total // per_page)),
        "query": q,
        "method_filter": method,
    })



@app.route("/api/keywords/<path:kw_id>")
def api_keyword_detail(kw_id):
    """Get full details for a single keyword, including related publications."""
    records = _run_query("""
        MATCH (k:Keyword {id: $kw_id})
        RETURN k.id AS id, k.name AS name, k.methods AS methods_str
    """, {"kw_id": kw_id})
    if records is None:
        return _neo4j_error_response()
    if not records:
        return jsonify({"error": "Keyword not found"}), 404

    rec = records[0]

    pub_records = _run_query("""
        MATCH (k:Keyword {id: $kw_id})<-[r:HAS_KEYWORD]-(d:Document)
        RETURN d.id AS pub_id, d.title AS title, r.method AS method, r.weight AS weight
        ORDER BY r.method, d.title
    """, {"kw_id": kw_id}) or []

    return jsonify({
        "id": rec["id"],
        "name": rec["name"],
        "methods": rec.get("methods_str", ""),
        "pub_rels": [{
            "pub_id": pr["pub_id"],
            "title": pr["title"],
            "method": pr["method"],
            "weight": pr["weight"],
        } for pr in pub_records],
    })



@app.route("/api/search/graph")
def api_search_graph():
    """
    Generate a Cypher query for visualizing search results on the graph.
    This shows HOW the search traverses the graph structure.
    """
    q = request.args.get("q", "").strip()
    search_type = request.args.get("type", "publications")

    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    query_lower = q.lower()

    if search_type == "keywords":
        cypher = (
            f"MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword)\n"
            f"WHERE toLower(k.name) CONTAINS '{_escape_cypher(query_lower)}'\n"
            f"RETURN d, r, k\n"
            f"LIMIT 150"
        )
        description = f"Термины, содержащие «{q}», и связанные публикации"
    else:
        cypher = (
            f"MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword)\n"
            f"WHERE toLower(d.title) CONTAINS '{_escape_cypher(query_lower)}'\n"
            f"   OR toLower(d.annotation) CONTAINS '{_escape_cypher(query_lower)}'\n"
            f"   OR toLower(k.name) CONTAINS '{_escape_cypher(query_lower)}'\n"
            f"RETURN d, r, k\n"
            f"LIMIT 200"
        )
        description = f"Публикации и термины, связанные с «{q}»"

    return jsonify({
        "cypher": cypher,
        "description": description,
        "query": q,
    })


def _escape_cypher(s):
    """Escape a string for safe inclusion in Cypher literals."""
    return s.replace("\\", "\\\\").replace("'", "\\'")



def load_data():
    """Initialize Neo4j connection and load corpus data."""
    print("Initializing Extra-Term-Graph Web API...")
    init_driver()
    _load_corpus()

    if _driver:
        result = _run_query("MATCH (d:Document) RETURN count(d) AS cnt")
        if result:
            cnt = result[0].get("cnt", 0)
            print(f"  ✓ Neo4j contains {cnt} documents")
            if cnt == 0:
                print("  ⚠ Database is empty. Run: python run_pipeline.py --step graph")
    else:
        print("  ⚠ Running without Neo4j — API will return errors")
        print("    → Start Neo4j first: run_neo4j.bat (Windows) or ./run_neo4j.sh (Linux)")

    print("Initialization complete!\n")


if __name__ == "__main__":
    load_data()
    print("=" * 60)
    print("  Extra-Term-Graph Web Interface")
    print("  Open in browser: http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)

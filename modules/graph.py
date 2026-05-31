import os
import re
import json
import csv
import pymorphy3
from tqdm import tqdm

morph = pymorphy3.MorphAnalyzer()
lemma_cache = {}

def normalize_phrase(phrase):
    if not phrase:
        return ""
    phrase = phrase.lower()
    words = re.findall(r'[а-яёa-z0-9]+', phrase)
    normalized_words = []
    for w in words:
        if w not in lemma_cache:
            parsed = morph.parse(w)[0]
            lemma_cache[w] = parsed.normal_form
        normalized_words.append(lemma_cache[w])
    return " ".join(sorted(normalized_words))

def build_and_export_graph(workspace_dir, jaccard_threshold=0.05, similarity_threshold=0.85, max_articles=None):
    corpus_dir = os.path.join(workspace_dir, "corpus")
    summary_json_path = os.path.join(corpus_dir, "corpus.json")
    export_dir = os.path.join(workspace_dir, "graph_export")
    
    if not os.path.exists(summary_json_path):
        raise FileNotFoundError(f"Consolidated index '{summary_json_path}' not found.")
        
    os.makedirs(export_dir, exist_ok=True)
    
    print("Loading corpus index...")
    with open(summary_json_path, "r", encoding="utf-8") as jf:
        corpus_data = json.load(jf)
        
    if max_articles is not None:
        corpus_data = corpus_data[:max_articles]
        
    print(f"Loaded {len(corpus_data)} articles. Extracting and normalizing keywords...")
    
    unique_keywords = {}
    publications = []
    pub_keyword_rels = []
    
    for item in corpus_data:
        filename = item["filename"]
        title = item["title"]
        annotation = item.get("annotation", "")
        
        name_no_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(corpus_dir, f"{name_no_ext}.json")
        
        summary_tfidf = ""
        summary_keybert = ""
        kw_tfidf = []
        kw_keybert = []
        
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as ajf:
                    art_data = json.load(ajf)
                    summarization = art_data.get("summarization", {})
                    summary_tfidf = summarization.get("summary_tfidf", "")
                    summary_keybert = summarization.get("summary_keybert", "")
                    kw_tfidf = art_data.get("keywords_tfidf", [])
                    kw_keybert = art_data.get("keywords_keybert", [])
            except Exception as e:
                print(f"Warning reading {filename}: {e}")
                
        pub_id = filename
        publications.append({
            "id": pub_id,
            "title": title,
            "authors": "; ".join(item.get("authors", [])),
            "annotation": annotation,
            "summary_tfidf": summary_tfidf,
            "summary_keybert": summary_keybert
        })
        
        kw_sources = [
            ("author", item.get("keywords", []), None),
            ("tfidf", kw_tfidf, None),
            ("keybert", kw_keybert, None)
        ]
        
        for method, kw_list, _ in kw_sources:
            for idx, kw in enumerate(kw_list):
                kw_str = kw.strip()
                if not kw_str:
                    continue
                
                norm_id = normalize_phrase(kw_str)
                if not norm_id:
                    continue
                    
                if norm_id not in unique_keywords:
                    unique_keywords[norm_id] = {
                        "originals": {},
                        "display_name": kw_str.capitalize()
                    }
                
                originals = unique_keywords[norm_id]["originals"]
                originals[kw_str] = originals.get(kw_str, 0) + 1
                
                weight = 1.0
                if method in ["tfidf", "keybert"]:
                    weight = float(10 - min(idx, 9))
                    
                pub_keyword_rels.append({
                    "pub_id": pub_id,
                    "keyword_id": norm_id,
                    "method": method,
                    "weight": weight
                })
                
    for norm_id, kw_info in unique_keywords.items():
        originals = kw_info["originals"]
        best_spelling = max(originals, key=originals.get)
        kw_info["display_name"] = best_spelling[0].upper() + best_spelling[1:] if best_spelling else norm_id
        
    print(f"Found {len(unique_keywords)} unique keywords after morphological normalization.")

    print(f"\nComputing document similarity based on keyword overlap (threshold >= {jaccard_threshold})...")
    pub_pub_rels = []
    
    pub_to_keywords = {}
    for r in pub_keyword_rels:
        pid = r["pub_id"]
        kw_id = r["keyword_id"]
        if pid not in pub_to_keywords:
            pub_to_keywords[pid] = set()
        pub_to_keywords[pid].add(kw_id)
        
    pub_ids = [p["id"] for p in publications]
    
    for i in range(len(pub_ids)):
        kws_i = pub_to_keywords.get(pub_ids[i], set())
        if not kws_i:
            continue
        for j in range(i + 1, len(pub_ids)):
            kws_j = pub_to_keywords.get(pub_ids[j], set())
            if not kws_j:
                continue
            
            intersection = kws_i.intersection(kws_j)
            union = kws_i.union(kws_j)
            jaccard = len(intersection) / len(union)
            
            if jaccard >= jaccard_threshold:
                pub_pub_rels.append({
                    "source": pub_ids[i],
                    "target": pub_ids[j],
                    "score": round(jaccard, 4)
                })
                
    print(f"Generated {len(pub_pub_rels)} publication similarity links.")

    # Determine dominant method for each keyword (for coloring in Neo4j)
    kw_method_map = {}
    for r in pub_keyword_rels:
        nid = r["keyword_id"]
        method = r["method"]
        if nid not in kw_method_map:
            kw_method_map[nid] = set()
        kw_method_map[nid].add(method)
    for nid, info in unique_keywords.items():
        methods = kw_method_map.get(nid, set())
        info["methods"] = ",".join(sorted(methods))

    print(f"\nWriting CSV graph nodes & edges to: {export_dir}")
    
    pub_csv_path = os.path.join(export_dir, "publications.csv")
    with open(pub_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["id", "title", "authors", "annotation", "summary_tfidf", "summary_keybert"])
        for p in publications:
            writer.writerow([p["id"], p["title"], p["authors"], p["annotation"], p["summary_tfidf"], p["summary_keybert"]])
            
    kw_csv_path = os.path.join(export_dir, "keywords.csv")
    with open(kw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["id", "name", "methods"])
        for nid, info in unique_keywords.items():
            writer.writerow([nid, info["display_name"], info.get("methods", "")])
            
    pub_kw_csv_path = os.path.join(export_dir, "rel_pub_keyword.csv")
    with open(pub_kw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["pub_id", "keyword_id", "method", "weight"])
        for r in pub_keyword_rels:
            writer.writerow([r["pub_id"], r["keyword_id"], r["method"], r["weight"]])
            
    pub_pub_csv_path = os.path.join(export_dir, "rel_pub_pub.csv")
    with open(pub_pub_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["source", "target", "score"])
        for r in pub_pub_rels:
            writer.writerow([r["source"], r["target"], r["score"]])
            

    # Generate Cypher LOAD CSV Script for Aura DB in the graph_export directory
    cypher_script_path = os.path.join(export_dir, "import_csv.cypher")
    print(f"Generating Neo4j LOAD CSV script: {cypher_script_path}")
    
    with open(cypher_script_path, "w", encoding="utf-8") as f:
        f.write("// --- Neo4j CSV Import Script ---\n")
        f.write("// Instructions: Place the CSV files from 'graph_export/' into your Neo4j Import folder,\n")
        f.write("// or set your own file path prefix (e.g. file:///rel_pub_pub.csv).\n\n")
        
        f.write("// 1. Create Constraints\n")
        f.write("CREATE CONSTRAINT pub_id_constraint IF NOT EXISTS FOR (p:Publication) REQUIRE p.id IS UNIQUE;\n")
        f.write("CREATE CONSTRAINT kw_id_constraint IF NOT EXISTS FOR (k:Keyword) REQUIRE k.id IS UNIQUE;\n\n")
        
        f.write("// 2. Import Publication Nodes\n")
        f.write("LOAD CSV WITH HEADERS FROM 'file:///publications.csv' AS row\n")
        f.write("MERGE (p:Publication {id: row.id})\n")
        f.write("SET p.title = row.title,\n")
        f.write("    p.annotation = row.annotation,\n")
        f.write("    p.summary_tfidf = row.summary_tfidf,\n")
        f.write("    p.summary_keybert = row.summary_keybert;\n\n")
        
        f.write("// 3. Import Keyword Nodes (with methods for color-coding)\n")
        f.write("LOAD CSV WITH HEADERS FROM 'file:///keywords.csv' AS row\n")
        f.write("MERGE (k:Keyword {id: row.id})\n")
        f.write("SET k.name = row.name, k.methods = row.methods;\n\n")
        
        f.write("// 4. Import Publication-Keyword Relationships\n")
        f.write("LOAD CSV WITH HEADERS FROM 'file:///rel_pub_keyword.csv' AS row\n")
        f.write("MATCH (p:Publication {id: row.pub_id})\n")
        f.write("MATCH (k:Keyword {id: row.keyword_id})\n")
        f.write("CREATE (p)-[:HAS_KEYWORD {method: row.method, weight: toFloat(row.weight)}]->(k);\n\n")
        
        f.write("// 5. Import Publication Similarity Relationships\n")
        f.write("LOAD CSV WITH HEADERS FROM 'file:///rel_pub_pub.csv' AS row\n")
        f.write("MATCH (p1:Publication {id: row.source})\n")
        f.write("MATCH (p2:Publication {id: row.target})\n")
        f.write("CREATE (p1)-[:SIMILAR_TO {score: toFloat(row.score)}]->(p2);\n\n")
        
        f.write("// 6. Assign color labels to Keywords by extraction method\n")
        f.write("MATCH (k:Keyword) WHERE k.methods CONTAINS 'author' SET k:AuthorKW;\n")
        f.write("MATCH (k:Keyword) WHERE k.methods CONTAINS 'tfidf' SET k:TFIDFKW;\n")
        f.write("MATCH (k:Keyword) WHERE k.methods CONTAINS 'keybert' SET k:KeyBERTKW;\n\n")

    print("\nAttempting to connect and upload to Neo4j database...")
    
    cred_file = None
    for f_name in os.listdir(workspace_dir):
        if f_name.startswith("Neo4j-") and f_name.endswith(".txt"):
            cred_file = os.path.join(workspace_dir, f_name)
            break
            
    file_creds = {}
    if cred_file:
        print(f"Found Neo4j credentials file: {os.path.basename(cred_file)}")
        try:
            with open(cred_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    file_creds[k.strip()] = v.strip()
        except Exception as e:
            print(f"Warning: Could not parse credentials file: {e}")

    neo4j_uri = os.environ.get("NEO4J_URI", file_creds.get("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user_file = file_creds.get("NEO4J_USERNAME", file_creds.get("NEO4J_USER", "neo4j"))
    neo4j_user = os.environ.get("NEO4J_USER", neo4j_user_file)
    neo4j_password = os.environ.get("NEO4J_PASSWORD", file_creds.get("NEO4J_PASSWORD", "extra_term_graph_2026"))
    
    if not neo4j_password:
        print("Neo4j password not found in environment or file. Skipping database upload.")
        return len(pub_pub_rels), 0
        
    try:
        from neo4j import GraphDatabase
        print(f"Connecting to Neo4j at {neo4j_uri}...")
        try:
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            driver.verify_connectivity()
            print(f"Connected successfully using user '{neo4j_user}'!")
        except Exception as conn_err:
            if neo4j_user != "neo4j":
                print(f"Connection failed with user '{neo4j_user}': {conn_err}")
                print("Trying fallback user 'neo4j' (standard for Aura DB)...")
                driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", neo4j_password))
                driver.verify_connectivity()
                print("Connected successfully using fallback user 'neo4j'!")
            else:
                raise conn_err
                
        print("Uploading in-memory batches...")
        
        def create_constraints(tx):
            tx.run("CREATE CONSTRAINT pub_id_constraint IF NOT EXISTS FOR (p:Publication) REQUIRE p.id IS UNIQUE")
            tx.run("CREATE CONSTRAINT kw_id_constraint IF NOT EXISTS FOR (k:Keyword) REQUIRE k.id IS UNIQUE")
            
        def clear_graph(tx):
            tx.run("MATCH (p:Publication) DETACH DELETE p")
            tx.run("MATCH (k:Keyword) DETACH DELETE k")
            
        def upload_publications(tx, batch):
            tx.run("""
            UNWIND $batch AS p
            MERGE (pub:Publication {id: p.id})
            SET pub.title = p.title, pub.annotation = p.annotation,
                pub.summary_tfidf = p.summary_tfidf, pub.summary_keybert = p.summary_keybert
            """, batch=batch)
            
        def upload_keywords(tx, batch):
            tx.run("""
            UNWIND $batch AS k
            MERGE (kw:Keyword {id: k.id})
            SET kw.name = k.name, kw.methods = k.methods
            """, batch=batch)
            
        def upload_pub_kw(tx, batch):
            tx.run("""
            UNWIND $batch AS r
            MATCH (p:Publication {id: r.pub_id})
            MATCH (k:Keyword {id: r.keyword_id})
            CREATE (p)-[:HAS_KEYWORD {method: r.method, weight: r.weight}]->(k)
            """, batch=batch)
            
        def upload_pub_pub(tx, batch):
            tx.run("""
            UNWIND $batch AS r
            MATCH (p1:Publication {id: r.source})
            MATCH (p2:Publication {id: r.target})
            CREATE (p1)-[:SIMILAR_TO {score: r.score}]->(p2)
            """, batch=batch)
            

            
        nodes_keywords = [{"id": nid, "name": info["display_name"], "methods": info.get("methods", "")} for nid, info in unique_keywords.items()]
        
        with driver.session() as session:
            session.execute_write(create_constraints)
            session.execute_write(clear_graph)
            
            print("Uploading publications...")
            for i in range(0, len(publications), 100):
                session.execute_write(upload_publications, publications[i:i+100])
                
            print("Uploading keywords...")
            for i in range(0, len(nodes_keywords), 100):
                session.execute_write(upload_keywords, nodes_keywords[i:i+100])
                
            print("Uploading publication-keyword extraction links...")
            for i in range(0, len(pub_keyword_rels), 500):
                session.execute_write(upload_pub_kw, pub_keyword_rels[i:i+500])
                
            print("Uploading publication similarity links...")
            for i in range(0, len(pub_pub_rels), 500):
                session.execute_write(upload_pub_pub, pub_pub_rels[i:i+500])
            
            print("Assigning color labels to keywords...")
            def assign_kw_labels(tx):
                tx.run("MATCH (k:Keyword) WHERE k.methods CONTAINS 'author' SET k:AuthorKW")
                tx.run("MATCH (k:Keyword) WHERE k.methods CONTAINS 'tfidf' SET k:TFIDFKW")
                tx.run("MATCH (k:Keyword) WHERE k.methods CONTAINS 'keybert' SET k:KeyBERTKW")
            session.execute_write(assign_kw_labels)
                
        driver.close()
        print("\n=== Graph Ingested and Uploaded to Neo4j Successfully! ===")
    except ImportError:
        print("\nNotice: 'neo4j' package is not installed. Skipping database upload.")
    except Exception as e:
        print(f"\nConnection to Neo4j database failed: {e}. Skipping database upload.")
        
    print("\n--- Graph Export Stage Completed ---")
    return len(pub_pub_rels), 0

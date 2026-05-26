// --- Neo4j CSV Import Script ---
// Instructions: Place the CSV files from 'graph_export/' into your Neo4j Import folder,
// or set your own file path prefix (e.g. file:///rel_pub_pub.csv).

// 1. Create Constraints
CREATE CONSTRAINT pub_id_constraint IF NOT EXISTS FOR (p:Publication) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT kw_id_constraint IF NOT EXISTS FOR (k:Keyword) REQUIRE k.id IS UNIQUE;

// 2. Import Publication Nodes
LOAD CSV WITH HEADERS FROM 'file:///publications.csv' AS row
MERGE (p:Publication {id: row.id})
SET p.title = row.title,
    p.annotation = row.annotation,
    p.summary_tfidf = row.summary_tfidf,
    p.summary_keybert = row.summary_keybert;

// 3. Import Keyword Nodes
LOAD CSV WITH HEADERS FROM 'file:///keywords.csv' AS row
MERGE (k:Keyword {id: row.id})
SET k.name = row.name;

// 4. Import Publication-Keyword Relationships
LOAD CSV WITH HEADERS FROM 'file:///rel_pub_keyword.csv' AS row
MATCH (p:Publication {id: row.pub_id})
MATCH (k:Keyword {id: row.keyword_id})
CREATE (p)-[:HAS_KEYWORD {method: row.method, weight: toFloat(row.weight)}]->(k);

// 5. Import Publication Similarity Relationships
LOAD CSV WITH HEADERS FROM 'file:///rel_pub_pub.csv' AS row
MATCH (p1:Publication {id: row.source})
MATCH (p2:Publication {id: row.target})
CREATE (p1)-[:SIMILAR_TO {score: toFloat(row.score)}]->(p2);

// 6. Import Keyword Semantic Similarity Relationships
LOAD CSV WITH HEADERS FROM 'file:///rel_keyword_keyword.csv' AS row
MATCH (k1:Keyword {id: row.source})
MATCH (k2:Keyword {id: row.target})
CREATE (k1)-[:SEMANTICALLY_SIMILAR {score: toFloat(row.score)}]->(k2);

// 7. Import Keyword Hierarchy (SUB_TERM_OF) Relationships
LOAD CSV WITH HEADERS FROM 'file:///rel_keyword_hierarchy.csv' AS row
MATCH (k2:Keyword {id: row.source})
MATCH (k1:Keyword {id: row.target})
CREATE (k2)-[:SUB_TERM_OF]->(k1);

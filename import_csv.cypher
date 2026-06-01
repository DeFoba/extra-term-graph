// --- Neo4j CSV Import Script ---
// Instructions: Place the CSV files from 'graph_export/' into your Neo4j Import folder,
// or set your own file path prefix (e.g. file:///rel_pub_pub.csv).

// 1. Create Constraints
CREATE CONSTRAINT pub_id_constraint IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT kw_id_constraint IF NOT EXISTS FOR (k:Keyword) REQUIRE k.id IS UNIQUE;

// 2. Import Document Nodes
LOAD CSV WITH HEADERS FROM 'file:///publications.csv' AS row
MERGE (d:Document {id: row.id})
SET d.title = row.title,
    d.annotation = row.annotation,
    d.summary_tfidf = row.summary_tfidf,
    d.summary_keybert = row.summary_keybert;

// 3. Import Keyword Nodes (with methods for color-coding)
LOAD CSV WITH HEADERS FROM 'file:///keywords.csv' AS row
MERGE (k:Keyword {id: row.id})
SET k.name = row.name, k.methods = row.methods;

// 4. Import Document-Keyword Relationships
LOAD CSV WITH HEADERS FROM 'file:///rel_pub_keyword.csv' AS row
MATCH (d:Document {id: row.pub_id})
MATCH (k:Keyword {id: row.keyword_id})
CREATE (d)-[:HAS_KEYWORD {method: row.method, weight: toFloat(row.weight)}]->(k);

// 5. Import Document Similarity Relationships
LOAD CSV WITH HEADERS FROM 'file:///rel_pub_pub.csv' AS row
MATCH (d1:Document {id: row.source})
MATCH (d2:Document {id: row.target})
CREATE (d1)-[:SIMILAR_TO {score: toFloat(row.score)}]->(d2);

// 6. Assign color labels to Keywords by extraction method
MATCH (k:Keyword) WHERE k.methods CONTAINS 'author' SET k:AuthorKW;
MATCH (k:Keyword) WHERE k.methods CONTAINS 'tfidf' SET k:TFIDFKW;
MATCH (k:Keyword) WHERE k.methods CONTAINS 'keybert' SET k:KeyBERTKW;


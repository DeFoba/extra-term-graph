import os
import re
import json
import pymorphy3
from tqdm import tqdm

morph = pymorphy3.MorphAnalyzer()
lemma_cache = {}

ABBREVIATIONS = {
    'рис', 'табл', 'г', 'вв', 'в', 'т.е', 'т.к', 'и др', 'см', 'стр', 
    'обл', 'акад', 'проф', 'доц', 'напр', 'п', 'вып', 'с', 'соавт',
    'fig', 'tab', 'e.g', 'i.e', 'al', 'vs', 'vol', 'no', 'pp'
}

def split_sentences(text):
    if not text:
        return []
    
    raw_splits = re.split(r'([.!?]\s+)', text)
    sentences = []
    current_sent = ""
    
    i = 0
    while i < len(raw_splits):
        part = raw_splits[i]
        current_sent += part
        
        if i + 1 < len(raw_splits):
            last_word_match = re.search(r'\b([а-яёa-z]+)[.!?]$', current_sent.lower().strip())
            if last_word_match:
                last_word = last_word_match.group(1)
                if last_word in ABBREVIATIONS:
                    current_sent += raw_splits[i+1]
                    i += 2
                    continue
            
            if i + 2 < len(raw_splits):
                next_text = raw_splits[i+2].strip()
                if next_text and not next_text[0].isupper() and next_text[0].isalnum():
                    current_sent += raw_splits[i+1]
                    i += 2
                    continue
            
            sentences.append(current_sent.strip())
            current_sent = ""
            i += 2
        else:
            i += 1
            
    if current_sent.strip():
        sentences.append(current_sent.strip())
        
    cleaned_sentences = []
    for s in sentences:
        s_clean = re.sub(r'\s+', ' ', s).strip()
        if s_clean:
            cleaned_sentences.append(s_clean)
            
    return cleaned_sentences

def filter_sentences(sentences):
    filtered = []
    for idx, s in enumerate(sentences):
        words = re.findall(r'[а-яёa-z0-9]+', s.lower())
        if len(words) < 8 or len(words) > 60:
            continue
            
        if re.match(r'^(рисунок|рис\.|таблица|табл\.|введение|заключение|литература|источники|с\.|стр\.|рис\s\d|табл\s\d)', s.strip().lower()):
            continue
            
        filtered.append((idx, s))
    return filtered

def lemmatize_word(word):
    w_clean = word.lower()
    if w_clean not in lemma_cache:
        lemma_cache[w_clean] = morph.parse(w_clean)[0].normal_form
    return lemma_cache[w_clean]

def tokenize_raw(text):
    return re.findall(r'[а-яёa-z0-9]+', text.lower())

def tokenize_lemmatized(text):
    words = tokenize_raw(text)
    return [lemmatize_word(w) for w in words]

def compute_lcs(x, y):
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        return 0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if x[i - 1] == y[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]

def compute_rouge_n(cand_tokens, ref_tokens, n):
    if len(cand_tokens) < n or len(ref_tokens) < n:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
    def get_ngrams(tokens, n):
        return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
        
    cand_ngrams = get_ngrams(cand_tokens, n)
    ref_ngrams = get_ngrams(ref_tokens, n)
    
    from collections import Counter
    cand_counts = Counter(cand_ngrams)
    ref_counts = Counter(ref_ngrams)
    
    overlap = 0
    for gram, count in ref_counts.items():
        if gram in cand_counts:
            overlap += min(count, cand_counts[gram])
            
    precision = overlap / len(cand_ngrams) if cand_ngrams else 0.0
    recall = overlap / len(ref_ngrams) if ref_ngrams else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}

def compute_rouge_l(cand_tokens, ref_tokens):
    if not cand_tokens or not ref_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    lcs_len = compute_lcs(cand_tokens, ref_tokens)
    precision = lcs_len / len(cand_tokens)
    recall = lcs_len / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}

def evaluate_summary(cand_text, ref_text):
    cand_raw = tokenize_raw(cand_text)
    ref_raw = tokenize_raw(ref_text)
    raw_metrics = {
        "rouge1": compute_rouge_n(cand_raw, ref_raw, 1),
        "rouge2": compute_rouge_n(cand_raw, ref_raw, 2),
        "rougeL": compute_rouge_l(cand_raw, ref_raw)
    }
    
    cand_lem = tokenize_lemmatized(cand_text)
    ref_lem = tokenize_lemmatized(ref_text)
    lem_metrics = {
        "rouge1": compute_rouge_n(cand_lem, ref_lem, 1),
        "rouge2": compute_rouge_n(cand_lem, ref_lem, 2),
        "rougeL": compute_rouge_l(cand_lem, ref_lem)
    }
    return {
        "raw": raw_metrics,
        "lemmatized": lem_metrics
    }

def compute_sentence_similarity(sent1_lemmas, sent2_lemmas):
    if not sent1_lemmas or not sent2_lemmas:
        return 0.0
    return len(sent1_lemmas.intersection(sent2_lemmas)) / len(sent1_lemmas.union(sent2_lemmas))

def generate_extractive_summary(filtered_sentences, keywords, num_sentences=4, lmbda=0.6):
    if not filtered_sentences:
        return ""
        
    keyword_weights = []
    for idx, kw in enumerate(keywords[:10]):
        weight = 10 - idx
        kw_lemmas = set(tokenize_lemmatized(kw))
        if kw_lemmas:
            keyword_weights.append((weight, kw_lemmas))
            
    candidates = []
    max_base_score = 0.0
    
    for orig_idx, sent_text in filtered_sentences:
        words = tokenize_raw(sent_text)
        if not words:
            continue
        sent_lemmas = set(tokenize_lemmatized(sent_text))
        
        raw_score = 0.0
        for weight, kw_lemmas in keyword_weights:
            overlap = len(kw_lemmas.intersection(sent_lemmas))
            match_score = overlap / len(kw_lemmas)
            raw_score += weight * match_score
            
        base_score = raw_score / (len(words) ** 0.5)
        candidates.append({
            "orig_idx": orig_idx,
            "text": sent_text,
            "lemmas": sent_lemmas,
            "base_score": base_score
        })
        if base_score > max_base_score:
            max_base_score = base_score
            
    if not candidates:
        return ""
        
    if max_base_score > 0:
        for c in candidates:
            c["norm_score"] = c["base_score"] / max_base_score
    else:
        for c in candidates:
            c["norm_score"] = 0.0
            
    selected = []
    while len(selected) < min(num_sentences, len(candidates)):
        best_mmr = -999999.0
        best_cand_idx = -1
        
        for i, c in enumerate(candidates):
            if not selected:
                max_sim = 0.0
            else:
                max_sim = max(compute_sentence_similarity(c["lemmas"], s["lemmas"]) for s in selected)
                
            mmr_score = lmbda * c["norm_score"] - (1 - lmbda) * max_sim
            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_cand_idx = i
                
        if best_cand_idx != -1:
            selected.append(candidates.pop(best_cand_idx))
        else:
            break
            
    selected.sort(key=lambda x: x["orig_idx"])
    return " ".join([s["text"] for s in selected])

def generate_and_evaluate_summaries(workspace_dir, max_articles=None):
    corpus_dir = os.path.join(workspace_dir, "corpus")
    summary_json_path = os.path.join(corpus_dir, "corpus.json")
    
    if not os.path.exists(summary_json_path):
        raise FileNotFoundError(f"Consolidated index '{summary_json_path}' not found.")
        
    print("Loading corpus index...")
    with open(summary_json_path, "r", encoding="utf-8") as jf:
        summary_data = json.load(jf)
        
    if max_articles is not None:
        summary_data = summary_data[:max_articles]
        
    def init_metric_accum():
        return {
            "raw": {
                "rouge1": {"p":[], "r":[], "f":[]},
                "rouge2": {"p":[], "r":[], "f":[]},
                "rougeL": {"p":[], "r":[], "f":[]}
            },
            "lemmatized": {
                "rouge1": {"p":[], "r":[], "f":[]},
                "rouge2": {"p":[], "r":[], "f":[]},
                "rougeL": {"p":[], "r":[], "f":[]}
            }
        }
        
    global_accum = {
        "tfidf": init_metric_accum(),
        "keybert": init_metric_accum()
    }
    
    def accumulate(accum, eval_result):
        for mode in ["raw", "lemmatized"]:
            for metric in ["rouge1", "rouge2", "rougeL"]:
                accum[mode][metric]["p"].append(eval_result[mode][metric]["precision"])
                accum[mode][metric]["r"].append(eval_result[mode][metric]["recall"])
                accum[mode][metric]["f"].append(eval_result[mode][metric]["f1"])
                
    summary_enriched = []
    
    for item in tqdm(summary_data, desc="Generating summaries & ROUGE"):
        filename = item["filename"]
        name_no_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(corpus_dir, f"{name_no_ext}.json")
        
        if not os.path.exists(json_path):
            continue
            
        with open(json_path, "r", encoding="utf-8") as ajf:
            art_data = json.load(ajf)
            
        main_text = art_data.get("main_text", "")
        author_annotation = art_data.get("annotation", "")
        keywords_tfidf = art_data.get("keywords_tfidf", [])
        keywords_keybert = art_data.get("keywords_keybert", [])
        
        all_sentences = split_sentences(main_text)
        filtered_sentences = filter_sentences(all_sentences)
        
        summary_tfidf = generate_extractive_summary(filtered_sentences, keywords_tfidf, num_sentences=4)
        summary_keybert = generate_extractive_summary(filtered_sentences, keywords_keybert, num_sentences=4)
        
        eval_tfidf = evaluate_summary(summary_tfidf, author_annotation)
        eval_keybert = evaluate_summary(summary_keybert, author_annotation)
        
        accumulate(global_accum["tfidf"], eval_tfidf)
        accumulate(global_accum["keybert"], eval_keybert)
        
        art_data["summarization"] = {
            "summary_tfidf": summary_tfidf,
            "summary_keybert": summary_keybert,
            "rouge_tfidf": eval_tfidf,
            "rouge_keybert": eval_keybert
        }
        
        with open(json_path, "w", encoding="utf-8") as ajf:
            json.dump(art_data, ajf, ensure_ascii=False, indent=2)
            
        summary_enriched.append({
            "filename": item["filename"],
            "title": item["title"],
            "authors": item.get("authors", []),
            "keywords": item["keywords"],
            "keywords_tfidf": item["keywords_tfidf"],
            "keywords_keybert": item["keywords_keybert"],
            "annotation": item["annotation"],
            "text_length": item["text_length"],
            "evaluation": item.get("evaluation", {}),
            "summarization": art_data["summarization"]
        })
        
    with open(summary_json_path, "w", encoding="utf-8") as jf:
        json.dump(summary_enriched, jf, ensure_ascii=False, indent=2)
        
    def calculate_averages(accum):
        averages = {}
        for mode in ["raw", "lemmatized"]:
            averages[mode] = {}
            for metric in ["rouge1", "rouge2", "rougeL"]:
                p_avg = sum(accum[mode][metric]["p"]) / len(accum[mode][metric]["p"]) if accum[mode][metric]["p"] else 0.0
                r_avg = sum(accum[mode][metric]["r"]) / len(accum[mode][metric]["r"]) if accum[mode][metric]["r"] else 0.0
                f_avg = sum(accum[mode][metric]["f"]) / len(accum[mode][metric]["f"]) if accum[mode][metric]["f"] else 0.0
                averages[mode][metric] = {"precision": p_avg, "recall": r_avg, "f1": f_avg}
        return averages
        
    avg_tfidf = calculate_averages(global_accum["tfidf"])
    avg_kb = calculate_averages(global_accum["keybert"])
    
    print("\n" + "="*80)
    print("                 GLOBAL EVALUATION REPORT (ROUGE METRICS)                 ")
    print("="*80)
    
    def print_mode_table(mode_name, tfidf_data, kb_data):
        print(f"\n[{mode_name.upper()} ROUGE SCORES]")
        print("-" * 75)
        print(f"{'Metric':<10} | {'TF-IDF Extractive':^28} | {'KeyBERT Extractive':^28}")
        print(f"{'':<10} | {'Prec.':^7} {'Rec.':^7} {'F1':^8} | {'Prec.':^7} {'Rec.':^7} {'F1':^8}")
        print("-" * 75)
        for m in ["rouge1", "rouge2", "rougeL"]:
            t_m = tfidf_data[m]
            k_m = kb_data[m]
            print(f"{m.upper():<10} | {t_m['precision']:6.2%} {t_m['recall']:6.2%} {t_m['f1']:7.2%} | {k_m['precision']:6.2%} {k_m['recall']:6.2%} {k_m['f1']:7.2%}")
        print("-" * 75)
        
    print_mode_table("Raw (Lexical)", avg_tfidf["raw"], avg_kb["raw"])
    print_mode_table("Lemmatized (Morphological)", avg_tfidf["lemmatized"], avg_kb["lemmatized"])
    print("\n--- Extractive Summarization and Evaluation Completed ---")

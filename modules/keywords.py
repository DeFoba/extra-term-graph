import os
import re
import json
import sys
import pymorphy3
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from keybert import KeyBERT

morph = pymorphy3.MorphAnalyzer()
lemma_cache = {}

ENGLISH_STOPWORDS = {
    'the', 'and', 'for', 'in', 'of', 'to', 'on', 'with', 'by', 'at', 'an', 'a', 'is', 'it', 'from', 'as', 'that', 'this', 'are', 'be'
}

RUSSIAN_STOPWORDS = {
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 
    'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 
    'о', 'из', 'ему', 'им', 'кто', 'этого', 'ней', 'хотя', 'после', 'эту', 'над', 'нее', 'вас', 'дом', 'этой', 'под', 
    'будет', 'этом', 'себя', 'свое', 'неё', 'моя', 'был', 'при', 'чтобы', 'всего', 'них', 'всех', 'ею', 'ныне', 'тому', 
    'себе', 'тебе', 'тем', 'нам', 'ими', 'мы', 'вы', 'они', 'их', 'кто', 'что', 'какой', 'чей', 'тот', 'этот', 'каждый', 
    'другой', 'все', 'весь', 'сам', 'самый', 'наш', 'ваш', 'свой', 'один', 'два', 'три', 'четыре', 'пять', 'первый', 
    'второй', 'третий', 'около', 'через', 'вдоль', 'сквозь', 'внутрь', 'внутри', 'вне', 'перед', 'пред', 'над', 'под', 
    'из-за', 'из-под', 'без', 'безо', 'кроме', 'для', 'ради', 'посредством', 'путем', 'ввиду', 'вследствие', 'благодаря', 
    'согласно', 'вопреки', 'навстречу', 'включая', 'исключая', 'спустя', 'касаемо', 'относительно', 'который', 'такой', 'мочь',
    'статья', 'работа', 'результат', 'исследование', 'автор', 'рисунок', 'таблица', 'раздел', 'метод', 'система', 
    'процесс', 'использование', 'основа', 'анализ', 'разработка', 'цель', 'задача', 'построение', 'применение', 
    'направление', 'область', 'свойство', 'данные', 'решение', 'вопрос', 'подход', 'оценка', 'значение', 'число', 
    'случай', 'представление', 'управление', 'описание', 'возможность', 'качество', 'условие', 'модель', 'структура',
    'рассмотрение', 'определение', 'раздел', 'пример', 'сведения', 'получение', 'предложение', 'режим', 'вывод',
    'правило', 'понятие', 'описание', 'основа', 'проблема', 'зависимость', 'действие', 'изменение', 'состояние',
    'проект', 'технология', 'субъект', 'объект', 'уровень', 'факт', 'текст', 'городской', 'знак', 'элемент', 
    'деятельность', 'группа', 'время', 'место', 'знаковый', 'товар', 'оборудование', 'наличие', 'реальный', 
    'известный', 'достаточно', 'цепочка', 'форма', 'объединение', 'множество', 'ситуация', 'введение', 
    'следующий', 'последующий', 'аналогичный', 'подготовка', 'команда', 'составлять', 'впечатляющий', 
    'поддержка', 'принятие', 'основать'
}

def is_valid_keyword(phrase):
    words = phrase.split()
    if not words:
        return False
        
    for i, w in enumerate(words):
        w_clean = w.strip().lower()
        if len(w_clean) < 3:
            return False
            
        if not re.match(r'^[а-яёa-z\-]+$', w_clean):
            return False
            
        if w_clean in RUSSIAN_STOPWORDS or w_clean in ENGLISH_STOPWORDS:
            return False
            
        parsed = morph.parse(w_clean)[0]
        pos = parsed.tag.POS
        
        disallowed_pos = {'VERB', 'INFN', 'PRTS', 'GRND', 'PRED', 'NPRO', 'PREP', 'CONJ', 'PRCL'}
        if pos in disallowed_pos:
            return False
            
        if len(words) > 1 and i == len(words) - 1:
            if pos in {'ADJF', 'ADJS', 'COMP'}:
                return False
                
    return True

def lemmatize_text(text):
    text = text.lower()
    text = re.sub(r'[^а-яё\- ]', ' ', text)
    tokens = text.split()
    
    lemmatized_tokens = []
    for t in tokens:
        if len(t) < 3:
            continue
        t = t.strip('-')
        if not t:
            continue
            
        if t not in lemma_cache:
            parsed = morph.parse(t)[0]
            pos = parsed.tag.POS
            if pos in {'NPRO', 'PREP', 'CONJ', 'PRCL', 'INTJ'}:
                lemma_cache[t] = None
            else:
                lemma_cache[t] = parsed.normal_form
                
        lemma = lemma_cache[t]
        if lemma and lemma not in RUSSIAN_STOPWORDS:
            if len(lemma) <= 3:
                if not any(c in 'аоуыэяеёюиaeiouy' for c in lemma.lower()):
                    continue
            lemmatized_tokens.append(lemma)
            
    return " ".join(lemmatized_tokens)

def normalize_phrase(phrase):
    if not phrase:
        return ""
    phrase = phrase.lower()
    words = re.findall(r'[а-яёa-z]+', phrase)
    
    normalized_words = []
    for w in words:
        if w not in lemma_cache:
            parsed = morph.parse(w)[0]
            lemma_cache[w] = parsed.normal_form
        lemma = lemma_cache[w]
        if lemma:
            normalized_words.append(lemma)
        
    return " ".join(sorted(normalized_words))

def compute_jaccard_similarity(phrase1, phrase2):
    tokens1 = set(phrase1.split())
    tokens2 = set(phrase2.split())
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1.intersection(tokens2)) / len(tokens1.union(tokens2))

def compute_exact_metrics(extracted_list, author_set, k):
    if not author_set:
        return 0.0, 0.0, 0.0
    extracted_k = extracted_list[:k]
    if not extracted_k:
        return 0.0, 0.0, 0.0
        
    matches = sum(1 for kw in extracted_k if kw in author_set)
    precision = matches / len(extracted_k)
    recall = matches / len(author_set)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def compute_soft_metrics(extracted_list, author_list, k):
    if not author_list:
        return 0.0, 0.0, 0.0
    extracted_k = extracted_list[:k]
    if not extracted_k:
        return 0.0, 0.0, 0.0
        
    precision_sum = 0.0
    for ext_kw in extracted_k:
        best_sim = max(compute_jaccard_similarity(ext_kw, auth_kw) for auth_kw in author_list)
        precision_sum += best_sim
    precision = precision_sum / len(extracted_k)
    
    recall_sum = 0.0
    for auth_kw in author_list:
        best_sim = max(compute_jaccard_similarity(ext_kw, auth_kw) for auth_kw in extracted_k)
        recall_sum += best_sim
    recall = recall_sum / len(author_list)
    
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1

def extract_and_evaluate_keywords(workspace_dir, model_name='mlsa-iai-msu-lab/sci-rus-tiny', max_articles=None):
    corpus_dir = os.path.join(workspace_dir, "corpus")
    summary_json_path = os.path.join(workspace_dir, "corpus.json")
    
    if not os.path.exists(summary_json_path):
        raise FileNotFoundError(f"Consolidated index '{summary_json_path}' not found.")
        
    print("Loading corpus index...")
    with open(summary_json_path, "r", encoding="utf-8") as jf:
        summary_data = json.load(jf)
        
    if max_articles is not None:
        summary_data = summary_data[:max_articles]
        
    articles = []
    lemmatized_corpus = []
    
    for item in tqdm(summary_data, desc="Lemmatizing corpus for TF-IDF"):
        filename = item["filename"]
        name_no_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(corpus_dir, f"{name_no_ext}.json")
        
        if not os.path.exists(json_path):
            continue
            
        with open(json_path, "r", encoding="utf-8") as ajf:
            art_data = json.load(ajf)
            
        articles.append(art_data)
        lemmatized_corpus.append(lemmatize_text(art_data.get("main_text", "")))
        
    print("\nFitting TF-IDF Vectorizer...")
    min_df = min(2, len(lemmatized_corpus))
    max_df = 1.0 if len(lemmatized_corpus) < 3 else 0.85
    vectorizer = TfidfVectorizer(max_df=max_df, min_df=min_df)
    tfidf_matrix = vectorizer.fit_transform(lemmatized_corpus)
    feature_names = vectorizer.get_feature_names_out()
    
    for idx, art_data in enumerate(articles):
        row = tfidf_matrix[idx].toarray()[0]
        top_indices = row.argsort()[::-1][:30]
        keywords_tfidf = []
        for i in top_indices:
            if row[i] <= 0:
                continue
            kw = feature_names[i]
            if is_valid_keyword(kw):
                keywords_tfidf.append(kw)
                if len(keywords_tfidf) >= 10:
                    break
        art_data["keywords_tfidf"] = keywords_tfidf
        
    print(f"\nLoading KeyBERT with '{model_name}'...")
    kw_model = KeyBERT(model=model_name)
    stopwords_list = list(RUSSIAN_STOPWORDS)
    
    for art_data in tqdm(articles, desc="KeyBERT inference"):
        text_chunk = art_data.get("main_text", "")[:5000]
        try:
            extracted = kw_model.extract_keywords(
                text_chunk,
                keyphrase_ngram_range=(1, 2),
                stop_words=stopwords_list,
                top_n=25,
                use_mmr=True,
                diversity=0.55
            )
            keywords_kb = []
            for item in extracted:
                kw = item[0].lower().strip()
                if is_valid_keyword(kw):
                    is_redundant = False
                    for existing in keywords_kb:
                        if kw in existing or existing in kw:
                            is_redundant = True
                            break
                    if not is_redundant:
                        keywords_kb.append(kw)
                        if len(keywords_kb) >= 10:
                            break
        except Exception:
            keywords_kb = []
            
        art_data["keywords_keybert"] = keywords_kb
        
    print("\nEvaluating keyword quality...")
    
    accum = {
        "tfidf": {"exact_5": [], "exact_10": [], "soft_5": [], "soft_10": []},
        "keybert": {"exact_5": [], "exact_10": [], "soft_5": [], "soft_10": []}
    }
    
    for art_data in articles:
        author_raw = art_data.get("keywords", [])
        author_norm = [normalize_phrase(kw) for kw in author_raw]
        author_set = set(author_norm)
        
        tfidf_norm = [normalize_phrase(kw) for kw in art_data.get("keywords_tfidf", [])]
        kb_norm = [normalize_phrase(kw) for kw in art_data.get("keywords_keybert", [])]
        
        e5_p, e5_r, e5_f = compute_exact_metrics(tfidf_norm, author_set, 5)
        e10_p, e10_r, e10_f = compute_exact_metrics(tfidf_norm, author_set, 10)
        s5_p, s5_r, s5_f = compute_soft_metrics(tfidf_norm, author_norm, 5)
        s10_p, s10_r, s10_f = compute_soft_metrics(tfidf_norm, author_norm, 10)
        
        accum["tfidf"]["exact_5"].append((e5_p, e5_r, e5_f))
        accum["tfidf"]["exact_10"].append((e10_p, e10_r, e10_f))
        accum["tfidf"]["soft_5"].append((s5_p, s5_r, s5_f))
        accum["tfidf"]["soft_10"].append((s10_p, s10_r, s10_f))
        
        k5_p, k5_r, k5_f = compute_exact_metrics(kb_norm, author_set, 5)
        k10_p, k10_r, k10_f = compute_exact_metrics(kb_norm, author_set, 10)
        ks5_p, ks5_r, ks5_f = compute_soft_metrics(kb_norm, author_norm, 5)
        ks10_p, ks10_r, ks10_f = compute_soft_metrics(kb_norm, author_norm, 10)
        
        accum["keybert"]["exact_5"].append((k5_p, k5_r, k5_f))
        accum["keybert"]["exact_10"].append((k10_p, k10_r, k10_f))
        accum["keybert"]["soft_5"].append((ks5_p, ks5_r, ks5_f))
        accum["keybert"]["soft_10"].append((ks10_p, ks10_r, ks10_f))
        
        art_data["evaluation"] = {
            "tfidf": {
                "exact": {"precision_at_5": e5_p, "recall_at_5": e5_r, "f1_at_5": e5_f, "precision_at_10": e10_p, "recall_at_10": e10_r, "f1_at_10": e10_f},
                "soft": {"precision_at_5": s5_p, "recall_at_5": s5_r, "f1_at_5": s5_f, "precision_at_10": s10_p, "recall_at_10": s10_r, "f1_at_10": s10_f}
            },
            "keybert": {
                "exact": {"precision_at_5": k5_p, "recall_at_5": k5_r, "f1_at_5": k5_f, "precision_at_10": k10_p, "recall_at_10": k10_r, "f1_at_10": k10_f},
                "soft": {"precision_at_5": ks5_p, "recall_at_5": ks5_r, "f1_at_5": ks5_f, "precision_at_10": ks10_p, "recall_at_10": ks10_r, "f1_at_10": ks10_f}
            }
        }
        
    summary_enriched = []
    for art_data in articles:
        filename = art_data["filename"]
        name_no_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(corpus_dir, f"{name_no_ext}.json")
        
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(art_data, jf, ensure_ascii=False, indent=2)
            
        summary_enriched.append({
            "filename": art_data["filename"],
            "title": art_data["title"],
            "keywords": art_data["keywords"],
            "keywords_tfidf": art_data["keywords_tfidf"],
            "keywords_keybert": art_data["keywords_keybert"],
            "annotation": art_data["annotation"],
            "text_length": len(art_data["main_text"]),
            "evaluation": art_data["evaluation"]
        })
        
    with open(summary_json_path, "w", encoding="utf-8") as jf:
        json.dump(summary_enriched, jf, ensure_ascii=False, indent=2)
        
    def get_avg(metric_list):
        p_avg = sum(x[0] for x in metric_list) / len(metric_list)
        r_avg = sum(x[1] for x in metric_list) / len(metric_list)
        f_avg = sum(x[2] for x in metric_list) / len(metric_list)
        return p_avg, r_avg, f_avg
        
    print("\n" + "="*80)
    print("                 GLOBAL KEYWORD MATCHING PERFORMANCE REPORT               ")
    print("="*80)
    
    def print_method_table(method_name, data):
        print(f"\n[{method_name.upper()} KEYWORDS MATCHES]")
        print("-" * 75)
        print(f"{'Metric':<15} | {'TF-IDF Extractive':^26} | {'KeyBERT Extractive':^26}")
        print(f"{'':<15} | {'Prec.':^6} {'Rec.':^6} {'F1':^7} | {'Prec.':^6} {'Rec.':^6} {'F1':^7}")
        print("-" * 75)
        for k in ["5", "10"]:
            t_p, t_r, t_f = get_avg(data["tfidf"][f"{method_name}_{k}"])
            k_p, k_r, k_f = get_avg(data["keybert"][f"{method_name}_{k}"])
            print(f"{'Top ' + k:<15} | {t_p:5.2%} {t_r:5.2%} {t_f:6.2%} | {k_p:5.2%} {k_r:5.2%} {k_f:6.2%}")
        print("-" * 75)
        
    print_method_table("exact", accum)
    print_method_table("soft", accum)
    
    print("\n--- Keyword Extraction and Evaluation Completed ---")

import os

def get_content():
    blocks = []
    blocks.append({"type": "h1", "text": "ПРИЛОЖЕНИЯ"})
    blocks.append({"type": "h2", "text": "Приложение А. Листинг модуля сборки корпуса (corpus.py, фрагмент)"})

    code_corpus = '''import os
import re
import json
import fitz  # PyMuPDF
import pymorphy3

morph = pymorphy3.MorphAnalyzer()

def extract_text_from_pdf(pdf_path):
    """Извлекает текст из PDF, обрезая колонтитулы."""
    doc = fitz.open(pdf_path)
    full_text = []
    for page in doc:
        page_height = page.rect.height
        margin_top = page_height * 0.05
        margin_bottom = page_height * 0.95
        blocks = page.get_text("blocks")
        for block in blocks:
            x0, y0, x1, y1, text, *_ = block
            if y0 >= margin_top and y1 <= margin_bottom:
                full_text.append(text.strip())
    doc.close()
    return "\\n".join(full_text)

def fix_hyphenation_pymorphy(text, morph):
    """Интеллектуальная склейка дефисных переносов."""
    lines = text.split("\\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1].lstrip()
            if next_line:
                next_word = next_line.split()[0]
                prefix = line[:-1].split()[-1] if line[:-1].split() else ""
                merged = prefix + next_word
                parsed = morph.parse(merged)
                if parsed and parsed[0].score > 0:
                    before = " ".join(line[:-1].split()[:-1])
                    rest = " ".join(next_line.split()[1:])
                    line = f"{before} {merged}".strip()
                    lines[i + 1] = rest
        result.append(line)
        i += 1
    return "\\n".join(result)

def is_text_readable(text):
    """Проверяет, что текст не содержит мусорных символов."""
    if not text:
        return False
    printable = sum(1 for c in text if c.isprintable() or c in "\\n\\r\\t")
    return printable / len(text) > 0.7

def is_russian_text(text):
    """Проверяет, что текст преимущественно на русском языке."""
    sample = text[:2000]
    cyrillic = sum(1 for c in sample if "\\u0400" <= c <= "\\u04FF")
    latin = sum(1 for c in sample if "A" <= c <= "z")
    return cyrillic > latin

def build_corpus(workspace_dir, max_articles=None):
    """Основная функция: обходит PDF-файлы и формирует JSON."""
    articles_dir = os.path.join(workspace_dir, "articles")
    corpus = []
    for filename in sorted(os.listdir(articles_dir)):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(articles_dir, filename)
        raw_text = extract_text_from_pdf(pdf_path)
        clean_text = fix_hyphenation_pymorphy(raw_text, morph)
        if not is_text_readable(clean_text):
            continue
        if not is_russian_text(clean_text):
            continue
        article = parse_article_structure(clean_text, filename)
        corpus.append(article)
        if max_articles and len(corpus) >= max_articles:
            break
    out_path = os.path.join(workspace_dir, "corpus", "corpus.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
    return corpus'''

    blocks.append({"type": "p", "text": code_corpus, "indent": None})

    blocks.append({"type": "h2", "text": "Приложение Б. Листинг модуля извлечения ключевых слов (keywords.py, фрагмент)"})

    code_keywords = '''import re
import json
import pymorphy3
from sklearn.feature_extraction.text import TfidfVectorizer
from keybert import KeyBERT

morph = pymorphy3.MorphAnalyzer()
lemma_cache = {}

RUSSIAN_STOPWORDS = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со",
    "как", "а", "то", "все", "она", "так", "его", "но", "да",
    "ты", "к", "у", "же", "вы", "за", "бы", "по", "только",
    "статья", "работа", "результат", "исследование", "автор",
    "метод", "система", "процесс", "использование", "основа",
    "анализ", "разработка", "цель", "задача", "данные"
}

def lemmatize_word(word):
    """Лемматизация одного слова с кэшированием."""
    if word in lemma_cache:
        return lemma_cache[word]
    parsed = morph.parse(word)[0]
    lemma = parsed.normal_form
    lemma_cache[word] = lemma
    return lemma

def lemmatize_text(text):
    """Лемматизация полного текста."""
    words = re.findall(r"[а-яёa-z]+", text.lower())
    lemmas = []
    for w in words:
        if len(w) < 3 or w in RUSSIAN_STOPWORDS:
            continue
        lemma = lemmatize_word(w)
        if lemma not in RUSSIAN_STOPWORDS:
            lemmas.append(lemma)
    return " ".join(lemmas)

def extract_tfidf_keywords(corpus_texts, top_n=10):
    """Извлечение TF-IDF ключевых слов из корпуса."""
    lemmatized = [lemmatize_text(t) for t in corpus_texts]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_df=0.85,
        min_df=1,
        max_features=5000,
        sublinear_tf=True
    )
    tfidf_matrix = vectorizer.fit_transform(lemmatized)
    feature_names = vectorizer.get_feature_names_out()
    results = []
    for i in range(len(corpus_texts)):
        row = tfidf_matrix[i].toarray().flatten()
        top_indices = row.argsort()[-top_n:][::-1]
        keywords = [(feature_names[j], float(row[j])) for j in top_indices]
        results.append(keywords)
    return results

def extract_keybert_keywords(texts, top_n=10):
    """Извлечение KeyBERT ключевых слов с диверсификацией MMR."""
    kw_model = KeyBERT(model="mlsa-iai-msu-lab/sci-rus-tiny")
    results = []
    for text in texts:
        kws = kw_model.extract_keywords(
            text, keyphrase_ngram_range=(1, 2),
            stop_words=None, top_n=top_n,
            use_mmr=True, diversity=0.7
        )
        results.append(kws)
    return results

def soft_match(kw1, kw2, threshold=0.5):
    """Нечеткое сравнение по Jaccard >= threshold."""
    s1 = set(lemmatize_word(w) for w in kw1.lower().split())
    s2 = set(lemmatize_word(w) for w in kw2.lower().split())
    if not s1 or not s2:
        return False
    jaccard = len(s1 & s2) / len(s1 | s2)
    return jaccard >= threshold'''

    blocks.append({"type": "p", "text": code_keywords, "indent": None})

    blocks.append({"type": "h2", "text": "Приложение В. Листинг модуля реферирования (summarization.py, фрагмент)"})

    code_summarization = '''import nltk
from nltk.tokenize import sent_tokenize

def sentence_weight(sentence, keywords_with_weights):
    """Вычисляет вес предложения как сумму весов терминов."""
    words = set(lemmatize_text(sentence).split())
    weight = 0.0
    for kw, w in keywords_with_weights:
        kw_lemmas = set(lemmatize_text(kw).split())
        if kw_lemmas & words:
            weight += w
    return weight

def jaccard_similarity(sent1, sent2):
    """Коэффициент Жаккара между двумя предложениями."""
    s1 = set(lemmatize_text(sent1).split())
    s2 = set(lemmatize_text(sent2).split())
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)

def extract_sentences_mmr(text, keywords_with_weights,
                          n_sentences=5, lambda_param=0.7):
    """MMR-реферирование: выбор топ-N предложений."""
    sentences = sent_tokenize(text)
    sentences = [s for s in sentences if len(s) > 20]
    if len(sentences) <= n_sentences:
        return sentences
    
    weights = {s: sentence_weight(s, keywords_with_weights)
               for s in sentences}
    selected = []
    remaining = list(sentences)
    
    while len(selected) < n_sentences and remaining:
        best_score = -float("inf")
        best_sent = None
        for candidate in remaining:
            relevance = weights[candidate]
            if selected:
                redundancy = max(
                    jaccard_similarity(candidate, s)
                    for s in selected
                )
            else:
                redundancy = 0.0
            mmr = lambda_param * relevance - \\
                  (1 - lambda_param) * redundancy
            if mmr > best_score:
                best_score = mmr
                best_sent = candidate
        if best_sent:
            selected.append(best_sent)
            remaining.remove(best_sent)
    
    # Восстанавливаем оригинальный порядок
    selected.sort(key=lambda s: text.index(s))
    return selected'''

    blocks.append({"type": "p", "text": code_summarization, "indent": None})

    return blocks

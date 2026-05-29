import os
import re
import json
import fitz
from tqdm import tqdm

def is_text_readable(text, threshold=0.75):
    """Check if text is mostly readable (not garbled encoding).
    Returns True if at least `threshold` fraction of chars are valid
    Cyrillic/Latin letters, digits, whitespace, or common punctuation.
    """
    if not text or len(text) < 100:
        return False
    valid_chars = 0
    for ch in text:
        if ('\u0400' <= ch <= '\u04FF' or  # Cyrillic
            'a' <= ch <= 'z' or 'A' <= ch <= 'Z' or
            '0' <= ch <= '9' or
            ch in ' \t\n\r.,;:!?()-"\'/[]{}+=<>@#$%&*_~\\'):
            valid_chars += 1
    ratio = valid_chars / len(text)
    return ratio >= threshold

def is_title_valid(title):
    """Check if the title is readable and meaningful (not garbled)."""
    if not title or len(title) < 3:
        return False
    # Title should contain real Cyrillic or Latin words (3+ letters in a row)
    words = re.findall(r'[а-яёА-ЯЁ]{3,}|[a-zA-Z]{3,}', title)
    if len(words) < 1:
        return False
    # Check readability of the title itself
    valid_chars = 0
    for ch in title:
        if ('\u0400' <= ch <= '\u04FF' or
            'a' <= ch <= 'z' or 'A' <= ch <= 'Z' or
            '0' <= ch <= '9' or
            ch in ' .,;:!?()-"\'/'):
            valid_chars += 1
    if len(title) > 0 and valid_chars / len(title) < 0.7:
        return False
    return True

def is_russian_text(text, threshold=0.5):
    """Check if text is predominantly Russian.
    Returns True if at least `threshold` fraction of letter characters are Cyrillic.
    """
    if not text:
        return False
    cyrillic = 0
    latin = 0
    for ch in text:
        if '\u0400' <= ch <= '\u04FF':
            cyrillic += 1
        elif ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'):
            latin += 1
    total_letters = cyrillic + latin
    if total_letters == 0:
        return False
    return (cyrillic / total_letters) >= threshold

def resolve_hyphenation(part1, part2):
    combined_no = part1 + part2
    combined_with = part1 + "-" + part2
    
    is_russian = all(
        'а' <= c.lower() <= 'я' or c.lower() == 'ё' 
        for c in part1 + part2
    )
    
    if is_russian:
        p1_lower = part1.lower()
        if p1_lower.endswith(('о', 'е')) and len(part1) >= 4 and len(part2) >= 5:
            return combined_with
        hyphen_prefixes = {'интернет', 'веб', 'бизнес', 'мини', 'микро', 'макро', 'вице', 'экс'}
        if p1_lower in hyphen_prefixes:
            return combined_with
        return combined_no
    else:
        p1_lower = part1.lower()
        prefixes = {'multi', 'anti', 'sub', 'co', 'non', 'pre', 'post', 'micro', 'macro', 'semi', 'self'}
        if p1_lower in prefixes:
            return part1 + "-" + part2
        return part1 + part2

def clean_and_resolve_hyphens(text):
    def repl(match):
        return resolve_hyphenation(match.group(1), match.group(2))
    return re.sub(r'(\b[а-яА-ЯёЁa-zA-Z]+)-\s*\n\s*([а-яА-ЯёЁa-zA-Z]+)', repl, text)

def normalize_text_spacing(text):
    if not text:
        return ""
    text = re.sub(r'\n\s*\n', '@@PARAGRAPH@@', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('@@PARAGRAPH@@', '\n\n')
    return "\n\n".join(p.strip() for p in text.split('\n\n') if p.strip())

def extract_authors(title_metadata):
    """Extract author names from the title_metadata block (text before 'Аннотация').
    Authors are identified by lines containing patterns like 'А.Б. Фамилия' or 'A.B. Surname'.
    """
    if not title_metadata:
        return []
    lines = [line.strip() for line in title_metadata.split("\n") if line.strip()]
    authors = []
    # Pattern: one or more author names with initials — Cyrillic or Latin
    # e.g. "Л.В. Аршинский, В.Л. Аршинский" or "A.V. Smirnov, T.V. Levashova"
    initials_pattern = re.compile(
        r'[А-ЯЁA-Z]\s*\.\s*[А-ЯЁA-Z]\s*\.'
    )
    for line in lines:
        line_lower = line.lower()
        # Skip known non-author lines
        if any(x in line_lower for x in [
            "удк", "doi:", "doi.org", "научная статья", "научный доклад",
            "©", "copyright", "@", "цитирование:", "http",
            "университет", "институт", "академия", "ооо", "оао",
            "филиал", "научный центр", "г. рождения",
            "orcid", "researcher", "spin",
            "россия", "russia", "москва", "moscow",
            "самара", "samara", "минск", "minsk",
        ]):
            continue
        # Must contain initials pattern
        if not initials_pattern.search(line):
            continue
        # Additional check: line should not be too long (likely a sentence, not authors)
        if len(line) > 200:
            continue
        # Clean up: remove superscript digits and extra whitespace
        clean_line = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰]+', '', line)
        clean_line = re.sub(r'\d+(?=[А-ЯЁA-Z])', '', clean_line)  # "1А." → "А."
        clean_line = re.sub(r'\s+', ' ', clean_line).strip()
        if clean_line:
            # Split by comma to get individual authors
            parts = re.split(r'\s*,\s*', clean_line)
            for part in parts:
                part = part.strip()
                if part and initials_pattern.search(part) and len(part) > 3:
                    # Remove trailing commas, periods and underscores
                    part = part.replace('_', ' ')
                    part = re.sub(r'\s+', ' ', part).strip(' ,.')
                    if part:
                        authors.append(part)
    return authors

def extract_title(title_metadata, filename):
    default_title = os.path.splitext(filename)[0].replace("_", " ")
    if not title_metadata:
        return default_title
        
    lines = [line.strip() for line in title_metadata.split("\n") if line.strip()]
    filtered_lines = []
    
    for line in lines:
        line_lower = line.lower()
        if any(x in line_lower for x in ["удк", "doi:", "doi.org", "научная статья", "научный доклад", "©", "copyright"]):
            continue
        affiliations = ["университет", "институт", "академия", "ооо", "оао", "филиал", "научный центр", "г. рождения", " lobach"]
        if any(aff in line_lower for aff in affiliations):
            continue
        if "@" in line_lower or "цитирование:" in line_lower:
            continue
        if len(line) < 10:
            continue
        filtered_lines.append(line)
        
    if filtered_lines:
        return filtered_lines[0]
    return default_title

def clean_keywords(keywords_str):
    if not keywords_str:
        return []
    keywords_str = keywords_str.replace("\n", " ")
    cleaned = keywords_str.strip().rstrip('.')
    raw_list = re.split(r'[,;]\s*', cleaned)
    
    filtered = []
    for k in raw_list:
        kw = re.sub(r'\s+', ' ', k.strip().lower())
        if not kw:
            continue
        if len(kw) > 60 or len(kw.split()) > 6:
            continue
        if any(x in kw for x in ['doi:', 'цитирование:', 'http', '//', 'т. ', '№', ' c. ', ' с. ', '________________']):
            continue
        filtered.append(kw)
    return filtered

def process_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {"error": f"Failed to open PDF: {str(e)}"}
        
    filtered_blocks = []
    for page in doc:
        blocks = page.get_text("blocks")
        for b in blocks:
            x0, y0, x1, y1, block_text, block_no, block_type = b
            if y0 < 70 or y1 > 755:
                continue
            filtered_blocks.append(block_text)
            
    if not filtered_blocks:
        return {"error": "No text content found after filtering headers/footers"}
        
    full_text = "\n\n".join(filtered_blocks)
    full_text = clean_and_resolve_hyphens(full_text)
    
    m_annot_ru = re.search(r'\bаннотация\b', full_text, re.IGNORECASE)
    m_keys_ru = re.search(r'\bключевые\s+слова\b', full_text, re.IGNORECASE)
    
    is_english_article_with_russian_summary = False
    if m_annot_ru and m_keys_ru:
        m_annot_en = re.search(r'\babstract\b', full_text, re.IGNORECASE)
        m_keys_en = re.search(r'\bkeywords\b|\bkey\s+words\b', full_text, re.IGNORECASE)
        if m_annot_ru.start() > 0.5 * len(full_text) and m_annot_en and m_annot_en.start() < 0.3 * len(full_text):
            is_english_article_with_russian_summary = True
            
    if is_english_article_with_russian_summary:
        idx_annot_en = m_annot_en.start()
        title_metadata = full_text[:idx_annot_en].strip()
        title = extract_title(title_metadata, filename)
        authors = extract_authors(title_metadata)
        
        idx_annot_ru = m_annot_ru.start()
        idx_keys_ru = m_keys_ru.start()
        
        raw_annotation = full_text[idx_annot_ru + len(m_annot_ru.group(0)):idx_keys_ru].strip()
        annotation = re.sub(r'^[:\s\-\.]+', '', raw_annotation).strip()
        annotation = normalize_text_spacing(annotation)
        
        if m_keys_en:
            idx_body_start_candidate = m_keys_en.start() + len(m_keys_en.group(0))
        else:
            idx_body_start_candidate = idx_annot_en + 100
            
        body_patterns = [r'\bintroduction\b', r'\bвведение\b', r'^\s*1\s+[a-zA-Z]+']
        all_body_markers = []
        for pat in body_patterns:
            flags = re.IGNORECASE | re.MULTILINE if '^' in pat else re.IGNORECASE
            for m in re.finditer(pat, full_text, flags):
                if m.start() > idx_body_start_candidate:
                    all_body_markers.append(m.start())
                    
        if all_body_markers:
            idx_body_start = min(all_body_markers)
        else:
            idx_body_start = full_text.find("\n", idx_body_start_candidate + 100)
            if idx_body_start == -1:
                idx_body_start = idx_body_start_candidate + 100
                
        idx_body_end = idx_annot_ru
        
        ref_patterns_ru = [
            r'^\s*список\s+источников\s*$',
            r'^\s*список\s+использованной\s+литературы\s*$',
            r'^\s*список\s+литературы\s*$',
            r'^\s*литература\s*$',
            r'^\s*references\s*$',
            r'сведения\s+об\s+авторах',
            r'about\s+the\s+authors'
        ]
        keywords_end_markers = []
        for pat in ref_patterns_ru:
            for m in re.finditer(pat, full_text, re.IGNORECASE | re.MULTILINE):
                if m.start() > idx_keys_ru:
                    keywords_end_markers.append(m.start())
                    
        if keywords_end_markers:
            idx_keywords_end = min(keywords_end_markers)
        else:
            idx_keywords_end = full_text.find("\n", idx_keys_ru + 150)
            if idx_keywords_end == -1:
                idx_keywords_end = idx_keys_ru + 150
                
        raw_keywords = full_text[idx_keys_ru + len(m_keys_ru.group(0)):idx_keywords_end].strip()
        keywords_str = re.sub(r'^[:\s\-\.]+', '', raw_keywords).strip()
        keywords_list = clean_keywords(keywords_str)
        
        main_text = full_text[idx_body_start:idx_body_end].strip()
        m_intro = re.search(r'^\s*(?:\d+[\s\.\-]+)?introduction\b', main_text, re.IGNORECASE | re.MULTILINE)
        if m_intro:
            main_text = main_text[m_intro.start():].strip()
        else:
            m_intro_early = re.search(r'\bintroduction\b', main_text[:1500], re.IGNORECASE)
            if m_intro_early:
                main_text = main_text[m_intro_early.start():].strip()
        main_text = normalize_text_spacing(main_text)
        
    else:
        # --- Best-effort extraction for articles with missing/malformed markers ---
        has_standard_structure = (m_annot_ru and m_keys_ru and 
                                  m_keys_ru.start() > m_annot_ru.start())
        
        if has_standard_structure:
            # === Standard path: both markers in correct order ===
            idx_annot_start = m_annot_ru.start()
            idx_keys_start = m_keys_ru.start()
            
            title_metadata = full_text[:idx_annot_start].strip()
            title = extract_title(title_metadata, filename)
            authors = extract_authors(title_metadata)
            
            raw_annotation = full_text[idx_annot_start + len(m_annot_ru.group(0)):idx_keys_start].strip()
            annotation = re.sub(r'^[:\s\-\.]+', '', raw_annotation).strip()
            annotation = normalize_text_spacing(annotation)
            
            body_patterns = [
                r'\bвведение\b', 
                r'\bцитирование\b', 
                r'\bдля\s+цитирования\b', 
                r'\bконфликт\s+интересов\b',
                r'^\s*1\s+[а-яА-Яa-zA-Z]+'
            ]
            all_body_markers = []
            for pat in body_patterns:
                flags = re.IGNORECASE | re.MULTILINE if '^' in pat else re.IGNORECASE
                for m in re.finditer(pat, full_text, flags):
                    if m.start() > idx_keys_start:
                        all_body_markers.append(m.start())
                        
            if all_body_markers:
                idx_body_start = min(all_body_markers)
            else:
                idx_body_start = full_text.find("\n", idx_keys_start + 150)
                if idx_body_start == -1:
                    idx_body_start = idx_keys_start + 150
                    
            raw_keywords = full_text[idx_keys_start + len(m_keys_ru.group(0)):idx_body_start].strip()
            keywords_str = re.sub(r'^[:\s\-\.]+', '', raw_keywords).strip()
            keywords_list = clean_keywords(keywords_str)
            
            ref_patterns = [
                r'^\s*список\s+источников\s*$',
                r'^\s*список\s+использованной\s+литературы\s*$',
                r'^\s*список\s+литературы\s*$',
                r'^\s*литература\s*$',
                r'^\s*references\s*$'
            ]
            ref_starts = []
            for pat in ref_patterns:
                for m in re.finditer(pat, full_text, re.IGNORECASE | re.MULTILINE):
                    if m.start() > idx_body_start:
                        ref_starts.append(m.start())
                        
            if ref_starts:
                idx_ref_start = min(ref_starts)
            else:
                idx_ref_start = len(full_text)
                
            main_text = full_text[idx_body_start:idx_ref_start].strip()
            m_intro = re.search(r'^\s*(?:\d+[\s\.\-]+)?введение\b', main_text, re.IGNORECASE | re.MULTILINE)
            if m_intro:
                main_text = main_text[m_intro.start():].strip()
            else:
                m_intro_early = re.search(r'\bвведение\b', main_text[:1500], re.IGNORECASE)
                if m_intro_early:
                    main_text = main_text[m_intro_early.start():].strip()
            main_text = normalize_text_spacing(main_text)
            
        else:
            # === Fallback path: missing or malformed markers ===
            # Try English markers first
            m_abstract = re.search(r'\babstract\b', full_text, re.IGNORECASE)
            m_keywords_en = re.search(r'\bkeywords\b|\bkey\s+words\b', full_text, re.IGNORECASE)
            
            if m_abstract and m_keywords_en and m_keywords_en.start() > m_abstract.start():
                # English structure found
                title_metadata = full_text[:m_abstract.start()].strip()
                title = extract_title(title_metadata, filename)
                authors = extract_authors(title_metadata)
                
                raw_annotation = full_text[m_abstract.start() + len(m_abstract.group(0)):m_keywords_en.start()].strip()
                annotation = re.sub(r'^[:\s\-\.]+', '', raw_annotation).strip()
                annotation = normalize_text_spacing(annotation)
                
                kw_end = full_text.find("\n", m_keywords_en.start() + 100)
                if kw_end == -1:
                    kw_end = m_keywords_en.start() + 200
                raw_kw = full_text[m_keywords_en.start() + len(m_keywords_en.group(0)):kw_end].strip()
                keywords_str = re.sub(r'^[:\s\-\.]+', '', raw_kw).strip()
                keywords_list = clean_keywords(keywords_str)
                
                # Main text: from after keywords to references
                ref_patterns = [
                    r'^\s*references\s*$', r'^\s*список\s+литературы\s*$',
                    r'^\s*литература\s*$', r'^\s*список\s+источников\s*$'
                ]
                ref_starts = []
                for pat in ref_patterns:
                    for m in re.finditer(pat, full_text, re.IGNORECASE | re.MULTILINE):
                        if m.start() > kw_end:
                            ref_starts.append(m.start())
                            
                body_start = kw_end
                body_end = min(ref_starts) if ref_starts else len(full_text)
                main_text = normalize_text_spacing(full_text[body_start:body_end].strip())
            else:
                # No structured markers at all — pure fallback
                # Try to find title in first ~500 chars
                first_chunk = full_text[:min(500, len(full_text))]
                title = extract_title(first_chunk, filename)
                authors = extract_authors(first_chunk)
                annotation = ""
                keywords_list = []
                
                # Cut references from the end
                ref_patterns = [
                    r'^\s*references\s*$', r'^\s*список\s+литературы\s*$',
                    r'^\s*литература\s*$', r'^\s*список\s+источников\s*$'
                ]
                ref_starts = []
                for pat in ref_patterns:
                    for m in re.finditer(pat, full_text, re.IGNORECASE | re.MULTILINE):
                        ref_starts.append(m.start())
                        
                body_end = min(ref_starts) if ref_starts else len(full_text)
                main_text = normalize_text_spacing(full_text[:body_end].strip())
            
            # Minimum text length check — if too short, not useful
            if len(main_text) < 200:
                return {"skipped": "Too little text content to extract anything useful"}
    
    # Quality check: reject garbled/unreadable text (broken PDF encoding)
    if not is_text_readable(main_text):
        return {"skipped": "Text appears garbled (encoding issue)"}
    
    # Quality check: reject articles with garbled/unreadable titles
    if not is_title_valid(title):
        return {"skipped": f"Title appears garbled: {title[:50]}"}
    
    # Language check: only Russian-language articles
    if not is_russian_text(main_text):
        return {"skipped": f"Non-Russian article: {title[:50]}"}
    
    return {
        "filename": filename,
        "title": title,
        "authors": authors,
        "annotation": annotation,
        "keywords": keywords_list,
        "main_text": main_text
    }

def build_corpus(workspace_dir, max_articles=None):
    articles_dir = os.path.join(workspace_dir, "articles")
    corpus_dir = os.path.join(workspace_dir, "corpus")
    
    if not os.path.exists(articles_dir):
        raise FileNotFoundError(f"Articles directory '{articles_dir}' does not exist.")
        
    os.makedirs(corpus_dir, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(articles_dir) if f.lower().endswith(".pdf")]
    if max_articles is not None:
        pdf_files = pdf_files[:max_articles]
    print(f"Found {len(pdf_files)} PDF files to process in articles/ directory.")
    
    processed_count = 0
    skipped_count = 0
    error_count = 0
    partial_count = 0
    
    summary_data = []
    
    for pdf_name in tqdm(pdf_files, desc="Building corpus"):
        pdf_path = os.path.join(articles_dir, pdf_name)
        result = process_pdf(pdf_path)
        
        if "error" in result:
            error_count += 1
            continue
        elif "skipped" in result:
            skipped_count += 1
            continue
            
        processed_count += 1
        if not result["keywords"]:
            partial_count += 1
        
        filename_no_ext = os.path.splitext(pdf_name)[0]
        json_path = os.path.join(corpus_dir, f"{filename_no_ext}.json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(result, jf, ensure_ascii=False, indent=2)
            
        summary_data.append({
            "filename": result["filename"],
            "title": result["title"],
            "authors": result["authors"],
            "keywords": result["keywords"],
            "annotation": result["annotation"],
            "text_length": len(result["main_text"])
        })
        
    master_json_path = os.path.join(corpus_dir, "corpus.json")
    with open(master_json_path, "w", encoding="utf-8") as jf:
        json.dump(summary_data, jf, ensure_ascii=False, indent=2)
        
    print(f"Corpus build finished: {processed_count} processed ({partial_count} partial, no author keywords), {skipped_count} skipped, {error_count} failed.")
    return master_json_path

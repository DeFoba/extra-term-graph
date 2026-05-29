/* ============================================================
   Extra-Term-Graph — Frontend Application
   SPA: Publications, Keywords, Cypher Queries
   ============================================================ */

(function () {
  'use strict';

  // ───── State ─────
  const state = {
    publications: [],
    keywords: [],
    relPubKw: [],
    relPubPub: [],
    kwById: {},
    pubById: {},
    kwMethods: {},
    kwPubCount: {},
    pubSearch: '',
    kwSearch: '',
    kwFilter: 'all',
    pubPage: 1,
    kwPage: 1,
    pubPerPage: 15,
    kwPerPage: 30,
    activeTab: 'publications',
  };

  // ───── Init ─────
  async function init() {
    showLoading();
    try {
      const [pubs, kws, relPK, relPP] = await Promise.all([
        fetchJSON('/api/publications'),
        fetchJSON('/api/keywords'),
        fetchJSON('/api/rel_pub_keyword'),
        fetchJSON('/api/rel_pub_pub'),
      ]);
      state.publications = pubs;
      state.keywords = kws;
      state.relPubKw = relPK;
      state.relPubPub = relPP;

      buildLookups();
      renderStats();
      renderPublications();
      renderKeywords();
      renderCypherGeneral();
      bindEvents();
    } catch (err) {
      console.error('Failed to load data:', err);
      document.querySelector('.main').innerHTML =
        '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Не удалось загрузить данные. Убедитесь, что сервер запущен и данные сгенерированы (python run_pipeline.py --step graph).</p></div>';
    }
  }

  async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
    return r.json();
  }

  function showLoading() {
    ['pub-list', 'kw-grid'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';
    });
  }

  // ───── Build Lookups ─────
  function buildLookups() {
    state.pubById = {};
    state.publications.forEach(p => { state.pubById[p.id] = p; });
    state.kwById = {};
    state.keywords.forEach(k => { state.kwById[k.id] = k; });
    state.kwMethods = {};
    state.kwPubCount = {};
    state.relPubKw.forEach(r => {
      if (!state.kwMethods[r.keyword_id]) state.kwMethods[r.keyword_id] = new Set();
      state.kwMethods[r.keyword_id].add(r.method);
      if (!state.kwPubCount[r.keyword_id]) state.kwPubCount[r.keyword_id] = new Set();
      state.kwPubCount[r.keyword_id].add(r.pub_id);
    });
  }

  // ───── Stats ─────
  function renderStats() {
    document.getElementById('stat-pubs').textContent = state.publications.length;
    document.getElementById('stat-keywords').textContent = state.keywords.length;
    document.getElementById('stat-relations').textContent = state.relPubKw.length;
    document.getElementById('stat-semantic').textContent = state.relPubPub.length;
  }

  // ───── Events ─────
  function bindEvents() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    const pubSearch = document.getElementById('pub-search');
    pubSearch.addEventListener('input', debounce(() => {
      state.pubSearch = pubSearch.value.trim().toLowerCase();
      state.pubPage = 1;
      renderPublications();
    }, 250));

    const kwSearch = document.getElementById('kw-search');
    kwSearch.addEventListener('input', debounce(() => {
      state.kwSearch = kwSearch.value.trim().toLowerCase();
      state.kwPage = 1;
      renderKeywords();
    }, 250));

    document.querySelectorAll('#kw-filters .filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#kw-filters .filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.kwFilter = btn.dataset.method;
        state.kwPage = 1;
        renderKeywords();
      });
    });

    const cypherSearch = document.getElementById('cypher-search');
    cypherSearch.addEventListener('input', debounce(() => {
      renderCypherSearch(cypherSearch.value.trim().toLowerCase());
    }, 300));
  }

  function switchTab(tabId) {
    state.activeTab = tabId;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`panel-${tabId}`).classList.add('active');
  }

  // ═══════════════════════════════════════
  //  PUBLICATIONS TAB
  // ═══════════════════════════════════════

  function filterPublications() {
    if (!state.pubSearch) return state.publications;
    const q = state.pubSearch;
    return state.publications.filter(p => {
      if (p.title && p.title.toLowerCase().includes(q)) return true;
      if (p.annotation && p.annotation.toLowerCase().includes(q)) return true;
      const rels = state.relPubKw.filter(r => r.pub_id === p.id);
      for (const r of rels) {
        const kw = state.kwById[r.keyword_id];
        if (kw && kw.name.toLowerCase().includes(q)) return true;
      }
      return false;
    });
  }

  function renderPublications() {
    const filtered = filterPublications();
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / state.pubPerPage));
    if (state.pubPage > totalPages) state.pubPage = totalPages;
    const start = (state.pubPage - 1) * state.pubPerPage;
    const page = filtered.slice(start, start + state.pubPerPage);

    document.getElementById('pub-results-info').innerHTML =
      `Показано <strong>${page.length}</strong> из <strong>${total}</strong> публикаций`;

    const list = document.getElementById('pub-list');
    if (page.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>Публикации не найдены</p></div>';
    } else {
      list.innerHTML = page.map(p => {
        const kwRels = state.relPubKw.filter(r => r.pub_id === p.id);
        const authorKws = kwRels.filter(r => r.method === 'author').slice(0, 5);
        const badges = authorKws.map(r => {
          const kw = state.kwById[r.keyword_id];
          return kw ? `<span class="badge badge-author">${esc(kw.name)}</span>` : '';
        }).join('');
        return `
          <div class="pub-card" data-pub-id="${esc(p.id)}">
            <div class="pub-card-title">${esc(p.title)}</div>
            ${p.authors && p.authors.length > 0 ? `<div class="pub-card-authors">✅ ${p.authors.map(a => esc(a)).join(', ')}</div>` : ''}
            <div class="pub-card-meta">
              <span class="badge badge-file">📄 ${esc(p.id)}</span>
              ${badges}
            </div>
            ${p.annotation ? `<div class="pub-card-annotation">${esc(p.annotation)}</div>` : ''}
          </div>`;
      }).join('');

      list.querySelectorAll('.pub-card').forEach(card => {
        card.addEventListener('click', () => showPubDetail(card.dataset.pubId));
      });
    }

    renderPagination('pub-pagination', state.pubPage, totalPages, pg => {
      state.pubPage = pg;
      renderPublications();
    });
  }

  function showPubDetail(pubId) {
    const p = state.pubById[pubId];
    if (!p) return;

    const kwRels = state.relPubKw.filter(r => r.pub_id === pubId);
    const authorKws = kwRels.filter(r => r.method === 'author');
    const tfidfKws = kwRels.filter(r => r.method === 'tfidf');
    const keybertKws = kwRels.filter(r => r.method === 'keybert');

    const simPubs = [];
    state.relPubPub.forEach(r => {
      if (r.source === pubId) simPubs.push({ id: r.target, score: r.score });
      else if (r.target === pubId) simPubs.push({ id: r.source, score: r.score });
    });
    simPubs.sort((a, b) => b.score - a.score);

    // Build keywords table
    const allKwRows = kwRels.map(r => {
      const kw = state.kwById[r.keyword_id];
      return { name: kw ? kw.name : r.keyword_id, method: r.method, weight: r.weight };
    });

    const container = document.getElementById('pub-detail');
    container.innerHTML = `
      <div class="detail-panel">
        <div class="detail-panel-header">
          <div class="detail-panel-title">${esc(p.title)}</div>
          <button class="detail-close-btn" id="pub-detail-close">✕</button>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">📄 Файл</div>
          <div class="detail-section-body"><span class="badge badge-file">${esc(p.id)}</span></div>
        </div>

        ${p.authors && p.authors.length > 0 ? `
        <div class="detail-section">
          <div class="detail-section-title">✍️ Авторы</div>
          <div class="detail-section-body">${p.authors.map(a => esc(a)).join(', ')}</div>
        </div>` : ''}

        ${p.annotation ? `
        <div class="detail-section">
          <div class="detail-section-title">📝 Аннотация</div>
          <div class="detail-section-body">${esc(p.annotation)}</div>
        </div>` : ''}

        <div class="detail-section">
          <div class="detail-section-title">👤 Авторские ключевые слова</div>
          <div class="detail-keywords-group">
            ${authorKws.length > 0
        ? authorKws.map(r => {
          const kw = state.kwById[r.keyword_id];
          return kw ? `<span class="badge badge-author" style="cursor:pointer" data-kw-nav="${esc(r.keyword_id)}">${esc(kw.name)}</span>` : '';
        }).join('')
        : '<span style="color:var(--text-muted);font-size:0.85rem">Нет данных</span>'}
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">📊 Все ключевые слова (таблица)</div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Ключевое слово</th><th>Метод</th><th>Вес</th></tr></thead>
              <tbody>
                ${allKwRows.map(r => `
                  <tr>
                    <td class="td-title">${esc(r.name)}</td>
                    <td class="td-badge"><span class="badge badge-${r.method}">${methodLabel(r.method)}</span></td>
                    <td>${r.weight}</td>
                  </tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>

        ${p.summary_tfidf ? `
        <div class="detail-section">
          <div class="detail-section-title">📑 Реферат (TF-IDF)</div>
          <div class="detail-section-body">${esc(p.summary_tfidf)}</div>
        </div>` : ''}

        ${p.summary_keybert ? `
        <div class="detail-section">
          <div class="detail-section-title">📑 Реферат (KeyBERT)</div>
          <div class="detail-section-body">${esc(p.summary_keybert)}</div>
        </div>` : ''}

        ${simPubs.length > 0 ? `
        <div class="detail-section">
          <div class="detail-section-title">🔗 Похожие публикации (Jaccard)</div>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>Публикация</th><th>Jaccard</th></tr></thead>
              <tbody>
                ${simPubs.slice(0, 10).map(s => {
          const sp = state.pubById[s.id];
          return sp ? `<tr class="similar-item" data-pub-id="${esc(s.id)}">
                    <td class="td-title">${esc(sp.title)}</td>
                    <td class="td-score"><span class="badge badge-score">${(s.score * 100).toFixed(1)}%</span></td>
                    </tr>
                  ` : '';
        }).join('')}
              </tbody>
            </table>
          </div>
        </div>` : ''}

        <div class="detail-section">
          <div class="detail-section-title">⚡ Cypher-запросы для этой публикации</div>
          ${renderCypherBlock('Все ключевые слова публикации',
          `MATCH (p:Publication {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN k.name AS keyword, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`)}
          ${renderCypherBlock('Связанные публикации через общие ключевые слова',
            `MATCH (p1:Publication {id: '${escCypher(pubId)}'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(p2:Publication)\nWHERE p1 <> p2\nRETURN p2.title AS related_publication,\n       collect(DISTINCT k.name) AS shared_keywords,\n       count(DISTINCT k) AS shared_count\nORDER BY shared_count DESC`)}
          ${renderCypherBlock('Визуализация: связанные статьи через общие ключевые слова (Neo4j Browser)',
              `MATCH path=(p:Publication {id: '${escCypher(pubId)}'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(p2:Publication)\nWHERE p <> p2\nRETURN path\nLIMIT 50`)}
          ${renderCypherBlock('Визуализация: ключевые слова публикации (Neo4j Browser)',
                `MATCH (p:Publication {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN p, r, k`)}
        </div>
      </div>`;

    document.getElementById('pub-detail-close').addEventListener('click', () => { container.innerHTML = ''; });

    container.querySelectorAll('[data-kw-nav]').forEach(badge => {
      badge.addEventListener('click', e => {
        e.stopPropagation();
        switchTab('keywords');
        setTimeout(() => showKwDetail(badge.dataset.kwNav), 100);
      });
    });

    container.querySelectorAll('.similar-item[data-pub-id]').forEach(row => {
      row.addEventListener('click', () => showPubDetail(row.dataset.pubId));
    });

    bindCopyButtons(container);
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ═══════════════════════════════════════
  //  KEYWORDS TAB
  // ═══════════════════════════════════════

  function filterKeywords() {
    let list = state.keywords;
    if (state.kwFilter !== 'all') {
      list = list.filter(k => {
        const methods = state.kwMethods[k.id];
        return methods && methods.has(state.kwFilter);
      });
    }
    if (state.kwSearch) {
      const q = state.kwSearch;
      list = list.filter(k => k.name.toLowerCase().includes(q) || k.id.toLowerCase().includes(q));
    }
    // Sort by publication count (most popular first)
    list.sort((a, b) => {
      const countA = state.kwPubCount[a.id] ? state.kwPubCount[a.id].size : 0;
      const countB = state.kwPubCount[b.id] ? state.kwPubCount[b.id].size : 0;
      return countB - countA;
    });
    return list;
  }

  function renderKeywords() {
    const filtered = filterKeywords();
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / state.kwPerPage));
    if (state.kwPage > totalPages) state.kwPage = totalPages;
    const start = (state.kwPage - 1) * state.kwPerPage;
    const page = filtered.slice(start, start + state.kwPerPage);

    document.getElementById('kw-results-info').innerHTML =
      `Показано <strong>${page.length}</strong> из <strong>${total}</strong> ключевых слов`;

    const grid = document.getElementById('kw-grid');
    if (page.length === 0) {
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🏷️</div><p>Ключевые слова не найдены</p></div>';
    } else {
      grid.innerHTML = page.map(k => {
        const methods = state.kwMethods[k.id] || new Set();
        const pubCount = state.kwPubCount[k.id] ? state.kwPubCount[k.id].size : 0;
        const badges = [];
        if (methods.has('author')) badges.push('<span class="badge badge-author">Автор</span>');
        if (methods.has('tfidf')) badges.push('<span class="badge badge-tfidf">TF-IDF</span>');
        if (methods.has('keybert')) badges.push('<span class="badge badge-keybert">KeyBERT</span>');
        return `
          <div class="kw-card" data-kw-id="${esc(k.id)}">
            <div class="kw-card-name">${esc(k.name)}</div>
            <div class="kw-card-info">
              ${badges.join('')}
              <span class="kw-pub-count">📄 ${pubCount}</span>
            </div>
          </div>`;
      }).join('');

      grid.querySelectorAll('.kw-card').forEach(card => {
        card.addEventListener('click', () => showKwDetail(card.dataset.kwId));
      });
    }

    renderPagination('kw-pagination', state.kwPage, totalPages, pg => {
      state.kwPage = pg;
      renderKeywords();
    });
  }

  function showKwDetail(kwId) {
    const k = state.kwById[kwId];
    if (!k) return;
    const methods = state.kwMethods[kwId] || new Set();

    // Related publications grouped by method
    const pubRels = state.relPubKw.filter(r => r.keyword_id === kwId);

    const container = document.getElementById('kw-detail');
    container.innerHTML = `
      <div class="detail-panel">
        <div class="detail-panel-header">
          <div class="detail-panel-title">${esc(k.name)}</div>
          <button class="detail-close-btn" id="kw-detail-close">✕</button>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Нормализованный ID</div>
          <div class="detail-section-body td-mono">${esc(k.id)}</div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">Методы извлечения</div>
          <div class="detail-keywords-group">
            ${methods.has('author') ? '<span class="badge badge-author">👤 Авторское</span>' : ''}
            ${methods.has('tfidf') ? '<span class="badge badge-tfidf">📊 TF-IDF</span>' : ''}
            ${methods.has('keybert') ? '<span class="badge badge-keybert">🤖 KeyBERT</span>' : ''}
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">📄 Связанные публикации (${pubRels.length})</div>
          <div class="kw-pubs-list">
            ${pubRels.map(r => {
      const pub = state.pubById[r.pub_id];
      return pub ? `<div class="kw-pub-item" data-pub-nav="${esc(r.pub_id)}">
                <span class="kw-pub-item-title">${esc(pub.title)}</span>
                <span class="badge badge-${r.method}">${methodLabel(r.method)}</span>
              </div>` : '';
    }).join('')}
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-section-title">⚡ Cypher-запросы</div>
          ${renderCypherBlock('Все публикации с этим термином',
      `MATCH (p:Publication)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN p.title AS publication, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`)}
          ${renderCypherBlock('Визуализация графа: статьи связанные через этот термин (Neo4j Browser)',
        `MATCH path=(p1:Publication)-[:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})<-[:HAS_KEYWORD]-(p2:Publication)\nWHERE id(p1) < id(p2)\nRETURN path\nLIMIT 50`)}
          ${renderCypherBlock('Визуализация: термин и все его публикации (Neo4j Browser)',
          `MATCH (p:Publication)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN p, r, k`)}
        </div>
      </div>`;

    document.getElementById('kw-detail-close').addEventListener('click', () => { container.innerHTML = ''; });

    container.querySelectorAll('[data-pub-nav]').forEach(row => {
      row.addEventListener('click', () => {
        switchTab('publications');
        setTimeout(() => showPubDetail(row.dataset.pubNav), 100);
      });
    });

    container.querySelectorAll('[data-kw-nav]').forEach(el => {
      el.addEventListener('click', e => {
        e.stopPropagation();
        showKwDetail(el.dataset.kwNav);
      });
    });

    bindCopyButtons(container);
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ═══════════════════════════════════════
  //  CYPHER TAB
  // ═══════════════════════════════════════

  function renderCypherGeneral() {
    const el = document.getElementById('cypher-general');
    const queries = [
      {
        title: '🔍 Все публикации и их авторские ключевые слова',
        code: `MATCH (p:Publication)-[r:HAS_KEYWORD {method: 'author'}]->(k:Keyword)\nRETURN p.title AS publication, collect(k.name) AS author_keywords\nORDER BY p.title`
      },
      {
        title: '📊 Топ-10 самых частых ключевых слов',
        code: `MATCH (k:Keyword)<-[:HAS_KEYWORD]-(p:Publication)\nRETURN k.name AS keyword, count(DISTINCT p) AS pub_count\nORDER BY pub_count DESC\nLIMIT 10`
      },
      {
        title: '🔗 Все пары похожих публикаций (Jaccard)',
        code: `MATCH (p1:Publication)-[r:SIMILAR_TO]->(p2:Publication)\nRETURN p1.title AS pub1, p2.title AS pub2, r.score AS jaccard\nORDER BY r.score DESC`
      },
      {
        title: '🧠 Семантически близкие термины (Cosine)',
        code: `MATCH (k1:Keyword)-[r:SEMANTICALLY_SIMILAR]->(k2:Keyword)\nRETURN k1.name AS term1, k2.name AS term2, r.score AS cosine\nORDER BY r.score DESC\nLIMIT 30`
      },
      {
        title: '🌲 Иерархия терминов (SUB_TERM_OF)',
        code: `MATCH (child:Keyword)-[:SUB_TERM_OF]->(parent:Keyword)\nRETURN child.name AS child_term, parent.name AS parent_term\nORDER BY parent.name, child.name`
      },
      {
        title: '📄 Публикации с наибольшим количеством ключевых слов',
        code: `MATCH (p:Publication)-[:HAS_KEYWORD]->(k:Keyword)\nRETURN p.title AS publication, count(k) AS keyword_count\nORDER BY keyword_count DESC\nLIMIT 10`
      },
      {
        title: '🔎 Найти путь между двумя публикациями через общие термины',
        code: `// Замените заголовки на нужные:\nMATCH path = (p1:Publication {title: 'TITLE_1'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(p2:Publication {title: 'TITLE_2'})\nRETURN k.name AS shared_keyword, path`
      },
      {
        title: '👤 Сравнение авторских vs. извлечённых ключевых слов',
        code: `MATCH (p:Publication)-[r:HAS_KEYWORD]->(k:Keyword)\nWITH p, r.method AS method, collect(k.name) AS keywords\nRETURN p.title AS publication, method, keywords\nORDER BY p.title, method`
      },
    ];

    el.innerHTML = queries.map(q => renderCypherBlock(q.title, q.code)).join('');
    bindCopyButtons(el);
  }

  function renderCypherSearch(query) {
    const el = document.getElementById('cypher-results');
    if (!query || query.length < 2) {
      el.innerHTML = '';
      return;
    }

    const matchedPubs = state.publications.filter(p =>
      p.title.toLowerCase().includes(query) || p.id.toLowerCase().includes(query)
    ).slice(0, 5);

    const matchedKws = state.keywords.filter(k =>
      k.name.toLowerCase().includes(query) || k.id.toLowerCase().includes(query)
    ).slice(0, 5);

    if (matchedPubs.length === 0 && matchedKws.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>Ничего не найдено</p></div>';
      return;
    }

    let html = '';

    matchedPubs.forEach(p => {
      html += `
        <div class="cypher-result-card" data-cypher-pub="${esc(p.id)}">
          <div class="cypher-result-name">📄 ${esc(p.title)}</div>
          <div class="cypher-result-type">Публикация — нажмите для генерации запросов</div>
        </div>`;
    });

    matchedKws.forEach(k => {
      html += `
        <div class="cypher-result-card" data-cypher-kw="${esc(k.id)}">
          <div class="cypher-result-name">🏷️ ${esc(k.name)}</div>
          <div class="cypher-result-type">Ключевое слово — нажмите для генерации запросов</div>
        </div>`;
    });

    el.innerHTML = html;

    el.querySelectorAll('[data-cypher-pub]').forEach(card => {
      card.addEventListener('click', () => {
        const pubId = card.dataset.cypherPub;
        const pub = state.pubById[pubId];
        if (!pub) return;
        el.innerHTML = `
          <div class="cypher-section">
            <h3 class="cypher-section-title">📄 ${esc(pub.title)}</h3>
            ${renderCypherBlock('Все ключевые слова',
          `MATCH (p:Publication {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN k.name AS keyword, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`)}
            ${renderCypherBlock('Только авторские ключевые слова',
            `MATCH (p:Publication {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD {method: 'author'}]->(k:Keyword)\nRETURN k.name AS author_keyword`)}
            ${renderCypherBlock('Похожие публикации',
              `MATCH (p1:Publication {id: '${escCypher(pubId)}'})-[r:SIMILAR_TO]-(p2:Publication)\nRETURN p2.title AS similar, r.score AS jaccard\nORDER BY r.score DESC`)}
            ${renderCypherBlock('Публикации с общими терминами',
                `MATCH (p1:Publication {id: '${escCypher(pubId)}'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(p2:Publication)\nWHERE p1 <> p2\nRETURN p2.title AS related_pub, collect(k.name) AS shared_keywords, count(k) AS shared_count\nORDER BY shared_count DESC`)}
          </div>`;
        bindCopyButtons(el);
      });
    });

    el.querySelectorAll('[data-cypher-kw]').forEach(card => {
      card.addEventListener('click', () => {
        const kwId = card.dataset.cypherKw;
        const kw = state.kwById[kwId];
        if (!kw) return;
        el.innerHTML = `
          <div class="cypher-section">
            <h3 class="cypher-section-title">🏷️ ${esc(kw.name)}</h3>
            ${renderCypherBlock('Все публикации с этим термином',
          `MATCH (p:Publication)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN p.title AS publication, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`)}
            ${renderCypherBlock('Визуализация графа: статьи связанные через термин (Neo4j Browser)',
            `MATCH path=(p1:Publication)-[:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})<-[:HAS_KEYWORD]-(p2:Publication)\nWHERE id(p1) < id(p2)\nRETURN path\nLIMIT 50`)}
            ${renderCypherBlock('Визуализация: термин и все публикации (Neo4j Browser)',
              `MATCH (p:Publication)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN p, r, k`)}
          </div>`;
        bindCopyButtons(el);
      });
    });
  }

  // ───── Cypher block rendering ─────
  function renderCypherBlock(title, code) {
    const highlighted = highlightCypher(code);
    const id = 'cypher-' + Math.random().toString(36).slice(2, 9);
    return `
      <div class="cypher-block">
        <div class="cypher-block-header">
          <span class="cypher-block-title">${title}</span>
          <button class="cypher-copy-btn" data-copy-target="${id}">📋 Копировать</button>
        </div>
        <pre class="cypher-code" id="${id}">${highlighted}</pre>
        <textarea style="display:none" id="${id}-raw">${esc(code)}</textarea>
      </div>`;
  }

  function highlightCypher(code) {
    // Escape HTML first
    let s = esc(code);
    // Comments
    s = s.replace(/(\/\/.*)/g, '<span class="cy-comment">$1</span>');
    // Keywords
    const kwds = ['MATCH', 'RETURN', 'WHERE', 'ORDER BY', 'LIMIT', 'WITH', 'CREATE', 'MERGE', 'SET', 'UNWIND',
      'OPTIONAL MATCH', 'DETACH DELETE', 'DELETE', 'AS', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
      'DESC', 'ASC', 'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'count', 'collect',
      'toFloat', 'id', 'IF NOT EXISTS', 'FOR', 'REQUIRE', 'IS UNIQUE', 'CONSTRAINT'];
    kwds.sort((a, b) => b.length - a.length);
    kwds.forEach(kw => {
      const re = new RegExp('\\b(' + kw.replace(/\s+/g, '\\s+') + ')\\b', 'gi');
      s = s.replace(re, '<span class="cy-keyword">$1</span>');
    });
    // Labels :Label
    s = s.replace(/:([A-Z][A-Za-z_]*)/g, ':<span class="cy-label">$1</span>');
    // Relationship types [:TYPE]
    s = s.replace(/\[([^\]]*?)]/g, (match) => {
      return match.replace(/:([A-Z_]+)/g, ':<span class="cy-rel">$1</span>');
    });
    // Properties {key: value}
    s = s.replace(/(\w+):/g, '<span class="cy-prop">$1</span>:');
    // Strings
    s = s.replace(/&#39;([^&#]*(?:&#[^;]*;[^&#]*)*)&#39;/g, '<span class="cy-string">\'$1\'</span>');
    return s;
  }

  function bindCopyButtons(container) {
    container.querySelectorAll('.cypher-copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.dataset.copyTarget;
        const rawEl = document.getElementById(targetId + '-raw');
        if (!rawEl) return;
        const text = rawEl.value;
        navigator.clipboard.writeText(text).then(() => {
          btn.classList.add('copied');
          btn.innerHTML = '✅ Скопировано';
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.innerHTML = '📋 Копировать';
          }, 2000);
        });
      });
    });
  }

  // ───── Pagination ─────
  function renderPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (totalPages <= 1) { container.innerHTML = ''; return; }

    let html = `<button class="page-btn" data-page="${currentPage - 1}" ${currentPage <= 1 ? 'disabled' : ''}>◀</button>`;
    const maxV = 7;
    let startP = Math.max(1, currentPage - Math.floor(maxV / 2));
    let endP = Math.min(totalPages, startP + maxV - 1);
    if (endP - startP < maxV - 1) startP = Math.max(1, endP - maxV + 1);

    if (startP > 1) {
      html += `<button class="page-btn" data-page="1">1</button>`;
      if (startP > 2) html += '<span style="color:var(--text-muted);padding:0 4px">…</span>';
    }
    for (let i = startP; i <= endP; i++) {
      html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }
    if (endP < totalPages) {
      if (endP < totalPages - 1) html += '<span style="color:var(--text-muted);padding:0 4px">…</span>';
      html += `<button class="page-btn" data-page="${totalPages}">${totalPages}</button>`;
    }
    html += `<button class="page-btn" data-page="${currentPage + 1}" ${currentPage >= totalPages ? 'disabled' : ''}>▶</button>`;

    container.innerHTML = html;
    container.querySelectorAll('.page-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const pg = parseInt(btn.dataset.page);
        if (pg >= 1 && pg <= totalPages) onPageChange(pg);
      });
    });
  }

  // ───── Helpers ─────
  function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function escCypher(str) {
    return String(str).replace(/'/g, "\\'");
  }

  function methodLabel(m) {
    if (m === 'author') return '👤 Автор';
    if (m === 'tfidf') return '📊 TF-IDF';
    if (m === 'keybert') return '🤖 KeyBERT';
    return m;
  }

  function debounce(fn, delay) {
    let t;
    return function (...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); };
  }

  document.addEventListener('DOMContentLoaded', init);
})();

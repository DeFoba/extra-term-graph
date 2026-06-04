   Extra-Term-Graph — Frontend Application
   SPA: Publications, Keywords, Graph Visualization, Cypher Queries
   All search and data retrieval via Neo4j Cypher (server-side).

(function () {
  'use strict';

  const state = {
    stats: { publications: 0, keywords: 0, rel_pub_keyword: 0, rel_pub_pub: 0 },
    pubSearch: '',
    pubPage: 1,
    pubPerPage: 15,
    pubTotal: 0,
    pubTotalPages: 1,
    pubItems: [],
    kwSearch: '',
    kwFilter: 'all',
    kwPage: 1,
    kwPerPage: 30,
    kwTotal: 0,
    kwTotalPages: 1,
    kwItems: [],
    activeTab: 'publications',
    neo4jConfig: null,
    neoViz: null,
  };

  const GRAPH_QUERIES = {
    all_pub_kw: "MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword) RETURN d, r, k LIMIT 100",
    similar_pubs: `MATCH (d1:Document)-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)
WHERE d1.id < d2.id
WITH d1, d2, count(k) AS shared_count
WHERE shared_count >= 2
ORDER BY shared_count DESC
LIMIT 10
MATCH path=(d1)-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2)
RETURN path`,
    top_keywords: `MATCH (k:Keyword)<-[:HAS_KEYWORD]-(d:Document)
WITH k, count(d) AS cnt ORDER BY cnt DESC LIMIT 10
MATCH (d2:Document)-[r:HAS_KEYWORD]->(k)
RETURN d2, r, k LIMIT 150`,
  };


  async function init() {
    showLoading();
    try {
      const [statsData, neo4jCfg] = await Promise.all([
        fetchJSON('/api/stats'),
        fetchJSON('/api/neo4j_config'),
      ]);
      state.stats = statsData;
      state.neo4jConfig = neo4jCfg;

      renderStats();
      bindEvents();

      await Promise.all([
        loadPublications(),
        loadKeywords(),
      ]);

      renderCypherGeneral();
    } catch (err) {
      console.error('Failed to load data:', err);
      document.querySelector('.main').innerHTML =
        '<div class="empty-state"><div class="empty-icon">⚠️</div>' +
        '<p>Не удалось загрузить данные. Убедитесь что:</p>' +
        '<ol style="text-align:left;max-width:500px;margin:1rem auto">' +
        '<li>Neo4j запущен (<code>run_neo4j.bat</code> или <code>./run_neo4j.sh</code>)</li>' +
        '<li>Данные загружены (<code>python run_pipeline.py --step graph</code>)</li>' +
        '<li>Flask сервер работает</li></ol></div>';
    }
  }

  async function fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      if (body.error) throw new Error(body.error + (body.hint ? ' | ' + body.hint : ''));
      throw new Error(`HTTP ${r.status} for ${url}`);
    }
    return r.json();
  }

  function showLoading() {
    ['pub-list', 'kw-grid'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';
    });
  }

  function renderStats() {
    document.getElementById('stat-pubs').textContent = state.stats.publications;
    document.getElementById('stat-keywords').textContent = state.stats.keywords;
    document.getElementById('stat-relations').textContent = state.stats.rel_pub_keyword;

    const dbStatus = document.getElementById('db-status-badge');
    if (dbStatus) {
      const dot = dbStatus.querySelector('.status-dot');
      const text = dbStatus.querySelector('.status-text');
      if (state.neo4jConfig && state.neo4jConfig.connected) {
        dot.style.background = '#2ECC71';
        dot.style.boxShadow = '0 0 8px rgba(46, 204, 113, 0.6)';
        text.textContent = 'Neo4j подключён';
        dbStatus.title = 'Подключено к ' + state.neo4jConfig.uri;
      } else {
        dot.style.background = '#E74C3C';
        dot.style.boxShadow = '0 0 8px rgba(231, 76, 60, 0.6)';
        text.textContent = 'Neo4j отключён';
        dbStatus.title = 'Нет подключения к базе данных';
      }
    }
  }

  function bindEvents() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    const pubSearch = document.getElementById('pub-search');
    pubSearch.addEventListener('input', debounce(() => {
      state.pubSearch = pubSearch.value.trim();
      state.pubPage = 1;
      loadPublications();
    }, 400));

    const pubGraphBtn = document.getElementById('pub-search-graph-btn');
    if (pubGraphBtn) {
      pubGraphBtn.addEventListener('click', () => {
        const q = document.getElementById('pub-search').value.trim();
        if (q) searchOnGraph(q, 'publications');
      });
    }

    const kwSearch = document.getElementById('kw-search');
    kwSearch.addEventListener('input', debounce(() => {
      state.kwSearch = kwSearch.value.trim();
      state.kwPage = 1;
      loadKeywords();
    }, 400));

    const kwGraphBtn = document.getElementById('kw-search-graph-btn');
    if (kwGraphBtn) {
      kwGraphBtn.addEventListener('click', () => {
        const q = document.getElementById('kw-search').value.trim();
        if (q) searchOnGraph(q, 'keywords');
      });
    }

    document.querySelectorAll('#kw-filters .filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#kw-filters .filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.kwFilter = btn.dataset.method;
        state.kwPage = 1;
        loadKeywords();
      });
    });

    const cypherSearch = document.getElementById('cypher-search');
    cypherSearch.addEventListener('input', debounce(() => {
      renderCypherSearch(cypherSearch.value.trim().toLowerCase());
    }, 300));

    bindGraphEvents();
  }

  function switchTab(tabId) {
    state.activeTab = tabId;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`panel-${tabId}`).classList.add('active');

    if (tabId === 'graph' && !state.neoViz && state.neo4jConfig && state.neo4jConfig.connected) {
      initGraph();
    }
  }


  async function loadPublications() {
    const list = document.getElementById('pub-list');
    list.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';

    try {
      const params = new URLSearchParams({
        page: state.pubPage,
        per_page: state.pubPerPage,
      });
      if (state.pubSearch) params.set('q', state.pubSearch);

      const data = await fetchJSON('/api/publications?' + params.toString());
      state.pubItems = data.items;
      state.pubTotal = data.total;
      state.pubTotalPages = data.total_pages;
      state.pubPage = data.page;

      renderPublications();
    } catch (err) {
      console.error('Failed to load publications:', err);
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Ошибка загрузки</p></div>';
    }
  }

  function renderPublications() {
    const items = state.pubItems;

    const infoEl = document.getElementById('pub-results-info');
    if (state.pubSearch) {
      infoEl.innerHTML = `Найдено <strong>${state.pubTotal}</strong> публикаций по запросу «<em>${esc(state.pubSearch)}</em>» <span class="search-via-neo4j">через Neo4j Cypher</span>`;
    } else {
      infoEl.innerHTML = `Всего <strong>${state.pubTotal}</strong> публикаций`;
    }

    const list = document.getElementById('pub-list');
    if (items.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>Публикации не найдены</p></div>';
    } else {
      list.innerHTML = items.map(p => {
        const kwList = p.keywords || [];
        const authorKws = kwList.filter(r => r.method === 'author').slice(0, 5);
        const hasAuthorKws = authorKws.length > 0;
        let badges;
        if (hasAuthorKws) {
          badges = authorKws.map(r => `<span class="badge badge-author">${esc(r.keyword_name)}</span>`).join('');
        } else {
          const keybertKws = kwList.filter(r => r.method === 'keybert').slice(0, 5);
          badges = keybertKws.map(r => `<span class="badge badge-keybert">${esc(r.keyword_name)}</span>`).join('');
        }

        const hasAnnotation = p.annotation && p.annotation.trim().length > 0;
        const annotationText = hasAnnotation ? p.annotation : (p.summary_keybert || '');
        const annotationLabel = hasAnnotation ? '' : '<span class="badge badge-auto-annotation">🤖 Авто-аннотация</span> ';

        return `
          <div class="pub-card" data-pub-id="${esc(p.id)}">
            <div class="pub-card-title">${esc(p.title)}</div>
            ${p.authors && p.authors.length > 0 ? `<div class="pub-card-authors">✅ ${p.authors.map(a => esc(a)).join(', ')}</div>` : ''}
            ${annotationText ? `<div class="pub-card-annotation">${annotationLabel}${esc(annotationText)}</div>` : ''}
            <div class="pub-card-meta">
              <a href="/articles/${encodeURIComponent(p.id)}" target="_blank" onclick="event.stopPropagation()" class="badge badge-file" style="text-decoration:none;color:inherit;cursor:pointer">📄 ${esc(p.id)}</a>
              ${badges}
              ${!hasAuthorKws && badges ? '<span class="badge badge-auto-kw">🤖 авто</span>' : ''}
            </div>
          </div>`;
      }).join('');

      list.querySelectorAll('.pub-card').forEach(card => {
        card.addEventListener('click', () => showPubDetail(card.dataset.pubId));
      });
    }

    renderPagination('pub-pagination', state.pubPage, state.pubTotalPages, pg => {
      state.pubPage = pg;
      loadPublications();
    });
  }

  async function showPubDetail(pubId) {
    const container = document.getElementById('pub-detail');
    container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';

    try {
      const p = await fetchJSON(`/api/publications/${encodeURIComponent(pubId)}`);

      const kwList = p.keywords || [];
      const authorKws = kwList.filter(r => r.method === 'author');
      const keybertKws = kwList.filter(r => r.method === 'keybert');
      const simPubs = p.similar || [];

      const graphCypher = `MATCH (d:Document {id: '${escCypher(pubId)}'})
OPTIONAL MATCH path1=(d)-[r:HAS_KEYWORD]->(k:Keyword)
OPTIONAL MATCH path2=(k)<-[r2:HAS_KEYWORD]-(d2:Document)
RETURN path1, path2 LIMIT 150`;

      container.innerHTML = `
        <div class="detail-panel">
          <div class="detail-panel-header">
            <div class="detail-panel-title">${esc(p.title)}</div>
            <button class="detail-close-btn" id="pub-detail-close">✕</button>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">📄 Файл</div>
            <div class="detail-section-body">
              <a href="/articles/${encodeURIComponent(p.id)}" target="_blank" class="badge badge-file" style="text-decoration:none;color:inherit;cursor:pointer">📄 ${esc(p.id)}</a>
            </div>
          </div>

          ${p.authors && p.authors.length > 0 ? `
          <div class="detail-section">
            <div class="detail-section-title">✍️ Авторы</div>
            <div class="detail-section-body">${p.authors.map(a => esc(a)).join(', ')}</div>
          </div>` : ''}

          ${(() => {
            const hasAnnotation = p.annotation && p.annotation.trim().length > 0;
            const annotationText = hasAnnotation ? p.annotation : (p.summary_keybert || '');
            if (!annotationText) return '';
            const title = hasAnnotation ? '📝 Аннотация' : '🤖 Аннотация (KeyBERT)';
            return `
            <div class="detail-section">
              <div class="detail-section-title">${title}</div>
              <div class="detail-section-body">${esc(annotationText)}</div>
            </div>`;
          })()}

          <div class="detail-section">
            <div class="detail-section-title">${authorKws.length > 0 ? '👤 Авторские ключевые слова' : '🤖 Ключевые слова (KeyBERT)'}</div>
            <div class="detail-keywords-group">
              ${authorKws.length > 0
                ? authorKws.map(r => `<span class="badge badge-author" style="cursor:pointer" data-kw-nav="${esc(r.keyword_id)}">${esc(r.keyword_name)}</span>`).join('')
                : (keybertKws.length > 0
                  ? keybertKws.map(r => `<span class="badge badge-keybert" style="cursor:pointer" data-kw-nav="${esc(r.keyword_id)}">${esc(r.keyword_name)}</span>`).join('')
                  : '<span style="color:var(--text-muted);font-size:0.85rem">Нет данных</span>')}
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">📊 Все ключевые слова (таблица)</div>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Ключевое слово</th><th>Метод</th><th>Вес</th></tr></thead>
                <tbody>
                  ${kwList.map(r => `
                    <tr>
                      <td class="td-title">${esc(r.keyword_name)}</td>
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
            <div class="detail-section-title">🔗 Связанные публикации (по общим терминам)</div>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead><tr><th>Публикация</th><th style="width:100px;text-align:center">Общих слов</th></tr></thead>
                <tbody>
                  ${simPubs.map(s => {
                    const uniqueKws = s.shared || [];
                    const displayKws = uniqueKws.slice(0, 5).join(', ');
                    const extraKws = uniqueKws.length > 5 ? ` и др. (+${uniqueKws.length - 5})` : '';
                    return `
                    <tr class="similar-item" data-pub-id="${esc(s.id)}">
                      <td class="td-title">
                        <div style="font-weight:600;margin-bottom:4px">${esc(s.title)}</div>
                        ${uniqueKws.length > 0 ? `<div style="font-size:0.75rem;color:var(--text-muted);line-height:1.2;word-break:break-word">Общие термины: ${esc(displayKws)}${esc(extraKws)}</div>` : ''}
                      </td>
                      <td class="td-score" style="text-align:center"><span class="badge badge-score">${s.score}</span></td>
                    </tr>`;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </div>` : ''}

          <div class="detail-section">
            <div class="detail-section-title">📊 Визуализация на графе</div>
            <div class="detail-section-body">
              <button class="graph-show-btn" id="pub-show-graph">🔍 Показать на графе</button>
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">⚡ Cypher-запросы</div>
            ${renderCypherBlock('Ключевые слова публикации',
              `MATCH (d:Document {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN k.name AS keyword, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`,
              `MATCH path=(d:Document {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN path`)}
            ${renderCypherBlock('Связанные публикации через общие термины',
              `MATCH (d1:Document {id: '${escCypher(pubId)}'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)\nWHERE d1 <> d2\nRETURN d2.title AS related,\n       collect(DISTINCT k.name) AS shared_keywords,\n       count(DISTINCT k) AS shared_count\nORDER BY shared_count DESC`,
              `MATCH path=(d1:Document {id: '${escCypher(pubId)}'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)\nWHERE d1 <> d2\nRETURN path\nLIMIT 100`)}
          </div>
        </div>`;

      document.getElementById('pub-detail-close').addEventListener('click', () => { container.innerHTML = ''; });
      document.getElementById('pub-show-graph').addEventListener('click', () => showOnGraph(graphCypher));

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
    } catch (err) {
      console.error('Failed to load publication detail:', err);
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Ошибка загрузки</p></div>';
    }
  }


  async function loadKeywords() {
    const grid = document.getElementById('kw-grid');
    grid.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';

    try {
      const params = new URLSearchParams({
        page: state.kwPage,
        per_page: state.kwPerPage,
      });
      if (state.kwSearch) params.set('q', state.kwSearch);
      if (state.kwFilter && state.kwFilter !== 'all') params.set('method', state.kwFilter);

      const data = await fetchJSON('/api/keywords?' + params.toString());
      state.kwItems = data.items;
      state.kwTotal = data.total;
      state.kwTotalPages = data.total_pages;
      state.kwPage = data.page;

      renderKeywords();
    } catch (err) {
      console.error('Failed to load keywords:', err);
      grid.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Ошибка загрузки</p></div>';
    }
  }

  function renderKeywords() {
    const items = state.kwItems;

    const infoEl = document.getElementById('kw-results-info');
    if (state.kwSearch) {
      infoEl.innerHTML = `Найдено <strong>${state.kwTotal}</strong> ключевых слов по запросу «<em>${esc(state.kwSearch)}</em>» <span class="search-via-neo4j">через Neo4j Cypher</span>`;
    } else {
      infoEl.innerHTML = `Всего <strong>${state.kwTotal}</strong> ключевых слов`;
    }

    const grid = document.getElementById('kw-grid');
    if (items.length === 0) {
      grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🏷️</div><p>Ключевые слова не найдены</p></div>';
    } else {
      grid.innerHTML = items.map(k => {
        const methodsStr = k.methods || '';
        const badges = [];
        if (methodsStr.includes('author')) badges.push('<span class="badge badge-author">Автор</span>');
        if (methodsStr.includes('tfidf')) badges.push('<span class="badge badge-tfidf">TF-IDF</span>');
        if (methodsStr.includes('keybert')) badges.push('<span class="badge badge-keybert">KeyBERT</span>');
        return `
          <div class="kw-card" data-kw-id="${esc(k.id)}">
            <div class="kw-card-name">${esc(k.name)}</div>
            <div class="kw-card-info">
              ${badges.join('')}
              <span class="kw-pub-count">📄 ${k.pub_count}</span>
            </div>
          </div>`;
      }).join('');

      grid.querySelectorAll('.kw-card').forEach(card => {
        card.addEventListener('click', () => showKwDetail(card.dataset.kwId));
      });
    }

    renderPagination('kw-pagination', state.kwPage, state.kwTotalPages, pg => {
      state.kwPage = pg;
      loadKeywords();
    });
  }

  async function showKwDetail(kwId) {
    const container = document.getElementById('kw-detail');
    container.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';

    try {
      const k = await fetchJSON(`/api/keywords/${encodeURIComponent(kwId)}`);
      const pubRels = k.pub_rels || [];
      const methodsStr = k.methods || '';

      const graphCypher = `MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'}) RETURN d, r, k`;

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
              ${methodsStr.includes('author') ? '<span class="badge badge-author">👤 Авторское</span>' : ''}
              ${methodsStr.includes('tfidf') ? '<span class="badge badge-tfidf">📊 TF-IDF</span>' : ''}
              ${methodsStr.includes('keybert') ? '<span class="badge badge-keybert">🤖 KeyBERT</span>' : ''}
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">📄 Связанные публикации (${pubRels.length})</div>
            <div class="kw-pubs-list">
              ${pubRels.map(r => `
                <div class="kw-pub-item" data-pub-nav="${esc(r.pub_id)}">
                  <span class="kw-pub-item-title">${esc(r.title)}</span>
                  <span class="badge badge-${r.method}">${methodLabel(r.method)}</span>
                </div>`).join('')}
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">📊 Визуализация на графе</div>
            <div class="detail-section-body">
              <button class="graph-show-btn" id="kw-show-graph">🔍 Показать на графе</button>
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-section-title">⚡ Cypher-запросы</div>
            ${renderCypherBlock('Все публикации с этим термином',
              `MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN d.title AS publication, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`,
              `MATCH path=(d:Document)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN path`)}
          </div>
        </div>`;

      document.getElementById('kw-detail-close').addEventListener('click', () => { container.innerHTML = ''; });
      document.getElementById('kw-show-graph').addEventListener('click', () => showOnGraph(graphCypher));

      container.querySelectorAll('[data-pub-nav]').forEach(row => {
        row.addEventListener('click', () => {
          switchTab('publications');
          setTimeout(() => showPubDetail(row.dataset.pubNav), 100);
        });
      });

      bindCopyButtons(container);
      container.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      console.error('Failed to load keyword detail:', err);
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Ошибка загрузки</p></div>';
    }
  }


  async function searchOnGraph(query, type) {
    try {
      const data = await fetchJSON(`/api/search/graph?q=${encodeURIComponent(query)}&type=${type}`);
      if (data.cypher) {
        switchTab('graph');
        setTimeout(() => {
          if (state.neoViz) {
            setGraphStatus(`⏳ Визуализация поиска: «${data.description}»...`);
            state.neoViz.renderWithCypher(data.cypher);
          } else {
            initGraph(data.cypher);
          }
          const select = document.getElementById('graph-query-select');
          select.value = 'custom';
          document.getElementById('graph-custom-query').style.display = 'block';
          document.getElementById('graph-cypher-input').value = data.cypher;
        }, 150);
      }
    } catch (err) {
      console.error('Graph search error:', err);
    }
  }


  function bindGraphEvents() {
    const querySelect = document.getElementById('graph-query-select');
    const customWrap = document.getElementById('graph-custom-query');
    const runBtn = document.getElementById('graph-run-btn');
    const stabilizeBtn = document.getElementById('graph-stabilize-btn');
    const clearBtn = document.getElementById('graph-clear-btn');

    querySelect.addEventListener('change', () => {
      customWrap.style.display = querySelect.value === 'custom' ? 'block' : 'none';
    });

    runBtn.addEventListener('click', () => runGraphQuery());
    stabilizeBtn.addEventListener('click', () => {
      if (state.neoViz) state.neoViz.stabilize();
    });
    clearBtn.addEventListener('click', () => {
      if (state.neoViz) state.neoViz.clearNetwork();
      setGraphStatus('Граф очищен');
    });
  }

  function initGraph(initialCypher) {
    if (!state.neo4jConfig || !state.neo4jConfig.connected) {
      setGraphStatus('❌ Neo4j не подключён. Запустите Neo4j и перезагрузите страницу.');
      return;
    }

    const cypher = initialCypher || GRAPH_QUERIES.all_pub_kw;

    try {
      const config = {
        containerId: "graph-viz",
        neo4j: {
          serverUrl: state.neo4jConfig.uri,
          serverUser: state.neo4jConfig.user,
          serverPassword: state.neo4jConfig.password,
        },
        visConfig: {
          nodes: {
            shape: "dot",
            font: { size: 12, color: "#E0E0E0", strokeWidth: 2, strokeColor: "#1a1a2e" },
            borderWidth: 2,
          },
          edges: {
            arrows: { to: { enabled: true, scaleFactor: 0.5 } },
            font: { size: 9, color: "#888", strokeWidth: 0 },
            smooth: { type: "continuous" },
          },
          physics: {
            barnesHut: { gravitationalConstant: -8000, springLength: 200, springConstant: 0.04 },
            stabilization: { iterations: 150 },
          },
          interaction: { hover: true, tooltipDelay: 200, zoomView: true, dragView: true },
        },
        labels: {
          Document: {
            label: "title",
            [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
              static: {
                color: { background: "#4A90D9", border: "#2C6FAD", highlight: { background: "#6BB5FF", border: "#4A90D9" } },
                shape: "dot",
                size: 20,
                font: { size: 11, color: "#E0E0E0" },
              },
              function: {
                title: (node) => {
                  const title = node.properties.title || node.properties.id || '';
                  const annotation = node.properties.annotation || '';
                  return `📄 ${title}\n\n${annotation ? annotation.substring(0, 200) + '...' : ''}`;
                },
              },
            },
          },
          Keyword: {
            label: "name",
            [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
              static: {
                shape: "dot",
                size: 14,
                font: { size: 10, color: "#E0E0E0" },
              },
              function: {
                title: (node) => {
                  const methods = node.properties.methods || '—';
                  return `🏷️ ${node.properties.name || node.properties.id}\nМетоды: ${methods}`;
                },
                color: (node) => {
                  const methods = node.properties.methods || '';
                  if (methods.includes('author')) {
                    return { background: "#2ECC71", border: "#1FA055", highlight: { background: "#5DEFA0", border: "#2ECC71" } };
                  } else if (methods.includes('tfidf')) {
                    return { background: "#F59E0B", border: "#D97706", highlight: { background: "#FBBF24", border: "#F59E0B" } };
                  } else if (methods.includes('keybert')) {
                    return { background: "#8B5CF6", border: "#6D28D9", highlight: { background: "#A78BFA", border: "#8B5CF6" } };
                  }
                  return { background: "#6B7280", border: "#4B5563", highlight: { background: "#9CA3AF", border: "#6B7280" } };
                },
              },
            },
          },
        },
        relationships: {
          HAS_KEYWORD: {
            [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
              static: {
                width: 1,
              },
              function: {
                title: (edge) => `Метод: ${edge.properties.method || '—'}\nВес: ${edge.properties.weight || '—'}`,
                color: (edge) => {
                  const method = edge.properties.method || '';
                  if (method === 'author') return { color: "#2ECC71", highlight: "#5DEFA0", opacity: 0.7 };
                  if (method === 'tfidf') return { color: "#F59E0B", highlight: "#FBBF24", opacity: 0.5 };
                  if (method === 'keybert') return { color: "#8B5CF6", highlight: "#A78BFA", opacity: 0.5 };
                  return { color: "#5D6D7E", highlight: "#85C1E9", opacity: 0.6 };
                },
              },
            },
          },
          SIMILAR_TO: {
            [NeoVis.NEOVIS_ADVANCED_CONFIG]: {
              static: {
                color: { color: "#E74C3C", highlight: "#FF7675", opacity: 0.8 },
                width: 2,
                dashes: [5, 5],
              },
              function: {
                label: (edge) => {
                  const score = edge.properties.score;
                  return score ? (score * 100).toFixed(0) + '%' : '';
                },
                title: (edge) => {
                  const score = edge.properties.score;
                  return `Jaccard: ${score ? (score * 100).toFixed(1) + '%' : '—'}`;
                },
              },
            },
          },
        },
        initialCypher: cypher,
      };

      state.neoViz = new NeoVis.default(config);

      state.neoViz.registerOnEvent("completed", (e) => {
        const nodeCount = e.nodeCount !== undefined ? e.nodeCount : '?';
        const relCount = e.relationshipCount !== undefined ? e.relationshipCount : '?';
        setGraphStatus(`✅ Граф загружен: ${nodeCount} узлов, ${relCount} связей`);
      });

      state.neoViz.registerOnEvent("error", (e) => {
        console.error("NeoVis error:", e);
        setGraphStatus(`❌ Ошибка: ${e.error || e}`);
      });

      setGraphStatus('⏳ Загрузка графа...');
      state.neoViz.render();
    } catch (err) {
      console.error("Graph init error:", err);
      setGraphStatus(`❌ Ошибка инициализации: ${err.message}`);
    }
  }

  function runGraphQuery() {
    const select = document.getElementById('graph-query-select');
    let cypher;
    if (select.value === 'custom') {
      cypher = document.getElementById('graph-cypher-input').value.trim();
      if (!cypher) { setGraphStatus('⚠️ Введите Cypher-запрос'); return; }
    } else {
      cypher = GRAPH_QUERIES[select.value];
    }
    if (!cypher) return;
    if (state.neoViz) {
      setGraphStatus('⏳ Выполнение запроса...');
      state.neoViz.renderWithCypher(cypher);
    } else {
      initGraph(cypher);
    }
  }

  function showOnGraph(cypher) {
    switchTab('graph');
    setTimeout(() => {
      if (state.neoViz) {
        setGraphStatus('⏳ Загрузка...');
        state.neoViz.renderWithCypher(cypher);
      } else {
        initGraph(cypher);
      }
      const select = document.getElementById('graph-query-select');
      select.value = 'custom';
      document.getElementById('graph-custom-query').style.display = 'block';
      document.getElementById('graph-cypher-input').value = cypher;
    }, 150);
  }

  function setGraphStatus(text) {
    const el = document.getElementById('graph-status');
    if (el) el.textContent = text;
  }


  function renderCypherGeneral() {
    const el = document.getElementById('cypher-general');
    const queries = [
      {
        title: '🔍 Все публикации и их авторские ключевые слова',
        code: `MATCH (d:Document)-[r:HAS_KEYWORD {method: 'author'}]->(k:Keyword)\nRETURN d.title AS publication, collect(k.name) AS author_keywords\nORDER BY d.title`,
        viz: `MATCH path=(d:Document)-[r:HAS_KEYWORD {method: 'author'}]->(k:Keyword)\nRETURN path`
      },
      {
        title: '📊 Топ-10 самых частых ключевых слов',
        code: `MATCH (k:Keyword)<-[:HAS_KEYWORD]-(d:Document)\nRETURN k.name AS keyword, count(DISTINCT d) AS pub_count\nORDER BY pub_count DESC\nLIMIT 10`,
        viz: `MATCH (k:Keyword)<-[:HAS_KEYWORD]-(d:Document)\nWITH k, count(DISTINCT d) AS pub_count\nORDER BY pub_count DESC\nLIMIT 10\nMATCH path=(k)<-[r:HAS_KEYWORD]-(d2:Document)\nRETURN path`
      },
      {
        title: '🔗 Пары публикаций с общими терминами (от 2 общих слов)',
        code: `MATCH (d1:Document)-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)\nWHERE d1.id < d2.id\nWITH d1, d2, collect(k.name) AS shared, count(k) AS shared_count\nWHERE shared_count >= 2\nRETURN d1.title AS pub1, d2.title AS pub2, shared, shared_count\nORDER BY shared_count DESC\nLIMIT 15`,
        viz: `MATCH (d1:Document)-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)\nWHERE d1.id < d2.id\nWITH d1, d2, count(k) AS shared_count\nWHERE shared_count >= 2\nORDER BY shared_count DESC\nLIMIT 10\nMATCH path=(d1)-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2)\nRETURN path`
      },
      {
        title: '📄 Публикации с наибольшим количеством ключевых слов',
        code: `MATCH (d:Document)-[:HAS_KEYWORD]->(k:Keyword)\nRETURN d.title AS publication, count(k) AS keyword_count\nORDER BY keyword_count DESC\nLIMIT 10`,
        viz: `MATCH (d:Document)-[:HAS_KEYWORD]->(k:Keyword)\nWITH d, count(k) AS keyword_count\nORDER BY keyword_count DESC\nLIMIT 10\nMATCH path=(d)-[:HAS_KEYWORD]->(k2:Keyword)\nRETURN path`
      },
      {
        title: '🔎 Поиск через граф: найти статьи по термину',
        code: `// Замените 'нейрон' на нужный запрос:\nMATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword)\nWHERE toLower(k.name) CONTAINS 'нейрон'\nRETURN d.title AS publication, k.name AS found_keyword, r.method AS method\nORDER BY d.title`,
        viz: `MATCH path=(d:Document)-[r:HAS_KEYWORD]->(k:Keyword)\nWHERE toLower(k.name) CONTAINS 'нейрон'\nRETURN path`
      },
      {
        title: '👤 Сравнение авторских vs. извлечённых ключевых слов',
        code: `MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword)\nWITH d, r.method AS method, collect(k.name) AS keywords\nRETURN d.title AS publication, method, keywords\nORDER BY d.title, method`,
        viz: `MATCH path=(d:Document)-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN path LIMIT 100`
      },
    ];

    el.innerHTML = queries.map(q => renderCypherBlock(q.title, q.code, q.viz)).join('');
    bindCopyButtons(el);
  }

  function renderCypherSearch(query) {
    const el = document.getElementById('cypher-results');
    if (!query || query.length < 2) { el.innerHTML = ''; return; }

    Promise.all([
      fetchJSON(`/api/publications?q=${encodeURIComponent(query)}&per_page=5`),
      fetchJSON(`/api/keywords?q=${encodeURIComponent(query)}&per_page=5`),
    ]).then(([pubData, kwData]) => {
      const matchedPubs = pubData.items || [];
      const matchedKws = kwData.items || [];

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
          const pub = matchedPubs.find(p => p.id === pubId);
          if (!pub) return;
          el.innerHTML = `
            <div class="cypher-section">
              <h3 class="cypher-section-title">📄 ${esc(pub.title)}</h3>
              ${renderCypherBlock('Все ключевые слова',
                `MATCH (d:Document {id: '${escCypher(pubId)}'})-[r:HAS_KEYWORD]->(k:Keyword)\nRETURN k.name AS keyword, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`)}
              ${renderCypherBlock('Похожие публикации',
                `MATCH (d1:Document {id: '${escCypher(pubId)}'})-[r:SIMILAR_TO]-(d2:Document)\nRETURN d2.title AS similar, r.score AS jaccard\nORDER BY r.score DESC`)}
              ${renderCypherBlock('Публикации с общими терминами',
                `MATCH (d1:Document {id: '${escCypher(pubId)}'})-[:HAS_KEYWORD]->(k:Keyword)<-[:HAS_KEYWORD]-(d2:Document)\nWHERE d1 <> d2\nRETURN d2.title AS related, collect(k.name) AS shared, count(k) AS cnt\nORDER BY cnt DESC`)}
            </div>`;
          bindCopyButtons(el);
        });
      });

      el.querySelectorAll('[data-cypher-kw]').forEach(card => {
        card.addEventListener('click', () => {
          const kwId = card.dataset.cypherKw;
          const kw = matchedKws.find(k => k.id === kwId);
          if (!kw) return;
          el.innerHTML = `
            <div class="cypher-section">
              <h3 class="cypher-section-title">🏷️ ${esc(kw.name)}</h3>
              ${renderCypherBlock('Все публикации с этим термином',
                `MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN d.title AS publication, r.method AS method, r.weight AS weight\nORDER BY r.method, r.weight DESC`)}
              ${renderCypherBlock('Визуализация: термин и публикации',
                `MATCH (d:Document)-[r:HAS_KEYWORD]->(k:Keyword {id: '${escCypher(kwId)}'})\nRETURN d, r, k`)}
            </div>`;
          bindCopyButtons(el);
        });
      });
    }).catch(err => {
      console.error('Cypher search error:', err);
      el.innerHTML = '<div class="empty-state"><p>Ошибка поиска</p></div>';
    });
  }

  function renderCypherBlock(title, code, vizCypher) {
    const highlighted = highlightCypher(code);
    const id = 'cypher-' + Math.random().toString(36).slice(2, 9);
    return `
      <div class="cypher-block">
        <div class="cypher-block-header">
          <span class="cypher-block-title">${title}</span>
          <div class="cypher-block-actions">
            <button class="cypher-viz-btn" data-viz-target="${id}" title="Визуализировать на графе">▶ Граф</button>
            <button class="cypher-copy-btn" data-copy-target="${id}">📋 Копировать</button>
          </div>
        </div>
        <pre class="cypher-code" id="${id}">${highlighted}</pre>
        <textarea style="display:none" id="${id}-raw">${esc(code)}</textarea>
        <textarea style="display:none" id="${id}-viz">${esc(vizCypher || '')}</textarea>
      </div>`;
  }

  function highlightCypher(code) {
    let s = esc(code);
    s = s.replace(/(\/\/.*)/g, '<span class="cy-comment">$1</span>');
    const kwds = ['MATCH', 'RETURN', 'WHERE', 'ORDER BY', 'LIMIT', 'WITH', 'CREATE', 'MERGE', 'SET', 'UNWIND',
      'OPTIONAL MATCH', 'DETACH DELETE', 'DELETE', 'AS', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
      'DESC', 'ASC', 'DISTINCT', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'count', 'collect',
      'toFloat', 'toLower', 'id', 'IF NOT EXISTS', 'FOR', 'REQUIRE', 'IS UNIQUE', 'CONSTRAINT', 'CONTAINS', 'SKIP'];
    kwds.sort((a, b) => b.length - a.length);
    kwds.forEach(kw => {
      const re = new RegExp('\\b(' + kw.replace(/\s+/g, '\\s+') + ')\\b', 'gi');
      s = s.replace(re, '<span class="cy-keyword">$1</span>');
    });
    s = s.replace(/:([A-Z][A-Za-z_]*)/g, ':<span class="cy-label">$1</span>');
    s = s.replace(/\[([^\]]*?)]/g, (match) => match.replace(/:([A-Z_]+)/g, ':<span class="cy-rel">$1</span>'));
    s = s.replace(/(\w+):/g, '<span class="cy-prop">$1</span>:');
    s = s.replace(/&#39;([^&#]*(?:&#[^;]*;[^&#]*)*)&#39;/g, '<span class="cy-string">\'$1\'</span>');
    return s;
  }

  function bindCopyButtons(container) {
    container.querySelectorAll('.cypher-copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const rawEl = document.getElementById(btn.dataset.copyTarget + '-raw');
        if (!rawEl) return;
        navigator.clipboard.writeText(rawEl.value).then(() => {
          btn.classList.add('copied');
          btn.innerHTML = '✅ Скопировано';
          setTimeout(() => { btn.classList.remove('copied'); btn.innerHTML = '📋 Копировать'; }, 2000);
        });
      });
    });

    container.querySelectorAll('.cypher-viz-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.dataset.vizTarget;
        const vizEl = document.getElementById(targetId + '-viz');
        if (vizEl && vizEl.value.trim()) {
          showOnGraph(vizEl.value);
          return;
        }
        const rawEl = document.getElementById(targetId + '-raw');
        if (!rawEl) return;
        let cypher = rawEl.value;
        if (/RETURN\s+\w+\.\w+\s+AS/i.test(cypher)) {
          const matchPart = cypher.match(/(MATCH\s+)(\(.+?)(?:\s+(?:WITH|RETURN))/is);
          if (matchPart) {
            cypher = matchPart[1] + 'path=' + matchPart[2] + '\nRETURN path\nLIMIT 100';
          }
        }
        showOnGraph(cypher);
      });
    });
  }

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

  function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function escCypher(str) { return String(str).replace(/'/g, "\\'"); }

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

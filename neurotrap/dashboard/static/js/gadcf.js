'use strict';

const ASSET_META = {
  env_file:    { icon:'fa-file-shield',  color:'#ef4444', bg:'rgba(239,68,68,0.12)'    },
  email_thread:{ icon:'fa-envelope',     color:'#f59e0b', bg:'rgba(245,158,11,0.12)'   },
  code_repo:   { icon:'fa-code',         color:'#00d4ff', bg:'rgba(0,212,255,0.12)'    },
  wiki_page:   { icon:'fa-book',         color:'#8b5cf6', bg:'rgba(139,92,246,0.12)'   },
  db_schema:   { icon:'fa-database',     color:'#10b981', bg:'rgba(16,185,129,0.12)'   },
};

let _assets = [];
let _selectedIndustry = 'financial_services';
let _selectedIntent   = 'credential_harvesting';
let _selectedSoph     = 2;

document.addEventListener('DOMContentLoaded', () => {
  loadAssets();
  initOptionButtons();
  document.getElementById('sophistication-range').addEventListener('input', e => {
    _selectedSoph = parseInt(e.target.value);
  });
});

function initOptionButtons() {
  document.querySelectorAll('#industry-options .gadcf-opt').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#industry-options .gadcf-opt').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      _selectedIndustry = btn.dataset.val;
    });
  });
  document.querySelectorAll('#intent-options .gadcf-opt').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#intent-options .gadcf-opt').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      _selectedIntent = btn.dataset.val;
    });
  });
}

async function loadAssets() {
  const res  = await fetch('/api/gadcf/assets').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  _assets = data.assets || [];
  renderAssets(_assets);
  document.getElementById('kpi-assets-total').textContent = _assets.length;
  const hasLLM = _assets.some(a => a.source === 'llm');
  const llmEl = document.getElementById('kpi-llm-status');
  llmEl.textContent = hasLLM ? 'Ollama' : 'Templates';
  llmEl.style.color  = hasLLM ? '#10b981' : '#64748b';
}

async function generateAssets() {
  const btn    = document.getElementById('gen-btn');
  const status = document.getElementById('gen-status');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating…';
  status.textContent = '';
  status.style.color = 'var(--text-dim)';

  const sophValues = ['beginner', 'automated_bot', 'advanced_human'];
  try {
    const res  = await fetch('/api/gadcf/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ industry: _selectedIndustry, intent: _selectedIntent, sophistication: sophValues[_selectedSoph] }),
    });
    const data = await res.json();
    if (data.assets) {
      _assets = [...data.assets, ..._assets];
      renderAssets(_assets);
      document.getElementById('kpi-assets-total').textContent = _assets.length;
      status.textContent = `✓ ${data.count} assets generated (${data.assets[0]?.source || 'template'})`;
      status.style.color = '#10b981';
      // Auto-preview first asset
      if (data.assets[0]) selectAsset(data.assets[0], document.querySelector('.gadcf-asset-card'));
    }
  } catch (e) {
    status.textContent = '✗ Generation failed';
    status.style.color = '#ef4444';
  }
  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Asset Package';
}

function renderAssets(assets) {
  const el    = document.getElementById('gadcf-assets-container');
  const count = document.getElementById('assets-count');
  if (!el) return;
  count.textContent = `${assets.length} assets`;
  if (!assets.length) {
    el.innerHTML = '<div class="preview-placeholder" style="padding:40px"><i class="fa-solid fa-folder-open" style="font-size:28px;color:rgba(139,92,246,0.3);display:block;margin-bottom:12px"></i>Generate a package to see assets here</div>';
    return;
  }
  el.innerHTML = '';
  assets.slice(0, 30).forEach(a => {
    const meta  = ASSET_META[a.asset_type] || { icon:'fa-file', color:'#64748b', bg:'rgba(100,116,139,0.1)' };
    const isLLM = a.source === 'llm';
    const card  = document.createElement('div');
    card.className = 'gadcf-asset-card';
    card.onclick   = () => selectAsset(a, card);
    card.innerHTML = `
      <div class="gadcf-asset-card-icon" style="background:${meta.bg};color:${meta.color}">
        <i class="fa-solid ${meta.icon}"></i>
      </div>
      <div style="flex:1;min-width:0">
        <div class="gadcf-asset-card-name">${a.filename || a.asset_type}</div>
        <div class="gadcf-asset-card-meta">${(a.industry||'').replace(/_/g,' ')} · ${(a.attacker_intent||'').replace(/_/g,' ')}</div>
      </div>
      <span class="gadcf-source-pill" style="background:${isLLM?'rgba(16,185,129,0.15)':'rgba(100,116,139,0.12)'};color:${isLLM?'#10b981':'#64748b'}">${isLLM?'LLM':'TMPL'}</span>
    `;
    el.appendChild(card);
  });
}

function selectAsset(asset, cardEl) {
  document.querySelectorAll('.gadcf-asset-card').forEach(c => c.classList.remove('selected'));
  if (cardEl) cardEl.classList.add('selected');
  document.getElementById('preview-filename').textContent = asset.filename || '';
  const area = document.getElementById('gadcf-preview-area');
  area.textContent = asset.content || '(no content)';
  area.style.color  = '#e2e8f0';
  // Syntax highlighting hint — just color keywords
  highlightPreview(area, asset.asset_type);
}

function highlightPreview(el, assetType) {
  if (assetType === 'env_file') {
    el.innerHTML = el.textContent.replace(/^(#.*)$/gm, '<span style="color:#475569">$1</span>')
      .replace(/^([A-Z_]+)(=)/gm, '<span style="color:#f59e0b">$1</span><span style="color:#64748b">$2</span>');
  } else if (assetType === 'code_repo') {
    el.innerHTML = el.textContent.replace(/(#.*)/g, '<span style="color:#475569">$1</span>')
      .replace(/(".*?")/g, '<span style="color:#10b981">$1</span>');
  }
}

function timeSince(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  return `${Math.floor(s/3600)}h ago`;
}

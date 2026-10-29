// LinkIntel AI - Interactive Frontend Controller

let allDiscoveredProspects = [];
let currentCategory = "";

document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupNichePresets();
  setupAnalyzeForm();
  setupBacklinkVerifier();
  setupCsvImporter();
  setupModals();
  loadScanHistory();
});

// Tab Navigation
function setupNavigation() {
  const navBtns = document.querySelectorAll('.nav-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      navBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');

      if (targetId === 'tab-history') {
        loadScanHistory();
      }
    });
  });
}

// Niche Preset Selector
function setupNichePresets() {
  const presetSelect = document.getElementById('niche_preset');
  const categoryInput = document.getElementById('category');
  const keywordsInput = document.getElementById('keywords');
  if (!presetSelect) return;

  const presets = {
    health: {
      category: "physiotherapy",
      keywords: "sports injury clinic, rehabilitation, wellness, physical therapy"
    },
    software: {
      category: "software",
      keywords: "developer tools, open source, productivity, devops"
    },
    ecommerce: {
      category: "ecommerce",
      keywords: "d2c, online store, retail products, shopping directory"
    },
    finance: {
      category: "fintech",
      keywords: "accounting, investing, wealth management, personal finance"
    },
    realestate: {
      category: "real estate",
      keywords: "property listing, commercial real estate, architecture"
    },
    legal: {
      category: "legal services",
      keywords: "law firm, attorneys, corporate counsel, legal directory"
    },
    education: {
      category: "education",
      keywords: "online courses, edtech, university resources, tutoring"
    },
    marketing: {
      category: "digital marketing",
      keywords: "seo tools, branding, design agency, social media"
    },
    fitness: {
      category: "fitness",
      keywords: "personal trainer, gyms, athletic coaching, sports nutrition"
    },
    custom: {
      category: "",
      keywords: ""
    }
  };

  presetSelect.addEventListener('change', () => {
    const val = presetSelect.value;
    if (presets[val]) {
      if (val !== 'custom') {
        categoryInput.value = presets[val].category;
        keywordsInput.value = presets[val].keywords;
      } else {
        categoryInput.value = '';
        keywordsInput.value = '';
        categoryInput.focus();
      }
    }
  });
}

// Tab 1: Analyze & Discover 100 Backlinks
function setupAnalyzeForm() {
  const form = document.getElementById('analyze-form');
  const submitBtn = document.getElementById('analyze-submit-btn');
  const resultsContainer = document.getElementById('analyze-results-container');
  const tbody = document.getElementById('analyze-tbody');
  const summaryBox = document.getElementById('analyze-summary');

  const progressWidget = document.getElementById('scan-progress-widget');
  const progressStage = document.getElementById('scan-progress-stage');
  const progressPercent = document.getElementById('scan-progress-percent');
  const progressBar = document.getElementById('scan-progress-bar');
  const progressDetails = document.getElementById('scan-progress-details');
  const progressId = document.getElementById('scan-progress-id');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const websiteUrl = document.getElementById('website_url').value.trim();
    const category = document.getElementById('category').value.trim();
    const country = document.getElementById('country').value.trim();
    const keywordsRaw = document.getElementById('keywords').value.trim();
    const provider = document.getElementById('provider').value;
    const targetCount = parseInt(document.getElementById('target_count').value, 10) || 100;
    const useDeepLearning = document.getElementById('use_deep_learning').checked;

    const keywords = keywordsRaw ? keywordsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> Dispatching async discovery worker...`;
    resultsContainer.style.display = 'none';

    if (progressWidget) {
      progressWidget.style.display = 'block';
      progressPercent.textContent = '0%';
      progressBar.style.width = '5%';
      progressStage.textContent = 'Enqueuing scan job...';
      progressDetails.textContent = 'Dispatching concurrent worker across web buckets...';
      progressId.textContent = '';
    }

    try {
      const response = await fetch('/api/v1/analyze?sync=false', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          website_url: websiteUrl,
          category,
          country,
          keywords,
          provider,
          target_count: targetCount,
          use_deep_learning: useDeepLearning,
          sync: false
        })
      });

      const initialData = await response.json();
      if (!response.ok) {
        throw new Error(initialData.detail || 'Analysis failed to start.');
      }

      if (response.status === 200) {
        // Synchronous response
        if (progressPercent) progressPercent.textContent = '100%';
        if (progressBar) progressBar.style.width = '100%';
        if (progressStage) progressStage.textContent = 'Scan complete!';
        allDiscoveredProspects = initialData.prospects || [];
        currentCategory = initialData.category || category;
        renderAnalysisResults(initialData, tbody, summaryBox);
        resultsContainer.style.display = 'block';
        if (progressWidget) {
          setTimeout(() => { progressWidget.style.display = 'none'; }, 1000);
        }
        loadScanHistory();
        return;
      }

      // Asynchronous job (202 Accepted)
      const scanId = initialData.scan_id;
      if (progressId) progressId.textContent = `Scan ID: ${scanId.substring(0, 8)}...`;
      if (progressStage) progressStage.textContent = initialData.stage || 'Scan in progress...';

      // Connect to Server-Sent Events (SSE) stream
      await listenToScanStream(scanId, category, tbody, summaryBox, resultsContainer, progressWidget, progressStage, progressPercent, progressBar, progressDetails);
      loadScanHistory();

    } catch (err) {
      alert(`Error: ${err.message}`);
      if (progressWidget) progressWidget.style.display = 'none';
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `🚀 Find 100 Backlinks (Live Web, Image &amp; PDF)`;
    }
  });

  // Setup filter pills
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const filter = pill.getAttribute('data-filter');
      filterProspects(filter, tbody);
    });
  });
}

function listenToScanStream(scanId, fallbackCategory, tbody, summaryBox, resultsContainer, progressWidget, progressStage, progressPercent, progressBar, progressDetails) {
  return new Promise((resolve) => {
    let eventSource = null;
    let pollInterval = null;
    let completed = false;

    const cleanup = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
    };

    const finishSuccess = async () => {
      if (completed) return;
      completed = true;
      cleanup();
      try {
        const res = await fetch(`/api/v1/scans/${scanId}`);
        if (res.ok) {
          const scanRecord = await res.json();
          const payload = scanRecord.payload || {};
          allDiscoveredProspects = payload.prospects || [];
          currentCategory = payload.category || fallbackCategory;
          renderAnalysisResults(payload, tbody, summaryBox);
          resultsContainer.style.display = 'block';
        }
      } catch (e) {
        console.error('Error fetching completed scan:', e);
      }
      if (progressWidget) {
        setTimeout(() => {
          progressWidget.style.display = 'none';
        }, 1200);
      }
      resolve();
    };

    const finishFailure = (errMsg) => {
      if (completed) return;
      completed = true;
      cleanup();
      if (progressStage) progressStage.textContent = `Error: ${errMsg}`;
      if (progressPercent) progressPercent.textContent = 'Failed';
      if (progressBar) progressBar.style.background = '#ef4444';
      alert(`Scan failed: ${errMsg}`);
      resolve();
    };

    if (window.EventSource) {
      eventSource = new EventSource(`/api/v1/scans/${scanId}/stream`);

      eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          const pct = Math.max(0, Math.min(100, data.progress || 0));
          if (progressPercent) progressPercent.textContent = `${pct}%`;
          if (progressBar) progressBar.style.width = `${pct}%`;
          if (progressStage && data.stage) progressStage.textContent = data.stage;
          if (progressDetails && data.found_count) progressDetails.textContent = `Found ${data.found_count} candidate backlinks so far...`;

          if (data.status === 'completed' || pct >= 100) {
            finishSuccess();
          } else if (data.status === 'failed') {
            finishFailure(data.error_message || data.stage || 'Scan processing failed.');
          }
        } catch (err) {
          console.warn('SSE parse error:', err);
        }
      };

      eventSource.onerror = () => {
        // Fallback to polling if SSE connection drops or is blocked
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        startPolling();
      };
    } else {
      startPolling();
    }

    function startPolling() {
      if (completed || pollInterval) return;
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/v1/scans/${scanId}/status`);
          if (res.ok) {
            const data = await res.json();
            const pct = Math.max(0, Math.min(100, data.progress || 0));
            if (progressPercent) progressPercent.textContent = `${pct}%`;
            if (progressBar) progressBar.style.width = `${pct}%`;
            if (progressStage && data.stage) progressStage.textContent = data.stage;
            if (progressDetails && data.prospects_found) progressDetails.textContent = `Found ${data.prospects_found} candidate backlinks so far...`;

            if (data.status === 'completed' || pct >= 100) {
              finishSuccess();
            } else if (data.status === 'failed') {
              finishFailure(data.error_message || 'Scan failed.');
            }
          }
        } catch (err) {
          console.warn('Poll error:', err);
        }
      }, 1500);
    }
  });
}

function filterProspects(filter, tbody) {
  let filtered = allDiscoveredProspects;
  if (filter === 'pdf') {
    filtered = allDiscoveredProspects.filter(p => (p.link_type || '').toLowerCase().includes('pdf'));
  } else if (filter === 'image') {
    filtered = allDiscoveredProspects.filter(p => (p.link_type || '').toLowerCase().includes('image') || (p.link_type || '').toLowerCase().includes('infographic'));
  } else if (filter === 'directory') {
    filtered = allDiscoveredProspects.filter(p => (p.link_type || '').toLowerCase().includes('directory') || (p.link_type || '').toLowerCase().includes('catalog'));
  } else if (filter === 'free') {
    filtered = allDiscoveredProspects.filter(p => p.cost_status === 'verified_free');
  }

  renderProspectRows(filtered, tbody, currentCategory);
}

function renderAnalysisResults(data, tbody, summaryBox) {
  const { scan_id, website_domain, category, prospects_found, verified_free_count, pending_verification_count, prospects, warnings } = data;

  // Wire export links to the active scan
  const xlsxBtn = document.getElementById('export-xlsx-btn');
  const csvBtn = document.getElementById('export-csv-btn');
  const jsonBtn = document.getElementById('export-json-btn');
  if (xlsxBtn) xlsxBtn.href = `/api/v1/export/xlsx/${scan_id}`;
  if (csvBtn) csvBtn.href = `/api/v1/export/csv/${scan_id}`;
  if (jsonBtn) jsonBtn.href = `/api/v1/export/json/${scan_id}`;

  // Update counts
  const pdfCount = prospects.filter(p => (p.link_type || '').toLowerCase().includes('pdf')).length;
  const imgCount = prospects.filter(p => (p.link_type || '').toLowerCase().includes('image') || (p.link_type || '').toLowerCase().includes('infographic')).length;
  const dirCount = prospects.filter(p => (p.link_type || '').toLowerCase().includes('directory') || (p.link_type || '').toLowerCase().includes('catalog')).length;

  document.getElementById('count-all').innerText = prospects.length;
  document.getElementById('count-pdf').innerText = pdfCount;
  document.getElementById('count-image').innerText = imgCount;
  document.getElementById('count-directory').innerText = dirCount;
  document.getElementById('count-free').innerText = verified_free_count;

  summaryBox.innerHTML = `
    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center; margin-bottom: 0.5rem;">
      <div><strong>Domain:</strong> <span style="color: var(--cyan);">${escapeHtml(website_domain)}</span></div>
      <div><strong>Niche:</strong> <span style="color: var(--cyan);">${escapeHtml(category)}</span></div>
      <div><strong>Backlinks Found:</strong> <span style="color: #67e8f9; font-weight: 700;">${prospects_found}</span></div>
      <div><span class="badge badge-verified-free">✓ ${verified_free_count} Verified Free</span></div>
      <div><span class="badge badge-pending">⏱ ${pending_verification_count} Unverified Terms</span></div>
    </div>
    ${warnings && warnings.length ? `
      <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--amber); padding: 0.6rem 0.9rem; font-size: 0.85rem; border-radius: 4px; color: #fde68a; margin-top: 0.75rem;">
        ${warnings.map(w => `<div>• ${escapeHtml(w)}</div>`).join('')}
      </div>
    ` : ''}
  `;

  renderProspectRows(prospects, tbody, category);
}

function renderProspectRows(prospects, tbody, category) {
  tbody.innerHTML = '';
  if (!prospects.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 2rem;">No backlinks matched this filter.</td></tr>';
    return;
  }

  prospects.forEach(p => {
    const scoreVal = p.score.opportunity_score;
    const scoreClass = scoreVal === null ? 'score-na' : (scoreVal >= 70 ? 'score-high' : 'score-med');
    const scoreDisplay = scoreVal !== null ? scoreVal : 'N/A';

    const costBadgeClass = p.cost_status === 'verified_free' ? 'badge-verified-free' : 
                          (p.cost_status === 'paid' ? 'badge-paid' : 'badge-pending');

    const liveUrl = p.page_url || ('https://' + p.domain);

    // Format Link Type badge
    let linkTypeBadge = `<span class="badge" style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a5b4fc;">${escapeHtml(p.link_type || '🌐 Directory')}</span>`;
    if ((p.link_type || '').includes('PDF')) {
      linkTypeBadge = `<span class="badge" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #fca5a5;">📄 PDF Doc</span>`;
    } else if ((p.link_type || '').includes('Image') || (p.link_type || '').includes('Infographic')) {
      linkTypeBadge = `<span class="badge" style="background: rgba(168, 85, 247, 0.15); border: 1px solid rgba(168, 85, 247, 0.3); color: #d8b4fe;">🖼️ Infographic</span>`;
    }

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>
        <div class="domain-cell">
          <a href="${escapeHtml(liveUrl)}" target="_blank" rel="noopener noreferrer" class="live-url-link" title="Open working webpage">
            🌐 ${escapeHtml(p.domain)} <span style="font-size: 0.75rem;">↗</span>
          </a>
          <span class="domain-sub">${escapeHtml(p.title || 'Live Resource Page')}</span>
          <a href="${escapeHtml(liveUrl)}" target="_blank" rel="noopener noreferrer" class="live-sub-link" title="Direct Live URL">
            🔗 ${escapeHtml(liveUrl.length > 45 ? liveUrl.substring(0, 45) + '...' : liveUrl)}
          </a>
        </div>
      </td>
      <td>${linkTypeBadge}</td>
      <td><span class="badge ${costBadgeClass}">${p.cost_status.replace('_', ' ')}</span></td>
      <td>
        <div class="score-pill ${scoreClass}">${scoreDisplay}</div>
      </td>
      <td>
        <div style="font-size: 0.78rem; line-height: 1.4; color: var(--text-muted);">
          <div>Relevance: <strong>${p.score.relevance ?? '—'}</strong></div>
          <div>Authority: <strong>${p.score.authority ?? '—'}</strong></div>
          <div>Spam Safety: <strong>${p.score.spam_risk !== null ? (100 - p.score.spam_risk) : '—'}</strong></div>
        </div>
      </td>
      <td>
        <button class="btn btn-sm btn-ai explain-btn" 
          data-domain="${escapeHtml(p.domain)}"
          data-category="${escapeHtml(category)}"
          data-evidence='${JSON.stringify({
            authority: p.score.authority,
            relevance: p.score.relevance,
            cost_status: p.cost_status,
            link_type: p.link_type,
            reasons: p.reasons
          })}'>
          ✨ AI Pitch
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Re-attach AI Explanation Listeners
  document.querySelectorAll('.explain-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const domain = btn.getAttribute('data-domain');
      const cat = btn.getAttribute('data-category');
      const evidence = JSON.parse(btn.getAttribute('data-evidence'));
      openAiExplanationModal(domain, cat, evidence);
    });
  });
}

// AI Outreach & Explanation Modal (Calls Google Gemini)
async function openAiExplanationModal(domain, category, evidence) {
  const modal = document.getElementById('ai-modal');
  const title = document.getElementById('ai-modal-domain');
  const content = document.getElementById('ai-modal-body');

  title.innerText = `AI Prospect Analysis: ${domain}`;
  content.innerHTML = '<div style="text-align: center; padding: 2rem;"><span class="spinner"></span> Consulting Google Gemini intelligence engine...</div>';
  modal.classList.add('active');

  try {
    const res = await fetch('/api/v1/prospects/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain, category, evidence })
    });
    const data = await res.json();
    content.innerHTML = `
      <div class="pitch-box" id="pitch-text">${escapeHtml(data.explanation || 'No explanation generated.')}</div>
      <div style="display: flex; justify-content: flex-end; margin-top: 1rem;">
        <button class="btn btn-sm btn-secondary" id="copy-pitch-btn">📋 Copy Pitch</button>
      </div>
    `;

    document.getElementById('copy-pitch-btn').addEventListener('click', () => {
      navigator.clipboard.writeText(data.explanation);
      alert('Outreach pitch copied to clipboard!');
    });
  } catch (err) {
    content.innerHTML = `<div style="color: var(--rose);">Failed to generate explanation: ${err.message}</div>`;
  }
}

// Tab 2: Real Backlink Verifier
function setupBacklinkVerifier() {
  const form = document.getElementById('backlink-verify-form');
  const submitBtn = document.getElementById('verify-submit-btn');
  const resultsCard = document.getElementById('verify-results-card');
  const tbody = document.getElementById('verify-tbody');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const urlsRaw = document.getElementById('verify_urls').value.trim();
    const targetDomain = document.getElementById('target_domain').value.trim();

    const urls = urlsRaw.split('\n').map(u => u.trim()).filter(Boolean);
    if (!urls.length) return alert('Please enter at least one URL.');

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Inspecting HTML...';

    try {
      const response = await fetch('/api/v1/backlinks/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls,
          target_domain: targetDomain || null
        })
      });

      const data = await response.json();
      tbody.innerHTML = '';

      data.results.forEach(r => {
        const tr = document.createElement('tr');
        const reachableBadge = r.reachable 
          ? `<span class="badge badge-verified-free">HTTP ${r.status_code || 200}</span>`
          : `<span class="badge badge-paid">Unreachable</span>`;

        let backlinkStatus = '<span style="color: var(--text-dim);">Not Checked</span>';
        if (r.backlink_found === true) {
          const dofollowBadge = r.is_dofollow 
            ? '<span class="badge badge-verified-free">dofollow</span>'
            : `<span class="badge badge-pending">${(r.rel || []).join(', ') || 'nofollow'}</span>`;
          backlinkStatus = `
            <div style="color: #34d399; font-weight: 600;">✓ Found</div>
            <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 0.2rem;">
              Anchor: "${escapeHtml(r.anchor_text || '')}"
            </div>
            <div style="margin-top: 0.25rem;">${dofollowBadge}</div>
          `;
        } else if (r.backlink_found === false) {
          backlinkStatus = '<span style="color: var(--rose); font-weight: 600;">✗ Missing</span>';
        }

        tr.innerHTML = `
          <td><div style="word-break: break-all; max-width: 320px;"><a href="${escapeHtml(r.url)}" target="_blank" class="live-url-link">🔗 ${escapeHtml(r.url)}</a></div></td>
          <td>${reachableBadge}</td>
          <td>${backlinkStatus}</td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(r.note || '')}</td>
        `;
        tbody.appendChild(tr);
      });

      resultsCard.style.display = 'block';
    } catch (err) {
      alert(`Error verifying backlinks: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Inspect &amp; Verify Backlinks';
    }
  });
}

// Tab 3: CSV Importer
function setupCsvImporter() {
  const dropzone = document.getElementById('csv-dropzone');
  const fileInput = document.getElementById('csv_file_input');
  const resultsCard = document.getElementById('csv-results-card');
  const tbody = document.getElementById('csv-tbody');

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      uploadCsv(e.dataTransfer.files[0], tbody, resultsCard);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
      uploadCsv(fileInput.files[0], tbody, resultsCard);
    }
  });
}

async function uploadCsv(file, tbody, resultsCard) {
  if (!file.name.endsWith('.csv')) {
    return alert('Please select a valid .csv file.');
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/v1/import/csv', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Import failed.');

    tbody.innerHTML = '';
    data.prospects.forEach(p => {
      const tr = document.createElement('tr');
      const scoreVal = p.score.opportunity_score ?? 'N/A';
      tr.innerHTML = `
        <td><strong>${escapeHtml(p.domain)}</strong></td>
        <td><span class="badge ${p.cost_status === 'verified_free' ? 'badge-verified-free' : 'badge-pending'}">${p.cost_status}</span></td>
        <td><strong>${scoreVal}</strong></td>
        <td style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml((p.reasons || []).join(' | '))}</td>
      `;
      tbody.appendChild(tr);
    });

    resultsCard.style.display = 'block';
  } catch (err) {
    alert(`CSV Upload Error: ${err.message}`);
  }
}

// Tab 4: Scan History Archive
async function loadScanHistory() {
  const tbody = document.getElementById('history-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/v1/scans?limit=50');
    const data = await res.json();

    if (!data.scans.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 2rem;">No past scans found in SQLite archive.</td></tr>';
      return;
    }

    tbody.innerHTML = '';
    data.scans.forEach(s => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><span style="font-family: monospace; font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(s.scan_id.substring(0, 8))}...</span></td>
        <td><strong>${escapeHtml(s.website_domain)}</strong></td>
        <td><span class="badge badge-pending">${escapeHtml(s.category)}</span></td>
        <td>${s.prospects_found} (${s.verified_free_count} free)</td>
        <td style="font-size: 0.8rem; color: var(--text-dim);">${new Date(s.created_at).toLocaleString()}</td>
        <td>
          <div style="display: flex; gap: 0.4rem;">
            <a href="/api/v1/export/xlsx/${s.scan_id}" class="btn btn-sm btn-secondary" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3);" title="Download Excel (.xlsx)">📊 Excel</a>
            <a href="/api/v1/export/csv/${s.scan_id}" class="btn btn-sm btn-secondary" title="Download CSV">📥 CSV</a>
            <a href="/api/v1/export/json/${s.scan_id}" class="btn btn-sm btn-secondary" title="Download JSON" target="_blank">JSON</a>
            <button class="btn btn-sm btn-secondary delete-scan-btn" data-id="${s.scan_id}" style="color: var(--rose);" title="Delete Scan">🗑</button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });

    document.querySelectorAll('.delete-scan-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        if (confirm(`Delete scan ${id.substring(0, 8)}?`)) {
          await fetch(`/api/v1/scans/${id}`, { method: 'DELETE' });
          loadScanHistory();
        }
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: var(--rose); padding: 1rem;">Failed to load scan history: ${err.message}</td></tr>`;
  }
}

function setupModals() {
  const modal = document.getElementById('ai-modal');
  const closeBtn = document.getElementById('ai-modal-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => modal.classList.remove('active'));
  }
  window.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

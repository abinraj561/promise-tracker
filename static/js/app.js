/**
 * PROMISE TRACKER - FRONTEND APPLICATION
 * Handles state, real-time filtering, AI promise extraction, WhatsApp chat simulation,
 * morning dispatch generation, and modal workflows.
 */

// --- Global State ---
const state = {
  currentTab: 'dashboard',
  theme: localStorage.getItem('pt_theme') || 'dark',
  filters: {
    status: 'all',
    direction: 'all',
    category: 'all',
    responsible: 'all',
    search: ''
  },
  promises: [],
  summary: {},
  currentPreset: 'furniture',
  extractedCandidates: [],
  team: []
};

// --- Industry Presets ---
const PRESETS = {
  furniture: {
    customerName: "Shihab",
    phone: "+91 98451 22334",
    avatar: "S",
    chat: [
      { sender: "Shihab", isCustomer: true, text: "Can you deliver the solid teak dining table by Friday?", time: "10:14 AM" },
      { sender: "Owner", isCustomer: false, text: "Yes, Friday evening definitely. Sameer will bring it by 6 PM.", time: "10:18 AM" }
    ]
  },
  agency: {
    customerName: "Rahul Verma",
    phone: "+91 98112 33445",
    avatar: "R",
    chat: [
      { sender: "Rahul", isCustomer: true, text: "Okay bro, I'll pay ₹20k tomorrow and you send the design by Monday.", time: "02:30 PM" },
      { sender: "Agency", isCustomer: false, text: "Done bro! Priya will send invoice and Rahul will share Figma links Monday.", time: "02:35 PM" }
    ]
  },
  interior: {
    customerName: "Ananya Sharma",
    phone: "+91 99234 55667",
    avatar: "A",
    chat: [
      { sender: "Ananya", isCustomer: true, text: "Need the 3D living room renders before our architect meeting on Thursday 5 PM.", time: "11:20 AM" },
      { sender: "Designer", isCustomer: false, text: "Noted Ananya! We'll email the 4K renders Thursday 4:30 PM sharp.", time: "11:45 AM" }
    ]
  },
  repair: {
    customerName: "Deepak Nair",
    phone: "+91 97456 77889",
    avatar: "D",
    chat: [
      { sender: "Deepak", isCustomer: true, text: "Can you replace my iPhone screen and battery before 5 PM today?", time: "01:10 PM" },
      { sender: "Arjun (Technician)", isCustomer: false, text: "Yes sir, your phone will be ready by 4 PM today.", time: "01:15 PM" }
    ]
  },
  clinic: {
    customerName: "Dr. Meenakshi Sundaram",
    phone: "+91 98800 11223",
    avatar: "M",
    chat: [
      { sender: "Dr. Meenakshi", isCustomer: true, text: "Please send the complete blood panel and lipid profile report by tomorrow 11 AM.", time: "04:45 PM" },
      { sender: "Clinic Coordinator", isCustomer: false, text: "Yes doctor, the lab report will be sent to your WhatsApp tomorrow 11:00 AM.", time: "05:00 PM" }
    ]
  },
  wedding: {
    customerName: "Pooja & Rohan",
    phone: "+91 98991 22334",
    avatar: "P",
    chat: [
      { sender: "Pooja", isCustomer: true, text: "Hi! Can you deliver the wedding teaser album within 48 hours?", time: "09:00 AM" },
      { sender: "Studio Manager", isCustomer: false, text: "Hi Pooja! Absolutely, the edited teaser gallery will be ready by Saturday 6 PM.", time: "09:20 AM" }
    ]
  },
  contractor: {
    customerName: "Sunil Hegde",
    phone: "+91 97312 44556",
    avatar: "S",
    chat: [
      { sender: "Sunil", isCustomer: true, text: "Please finish the kitchen tile work and plumbing check by Wednesday.", time: "08:15 AM" },
      { sender: "Vikram (Site Eng)", isCustomer: false, text: "Understood Sunil. Vikram will inspect and complete handover by Wednesday 4 PM.", time: "08:30 AM" }
    ]
  }
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  applyTheme(state.theme);
  setupNavigation();
  setupFilters();
  setupModals();
  setupChatSimulator();
  setupMorningDispatch();
  setupWebhookSimulator();
  setupIntegrationsHub();
  
  // Initial Data Load
  fetchSummary();
  fetchPromises();
  fetchTeam();
  fetchIntegrationConfig();

  // Polling for live time updates every 60s
  setInterval(() => {
    fetchSummary();
    fetchPromises();
  }, 60000);
});

// --- Theme Toggling ---
function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('pt_theme', theme);
  
  const icon = document.getElementById('theme-icon');
  const text = document.getElementById('theme-text');
  if (theme === 'light') {
    icon.textContent = '🌙';
    text.textContent = 'Switch to Dark Mode';
  } else {
    icon.textContent = '☀️';
    text.textContent = 'Switch to Light Mode';
  }
}

document.getElementById('theme-toggle-btn').addEventListener('click', () => {
  const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
  applyTheme(nextTheme);
});

// --- Toast Notifications ---
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : '⚠️'}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// --- Navigation ---
function setupNavigation() {
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const tabId = item.getAttribute('data-tab');
      switchTab(tabId);
    });
  });

  document.getElementById('banner-dispatch-btn').addEventListener('click', () => {
    switchTab('morning-briefing');
  });
}

function switchTab(tabId) {
  state.currentTab = tabId;
  document.querySelectorAll('.nav-item').forEach(nav => {
    nav.classList.toggle('active', nav.getAttribute('data-tab') === tabId);
  });
  document.querySelectorAll('.tab-view').forEach(view => {
    view.style.display = view.id === `view-${tabId}` ? 'block' : 'none';
  });

  if (tabId === 'dashboard') {
    fetchSummary();
    fetchPromises();
  } else if (tabId === 'morning-briefing') {
    fetchMorningDigest();
  } else if (tabId === 'team-board') {
    fetchTeam();
  } else if (tabId === 'integrations') {
    fetchIntegrationConfig();
  }
}

// --- API Calls & Dashboard Rendering ---
async function fetchSummary() {
  try {
    const res = await fetch('/api/dashboard/summary');
    const data = await res.json();
    state.summary = data;
    renderSummary(data);
  } catch (err) {
    console.error('Failed to fetch summary', err);
  }
}

function renderSummary(data) {
  document.getElementById('stat-overdue').textContent = data.overdue || 0;
  document.getElementById('stat-due-today').textContent = data.due_today || 0;
  document.getElementById('stat-pending').textContent = data.pending || 0;
  document.getElementById('stat-trust').textContent = `${data.reliability_rate || 98.4}%`;

  document.getElementById('sidebar-trust-score').textContent = `${data.reliability_rate || 98.4}%`;
  document.getElementById('sidebar-trust-fill').style.width = `${data.reliability_rate || 98.4}%`;

  const navBadge = document.getElementById('nav-due-today-badge');
  navBadge.textContent = `${data.due_today || 0} Due`;
  navBadge.className = `nav-badge ${(data.overdue > 0) ? 'badge-alert' : 'badge-warning'}`;

  // Update Morning Banner
  const banner = document.getElementById('morning-banner-container');
  const headline = document.getElementById('banner-headline');
  const icon = document.getElementById('banner-icon');

  if (data.overdue > 0) {
    icon.textContent = '🔴';
    headline.textContent = `CRITICAL: ${data.overdue} promise${data.overdue > 1 ? 's are' : ' is'} overdue & ${data.due_today} due today`;
    banner.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(245, 158, 11, 0.1) 100%)';
  } else if (data.due_today > 0) {
    icon.textContent = '⚠️';
    headline.textContent = `${data.due_today} customer promise${data.due_today > 1 ? 's are' : ' is'} due today`;
    banner.style.background = 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(239, 68, 68, 0.1) 100%)';
  } else {
    icon.textContent = '✨';
    headline.textContent = `All customer commitments are on schedule! (0 overdue)`;
    banner.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.1) 100%)';
  }
}

async function fetchPromises() {
  try {
    const params = new URLSearchParams(state.filters);
    const res = await fetch(`/api/promises?${params.toString()}`);
    const data = await res.json();
    state.promises = data.promises || [];
    renderPromises(state.promises);
  } catch (err) {
    console.error('Failed to fetch promises', err);
  }
}

function renderPromises(promises) {
  const container = document.getElementById('promises-grid');
  container.innerHTML = '';

  if (promises.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 60px 20px; text-align: center; color: var(--text-muted); background: var(--bg-card); border-radius: 16px; border: 1px dashed var(--border-glass);">
        <div style="font-size: 40px; margin-bottom: 12px;">🔍</div>
        <h3 style="font-size: 1.2rem; color: var(--text-main); margin-bottom: 6px;">No promises found</h3>
        <p>Try clearing filters or create a new customer promise.</p>
      </div>
    `;
    return;
  }

  promises.forEach(p => {
    const card = document.createElement('div');
    card.className = `promise-card status-${p.status}`;
    
    // Status Badge text & styling
    let statusLabel = '⏳ Pending';
    let statusClass = 'pending';
    if (p.status === 'overdue') {
      statusLabel = '🔴 Overdue';
      statusClass = 'overdue';
    } else if (p.status === 'due_today') {
      statusLabel = '⚠️ Due Today';
      statusClass = 'due_today';
    } else if (p.status === 'completed') {
      statusLabel = '✅ Fulfilled';
      statusClass = 'completed';
    } else if (p.status === 'renegotiated') {
      statusLabel = '🔄 Rescheduled';
      statusClass = 'renegotiated';
    }

    const isCustomerCommitment = p.direction === 'customer_to_business';
    const directionBadge = isCustomerCommitment 
      ? '<span class="direction-tag tag-incoming">📥 Client Commitment</span>'
      : '<span class="direction-tag tag-outgoing">📤 Our Deliverable</span>';

    const paymentPill = (p.payment_amount && p.payment_amount > 0)
      ? `<span style="font-family: var(--font-mono); font-weight: 700; color: #fbbf24; background: rgba(245, 158, 11, 0.15); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;">💰 ${p.currency}${p.payment_amount.toLocaleString()}</span>`
      : '';

    card.innerHTML = `
      <div>
        <div class="promise-top">
          <span class="promise-code">${p.promise_code}</span>
          <span class="status-badge ${statusClass}">${statusLabel}</span>
        </div>

        <div class="customer-info">
          <span class="customer-name">${p.customer_name}</span>
          ${directionBadge}
          ${paymentPill}
        </div>

        <div class="promise-body" style="margin-top: 12px;">
          <h4 class="promise-title">${p.title}</h4>
          <div class="promise-deliverable">
            ${p.deliverable}
          </div>
          ${p.proof_note ? `<div style="font-size: 0.775rem; color: #34d399; background: rgba(16, 185, 129, 0.1); padding: 6px 10px; border-radius: 6px;"><strong>Proof:</strong> ${p.proof_note}</div>` : ''}
          ${p.renegotiated_reason ? `<div style="font-size: 0.775rem; color: #a78bfa; background: rgba(139, 92, 246, 0.1); padding: 6px 10px; border-radius: 6px;"><strong>Rescheduled (${p.renegotiated_count}x):</strong> ${p.renegotiated_reason}</div>` : ''}
        </div>
      </div>

      <div>
        <div class="promise-meta">
          <div class="due-time">
            <span>📅</span>
            <span>${p.due_date_text || p.due_date}</span>
          </div>
          <div class="responsible-tag">
            <span class="avatar-dot"></span>
            <span>${p.responsible_person}</span>
          </div>
        </div>

        <div class="promise-actions">
          ${p.status !== 'completed' ? `
            <button class="btn btn-primary btn-sm btn-fulfill" data-id="${p.id}" data-title="${p.title}" data-customer="${p.customer_name}">
              <span>✅</span> Fulfill
            </button>
            <button class="btn btn-secondary btn-sm btn-renegotiate" data-id="${p.id}" data-title="${p.title}" data-date="${p.due_date}">
              <span>🔄</span> Reschedule
            </button>
          ` : ''}
          <button class="btn btn-whatsapp btn-sm btn-whatsapp-nudge" data-id="${p.id}" data-customer="${p.customer_name}" data-phone="${p.customer_phone}" data-title="${p.title}" data-due="${p.due_date_text || p.due_date}">
            <span>💬</span> Nudge
          </button>
          <button class="btn btn-secondary btn-sm btn-audit" data-id="${p.id}" title="Audit History">
            <span>📜</span>
          </button>
          <button class="btn btn-danger btn-sm btn-delete" data-id="${p.id}" title="Delete">
            <span>🗑️</span>
          </button>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  // Attach card event listeners
  container.querySelectorAll('.btn-fulfill').forEach(b => b.addEventListener('click', onOpenFulfillModal));
  container.querySelectorAll('.btn-renegotiate').forEach(b => b.addEventListener('click', onOpenRenegotiateModal));
  container.querySelectorAll('.btn-audit').forEach(b => b.addEventListener('click', onOpenAuditModal));
  container.querySelectorAll('.btn-whatsapp-nudge').forEach(b => b.addEventListener('click', onWhatsAppNudgeClick));
  container.querySelectorAll('.btn-delete').forEach(b => b.addEventListener('click', onDeletePromiseClick));
}

// --- Filters Setup ---
function setupFilters() {
  // Status Pills
  document.querySelectorAll('#status-filters .filter-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#status-filters .filter-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.filters.status = btn.getAttribute('data-status');
      fetchPromises();
    });
  });

  // Direction Pills
  document.querySelectorAll('#direction-filters .filter-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#direction-filters .filter-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.filters.direction = btn.getAttribute('data-direction');
      fetchPromises();
    });
  });

  // Category & Responsible Dropdowns
  document.getElementById('category-filter').addEventListener('change', (e) => {
    state.filters.category = e.target.value;
    fetchPromises();
  });

  document.getElementById('responsible-filter').addEventListener('change', (e) => {
    state.filters.responsible = e.target.value;
    fetchPromises();
  });

  // Search Input (debounced)
  let searchTimeout;
  document.getElementById('search-input').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = e.target.value.trim();
      fetchPromises();
    }, 250);
  });

  // Export CSV
  document.getElementById('btn-export-csv').addEventListener('click', () => {
    window.location.href = '/api/export/csv';
  });
}

// --- WhatsApp Chat Simulator & AI Extractor ---
function setupChatSimulator() {
  // Preset Chips
  document.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const presetKey = chip.getAttribute('data-preset');
      loadChatPreset(presetKey);
    });
  });

  // Load Initial Preset
  loadChatPreset('furniture');

  // Run AI Extraction Button
  document.getElementById('btn-run-extraction').addEventListener('click', runAiExtraction);

  // Save All Extracted Button
  document.getElementById('btn-save-all-extracted').addEventListener('click', saveAllExtracted);

  // Voice memo simulation
  document.getElementById('btn-audio-memo').addEventListener('click', simulateVoiceMemo);
}

function loadChatPreset(key) {
  state.currentPreset = key;
  const preset = PRESETS[key] || PRESETS.furniture;
  
  document.getElementById('sim-contact-name').textContent = `${preset.customerName} (Customer)`;
  document.getElementById('sim-contact-phone').textContent = `${preset.phone} • online`;
  document.getElementById('sim-avatar').textContent = preset.avatar;

  const stream = document.getElementById('chat-stream');
  stream.innerHTML = '';

  let rawChatText = '';
  preset.chat.forEach(msg => {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${msg.isCustomer ? 'customer' : 'business'}`;
    bubble.innerHTML = `
      <span class="bubble-sender">${msg.sender}</span>
      <span>${msg.text}</span>
      <span class="bubble-time">${msg.time}</span>
    `;
    stream.appendChild(bubble);
    rawChatText += `${msg.sender}: ${msg.text}\n`;
  });

  document.getElementById('custom-chat-input').value = rawChatText.trim();
}

function simulateVoiceMemo() {
  const voiceMemos = [
    "Audio Memo [Call with Shihab]: Shihab called to confirm delivery of 6-seater dining table by this Friday 6 PM. Sameer is assigned.",
    "Audio Memo [Site Call]: Sunil confirmed tiles need to be laid by Wednesday afternoon. Site engineer Vikram is handling.",
    "Audio Memo [Studio]: Pooja requested the wedding teaser video before Saturday evening."
  ];
  const randomMemo = voiceMemos[Math.floor(Math.random() * voiceMemos.length)];
  document.getElementById('custom-chat-input').value = randomMemo;
  showToast("🎙️ Voice memo transcribed into chat area!");
  runAiExtraction();
}

async function runAiExtraction() {
  const text = document.getElementById('custom-chat-input').value.trim();
  if (!text) {
    showToast("Please enter a conversation or select a preset", "danger");
    return;
  }

  const container = document.getElementById('extraction-cards-container');
  container.innerHTML = `
    <div style="padding: 30px; text-align: center; color: var(--accent-primary);">
      <div style="font-size: 28px; animation: bannerPulse 1s infinite;">⚡</div>
      <p style="margin-top: 8px; font-weight: 700;">Analyzing conversation with AI Promise Extractor...</p>
    </div>
  `;

  try {
    const res = await fetch('/api/promises/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    });
    const data = await res.json();
    state.extractedCandidates = data.candidates || [];
    renderExtractionResults(state.extractedCandidates);
  } catch (err) {
    console.error('Extraction failed', err);
    container.innerHTML = `<div style="color: #ef4444; padding: 20px;">Extraction failed. Please try again.</div>`;
  }
}

function renderExtractionResults(candidates) {
  const container = document.getElementById('extraction-cards-container');
  const countBadge = document.getElementById('extraction-count-badge');
  const actionsBar = document.getElementById('extraction-actions-bar');
  container.innerHTML = '';

  if (candidates.length === 0) {
    countBadge.textContent = '0 promises detected';
    container.innerHTML = `
      <div style="padding: 30px; text-align: center; color: var(--text-muted); background: var(--bg-card); border-radius: 16px;">
        <p>No clear commitments detected in this text. Try adding dates (e.g. "by Friday", "tomorrow").</p>
      </div>
    `;
    actionsBar.style.display = 'none';
    return;
  }

  countBadge.textContent = `${candidates.length} promise${candidates.length > 1 ? 's' : ''} detected!`;
  actionsBar.style.display = 'block';

  candidates.forEach((c, idx) => {
    const card = document.createElement('div');
    card.className = 'result-card';
    
    const isIncoming = c.direction === 'customer_to_business';
    const directionBadge = isIncoming
      ? '<span class="direction-tag tag-incoming">📥 Client Commitment</span>'
      : '<span class="direction-tag tag-outgoing">📤 Our Deliverable</span>';

    const amtText = c.payment_amount > 0 ? `• 💰 ${c.currency}${c.payment_amount.toLocaleString()}` : '';

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <span style="font-size: 0.75rem; font-weight: 700; color: var(--accent-primary); text-transform: uppercase;">PROMISE CANDIDATE #${idx + 1}</span>
          <h4 style="font-size: 1.05rem; font-weight: 800; margin-top: 2px;">${c.title}</h4>
        </div>
        ${directionBadge}
      </div>

      <div style="margin: 10px 0; background: var(--bg-tertiary); padding: 10px 12px; border-radius: 8px; font-size: 0.85rem; color: var(--text-main);">
        <strong>Deliverable:</strong> ${c.deliverable}
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.8rem; color: var(--text-muted);">
        <div>👤 <strong>Customer:</strong> ${c.customer_name}</div>
        <div>📅 <strong>Due:</strong> <span style="color: var(--text-main); font-weight: 700;">${c.due_date_text}</span></div>
        <div>🎯 <strong>Responsible:</strong> ${c.responsible_person} (${c.responsible_role})</div>
        <div>⚡ <strong>Priority:</strong> ${c.priority.toUpperCase()} ${amtText}</div>
      </div>
    `;
    container.appendChild(card);
  });
}

async function saveAllExtracted() {
  if (state.extractedCandidates.length === 0) return;

  try {
    const res = await fetch('/api/promises/batch-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.extractedCandidates)
    });
    const data = await res.json();
    showToast(`Successfully saved ${data.count} promise${data.count > 1 ? 's' : ''} to board!`);
    
    // Switch to Dashboard
    switchTab('dashboard');
  } catch (err) {
    console.error('Failed to batch save', err);
    showToast("Failed to save promises", "danger");
  }
}

// --- Morning Dispatch Center ---
async function fetchMorningDigest() {
  try {
    const res = await fetch('/api/notifications/whatsapp-digest');
    const data = await res.json();

    document.getElementById('team-digest-text').textContent = data.team_digest;

    const nudgesContainer = document.getElementById('customer-nudges-list');
    nudgesContainer.innerHTML = '';

    if (!data.customer_nudges || data.customer_nudges.length === 0) {
      nudgesContainer.innerHTML = `<div style="padding: 20px; color: var(--text-muted); text-align: center;">No individual customer updates required right now.</div>`;
      return;
    }

    data.customer_nudges.forEach(n => {
      const item = document.createElement('div');
      item.style.background = 'var(--bg-tertiary)';
      item.style.padding = '14px 16px';
      item.style.borderRadius = '12px';
      item.style.border = '1px solid var(--border-glass)';
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <strong style="font-size: 0.9rem;">${n.customer_name} (${n.promise_code})</strong>
          <span style="font-size: 0.75rem; color: var(--text-dim);">${n.customer_phone}</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.4;">${n.message}</p>
        <div style="margin-top: 10px; display: flex; gap: 8px;">
          <a href="https://wa.me/${(n.customer_phone || '').replace(/[^0-9]/g, '')}?text=${encodeURIComponent(n.message)}" target="_blank" class="btn btn-whatsapp btn-sm">
            <span>📲</span> Open in WhatsApp
          </a>
          <button class="btn btn-secondary btn-sm btn-copy-nudge" data-msg="${encodeURIComponent(n.message)}">
            <span>📋</span> Copy Text
          </button>
        </div>
      `;
      nudgesContainer.appendChild(item);
    });

    nudgesContainer.querySelectorAll('.btn-copy-nudge').forEach(b => {
      b.addEventListener('click', (e) => {
        const text = decodeURIComponent(b.getAttribute('data-msg'));
        navigator.clipboard.writeText(text);
        showToast("Customer message copied to clipboard!");
      });
    });

  } catch (err) {
    console.error('Failed to fetch morning digest', err);
  }
}

function setupMorningDispatch() {
  document.getElementById('btn-copy-team-digest').addEventListener('click', () => {
    const text = document.getElementById('team-digest-text').textContent;
    navigator.clipboard.writeText(text);
    showToast("📋 Daily team morning dispatch copied to clipboard!");
  });
}

// --- Team Accountability Board ---
async function fetchTeam() {
  try {
    const res = await fetch('/api/team');
    const data = await res.json();
    state.team = data.team || [];
    renderTeam(state.team);
  } catch (err) {
    console.error('Failed to fetch team', err);
  }
}

function renderTeam(team) {
  const container = document.getElementById('team-grid');
  container.innerHTML = '';

  team.forEach(m => {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.style.setProperty('--card-accent', m.avatar_color || '#10b981');
    card.innerHTML = `
      <div class="stat-header">
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 36px; height: 36px; border-radius: 50%; background: ${m.avatar_color || '#10b981'}; display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 800;">
            ${m.name.charAt(0)}
          </div>
          <div>
            <h4 style="font-size: 1rem; font-weight: 700;">${m.name}</h4>
            <span style="font-size: 0.75rem; color: var(--text-dim);">${m.role}</span>
          </div>
        </div>
        <span style="font-size: 0.75rem; font-family: var(--font-mono); font-weight: 700; color: var(--accent-primary);">${m.total_promises} Active</span>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-glass); text-align: center;">
        <div style="background: rgba(239, 68, 68, 0.1); padding: 6px; border-radius: 8px;">
          <div style="font-size: 1.1rem; font-weight: 800; color: #ef4444; font-family: var(--font-mono);">${m.overdue_count || 0}</div>
          <div style="font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase;">Overdue</div>
        </div>
        <div style="background: rgba(245, 158, 11, 0.1); padding: 6px; border-radius: 8px;">
          <div style="font-size: 1.1rem; font-weight: 800; color: #f59e0b; font-family: var(--font-mono);">${m.due_today_count || 0}</div>
          <div style="font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase;">Due Today</div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.1); padding: 6px; border-radius: 8px;">
          <div style="font-size: 1.1rem; font-weight: 800; color: #10b981; font-family: var(--font-mono);">${m.completed_count || 0}</div>
          <div style="font-size: 0.65rem; color: var(--text-dim); text-transform: uppercase;">Fulfilled</div>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// --- WhatsApp Webhook Simulator ---
function setupWebhookSimulator() {
  document.getElementById('webhook-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      sender_name: document.getElementById('webhook-sender').value,
      from: document.getElementById('webhook-phone').value,
      message: document.getElementById('webhook-msg').value
    };

    try {
      const res = await fetch('/api/webhook/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      const resBox = document.getElementById('webhook-response-box');
      resBox.style.display = 'block';
      document.getElementById('webhook-response-json').textContent = JSON.stringify(data, null, 2);
      showToast(`Webhook simulated! Extracted ${data.extracted_promises_count} promises.`);
      fetchSummary();
    } catch (err) {
      console.error('Webhook simulation failed', err);
      showToast("Webhook failed", "danger");
    }
  });
}

// --- Modals Setup & Actions ---
function setupModals() {
  // Close buttons
  document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.getAttribute('data-close');
      document.getElementById(modalId).classList.remove('active');
    });
  });

  // Open Create Modal
  document.getElementById('btn-open-create-modal').addEventListener('click', () => {
    // Set default datetime to tomorrow 5 PM
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(17, 0, 0, 0);
    const isoString = tomorrow.toISOString().slice(0, 16);
    document.querySelector('#form-create-promise input[name="due_date"]').value = isoString;

    document.getElementById('modal-create-promise').classList.add('active');
  });

  // Create Promise Submit
  document.getElementById('form-create-promise').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    
    const payload = {
      customer_name: formData.get('customer_name'),
      customer_phone: formData.get('customer_phone'),
      direction: formData.get('direction'),
      category: formData.get('category'),
      title: formData.get('title'),
      deliverable: formData.get('deliverable'),
      due_date: formData.get('due_date').replace('T', ' '),
      due_date_text: formData.get('due_date_text') || formData.get('due_date').replace('T', ' '),
      responsible_person: formData.get('responsible_person'),
      priority: formData.get('priority'),
      payment_amount: parseFloat(formData.get('payment_amount') || 0)
    };

    try {
      const res = await fetch('/api/promises', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      await res.json();
      document.getElementById('modal-create-promise').classList.remove('active');
      form.reset();
      showToast("Promise logged successfully!");
      fetchSummary();
      fetchPromises();
    } catch (err) {
      console.error('Failed to create promise', err);
      showToast("Failed to create promise", "danger");
    }
  });

  // Fulfill Promise Submit
  document.getElementById('form-fulfill-promise').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('fulfill-promise-id').value;
    const proofNote = document.getElementById('fulfill-proof-note').value;
    const attachment = document.getElementById('fulfill-proof-attachment').value;

    try {
      await fetch(`/api/promises/${id}/fulfill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proof_note: proofNote, proof_attachment: attachment })
      });
      document.getElementById('modal-fulfill-promise').classList.remove('active');
      showToast("Promise fulfilled & proof recorded! 🏆");
      fetchSummary();
      fetchPromises();
    } catch (err) {
      console.error('Failed to fulfill', err);
      showToast("Failed to mark as fulfilled", "danger");
    }
  });

  // Renegotiate Deadline Submit
  document.getElementById('form-renegotiate-promise').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('renegotiate-promise-id').value;
    const newDate = document.getElementById('renegotiate-new-date').value.replace('T', ' ');
    const newText = document.getElementById('renegotiate-new-text').value;
    const reason = document.getElementById('renegotiate-reason').value;

    try {
      await fetch(`/api/promises/${id}/renegotiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_due_date: newDate, new_due_date_text: newText, reason: reason })
      });
      document.getElementById('modal-renegotiate-promise').classList.remove('active');
      showToast("Promise deadline updated with audit justification!");
      fetchSummary();
      fetchPromises();
    } catch (err) {
      console.error('Failed to renegotiate', err);
      showToast("Failed to renegotiate deadline", "danger");
    }
  });
}

function onOpenFulfillModal(e) {
  const btn = e.currentTarget;
  const id = btn.getAttribute('data-id');
  const title = btn.getAttribute('data-title');
  const customer = btn.getAttribute('data-customer');

  document.getElementById('fulfill-promise-id').value = id;
  document.getElementById('fulfill-promise-summary').textContent = `Fulfilling: "${title}" for ${customer}`;
  document.getElementById('fulfill-proof-note').value = '';
  document.getElementById('fulfill-proof-attachment').value = '';
  document.getElementById('modal-fulfill-promise').classList.add('active');
}

function onOpenRenegotiateModal(e) {
  const btn = e.currentTarget;
  const id = btn.getAttribute('data-id');
  const title = btn.getAttribute('data-title');
  const date = btn.getAttribute('data-date');

  document.getElementById('renegotiate-promise-id').value = id;
  document.getElementById('renegotiate-promise-summary').textContent = `Rescheduling: "${title}" (Current due: ${date})`;
  document.getElementById('renegotiate-reason').value = '';
  document.getElementById('renegotiate-new-text').value = '';
  document.getElementById('modal-renegotiate-promise').classList.add('active');
}

function onOpenAuditModal(e) {
  const id = e.currentTarget.getAttribute('data-id');
  const promise = state.promises.find(p => p.id == id);
  if (!promise) return;

  document.getElementById('audit-modal-title').textContent = `Audit Trail: ${promise.promise_code} (${promise.customer_name})`;
  const container = document.getElementById('audit-logs-timeline');
  container.innerHTML = '';

  const logs = promise.audit_logs || [];
  if (logs.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted);">No audit logs recorded for this item.</p>`;
  } else {
    logs.forEach(l => {
      const entry = document.createElement('div');
      entry.style.background = 'var(--bg-tertiary)';
      entry.style.padding = '12px 16px';
      entry.style.borderRadius = '10px';
      entry.style.borderLeft = '3px solid var(--accent-primary)';
      entry.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
          <strong style="font-size: 0.85rem; color: var(--accent-primary);">${l.action} by ${l.actor}</strong>
          <span style="font-size: 0.75rem; color: var(--text-dim);">${l.created_at}</span>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted);">${l.details}</p>
      `;
      container.appendChild(entry);
    });
  }

  document.getElementById('modal-audit-history').classList.add('active');
}

function onWhatsAppNudgeClick(e) {
  const btn = e.currentTarget;
  const customer = btn.getAttribute('data-customer');
  const phone = btn.getAttribute('data-phone') || '';
  const title = btn.getAttribute('data-title');
  const due = btn.getAttribute('data-due');

  const msg = `Hi ${customer}, friendly update from our team regarding *${title}*. We are on track for *${due}*. Please let us know if you have any questions!`;
  const cleanPhone = phone.replace(/[^0-9]/g, '');
  
  if (cleanPhone) {
    window.open(`https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg)}`, '_blank');
  } else {
    navigator.clipboard.writeText(msg);
    showToast("Nudge text copied to clipboard!");
  }
}

async function onDeletePromiseClick(e) {
  const id = e.currentTarget.getAttribute('data-id');
  if (confirm("Are you sure you want to delete this promise record?")) {
    try {
      await fetch(`/api/promises/${id}`, { method: 'DELETE' });
      showToast("Promise deleted");
      fetchSummary();
      fetchPromises();
    } catch (err) {
      console.error('Delete failed', err);
      showToast("Failed to delete", "danger");
    }
  }
}

// --- Integrations Hub (Microsoft Teams & WhatsApp) ---

async function fetchIntegrationConfig() {
  try {
    const res = await fetch('/api/integrations/config');
    const cfg = await res.json();

    // Teams fields
    document.getElementById('cfg-teams-webhook-url').value = cfg.teams_webhook_url || '';
    document.getElementById('cfg-teams-channel-name').value = cfg.teams_channel_name || 'General / Operations';
    document.getElementById('cfg-teams-auto-morning').checked = cfg.teams_auto_morning_digest !== false;
    document.getElementById('cfg-teams-auto-overdue').checked = cfg.teams_auto_overdue_alert !== false;

    // WhatsApp fields
    document.getElementById('cfg-wa-phone-id').value = cfg.whatsapp_phone_number_id || '';
    document.getElementById('cfg-wa-token').value = cfg.whatsapp_access_token || '';
    document.getElementById('cfg-wa-auto-ack').checked = cfg.whatsapp_auto_ack !== false;
    document.getElementById('wa-verify-token-val').value = cfg.whatsapp_verify_token || 'promise_tracker_secret_token_2026';
    
    // Status Badges
    const teamsBadge = document.getElementById('teams-status-badge');
    if (cfg.teams_webhook_url) {
      teamsBadge.textContent = 'Active Webhook';
      teamsBadge.className = 'status-badge completed';
    } else {
      teamsBadge.textContent = 'Not Connected';
      teamsBadge.className = 'status-badge pending';
    }

  } catch (err) {
    console.error('Failed to load integration config', err);
  }
}

function setupIntegrationsHub() {
  // 1. Copy WhatsApp Webhook URL
  document.getElementById('btn-copy-wa-url').addEventListener('click', () => {
    const url = document.getElementById('wa-callback-url').value;
    navigator.clipboard.writeText(url);
    showToast("📋 WhatsApp Callback URL copied to clipboard!");
  });

  // 2. Copy WhatsApp Verify Token
  document.getElementById('btn-copy-wa-token').addEventListener('click', () => {
    const token = document.getElementById('wa-verify-token-val').value;
    navigator.clipboard.writeText(token);
    showToast("📋 WhatsApp Verify Token copied to clipboard!");
  });

  // 3. Save Microsoft Teams Config
  document.getElementById('form-teams-config').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      teams_enabled: true,
      teams_webhook_url: document.getElementById('cfg-teams-webhook-url').value.trim(),
      teams_channel_name: document.getElementById('cfg-teams-channel-name').value.trim(),
      teams_auto_morning_digest: document.getElementById('cfg-teams-auto-morning').checked,
      teams_auto_overdue_alert: document.getElementById('cfg-teams-auto-overdue').checked
    };

    try {
      await fetch('/api/integrations/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast("Microsoft Teams settings saved successfully! 👥");
      fetchIntegrationConfig();
    } catch (err) {
      showToast("Failed to save Teams config", "danger");
    }
  });

  // 4. Save WhatsApp Cloud API Config
  document.getElementById('form-whatsapp-config').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      whatsapp_enabled: true,
      whatsapp_phone_number_id: document.getElementById('cfg-wa-phone-id').value.trim(),
      whatsapp_access_token: document.getElementById('cfg-wa-token').value.trim(),
      whatsapp_auto_ack: document.getElementById('cfg-wa-auto-ack').checked
    };

    try {
      await fetch('/api/integrations/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast("WhatsApp Cloud API settings saved! 💬");
      fetchIntegrationConfig();
    } catch (err) {
      showToast("Failed to save WhatsApp config", "danger");
    }
  });

  // 5. Test Teams Alert Card
  document.getElementById('btn-teams-test-alert').addEventListener('click', async () => {
    const webhookUrl = document.getElementById('cfg-teams-webhook-url').value.trim();
    if (!webhookUrl) {
      showToast("Please enter your Teams Webhook URL first", "danger");
      return;
    }

    try {
      const res = await fetch('/api/integrations/teams/send-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl })
      });
      const data = await res.json();
      if (data.status === 'success') {
        showToast("Test Adaptive Card delivered to Teams Channel! 🚀");
      } else {
        showToast(`Teams Webhook response: ${data.error || JSON.stringify(data)}`, "danger");
      }
    } catch (err) {
      showToast("Failed to reach Teams Webhook endpoint", "danger");
    }
  });

  // 6. Dispatch Morning Digest to Teams Now
  document.getElementById('btn-teams-dispatch-digest').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/integrations/teams/dispatch-digest', { method: 'POST' });
      const data = await res.json();
      showToast(`Morning Dispatch sent to Teams! (${data.due_today_count} due, ${data.overdue_count} overdue)`);
    } catch (err) {
      showToast("Failed to dispatch to Teams. Check Webhook URL in settings.", "danger");
    }
  });

  // 7. Run Teams Bot Command Console
  document.getElementById('btn-run-teams-bot').addEventListener('click', async () => {
    const input = document.getElementById('teams-bot-input').value.trim();
    if (!input) return;

    try {
      const res = await fetch('/api/integrations/teams/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input })
      });
      const data = await res.json();
      const outputBox = document.getElementById('teams-bot-output');
      outputBox.style.display = 'block';
      outputBox.textContent = data.text || JSON.stringify(data, null, 2);
      showToast("Bot command executed!");
    } catch (err) {
      showToast("Bot command failed", "danger");
    }
  });

  // 8. Test Outbound WhatsApp Message
  document.getElementById('btn-send-wa-test').addEventListener('click', async () => {
    const phone = document.getElementById('wa-test-phone').value.trim();
    const msg = document.getElementById('wa-test-msg').value.trim();

    try {
      const res = await fetch('/api/integrations/whatsapp/send-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone, message: msg })
      });
      const data = await res.json();
      const outputBox = document.getElementById('wa-test-output');
      outputBox.style.display = 'block';
      outputBox.textContent = JSON.stringify(data, null, 2);
      showToast(`WhatsApp Message Sent (${data.mode})! 📲`);
    } catch (err) {
      showToast("Failed to send WhatsApp message", "danger");
    }
  });
}

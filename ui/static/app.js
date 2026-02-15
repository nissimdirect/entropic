// Entropic — DAW-Style UI Controller
// Handles: effect browser, drag-to-chain, Moog knobs, real-time preview
// Layers panel (Photoshop), History panel (Photoshop), Ableton on/off toggles

const API = '';

// ============ TOAST / MODAL SYSTEM (replaces alert/prompt) ============

function showToast(message, type = 'info', action = null, duration = null, details = null) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    if (duration === null) {
        duration = (type === 'error' || type === 'warning') ? 8000 : 4000;
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
    let html = `<span class="toast-icon">${_toastIcon(type)}</span>`;
    html += `<span class="toast-msg">${esc(message)}</span>`;
    if (details) {
        html += `<button class="toast-details-btn" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block';event.stopPropagation()">Details</button>`;
        html += `<pre class="toast-details">${esc(typeof details === 'string' ? details : String(details))}</pre>`;
    }
    if (action) {
        html += `<button class="toast-action" onclick="(${action.fn})();event.stopPropagation()">${esc(action.label)}</button>`;
    }
    toast.innerHTML = html;
    toast.addEventListener('click', () => {
        clearTimeout(toast._timer);
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'opacity 0.3s, transform 0.3s';
        setTimeout(() => toast.remove(), 300);
    });
    toast.style.cursor = 'pointer';
    container.appendChild(toast);
    toast._timer = setTimeout(() => {
        if (toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'opacity 0.3s, transform 0.3s';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

function _toastIcon(type) {
    switch (type) {
        case 'success': return '&#10003;';
        case 'error': return '&#10007;';
        case 'warning': return '&#9888;';
        case 'info': return '&#8505;';
        default: return '';
    }
}

function showErrorToast(message, details) {
    showToast(message, 'error', null, 8000, details || null);
}

// Structured error handler — parses server error detail dicts with hint + action
function handleApiError(data, context) {
    let detail = data;
    // FastAPI wraps HTTPException detail in {detail: ...}
    if (data && data.detail && typeof data.detail === 'object') {
        detail = data.detail;
    } else if (data && data.detail && typeof data.detail === 'string') {
        showErrorToast(`${context}: ${data.detail}`);
        return;
    }

    const message = detail.detail || detail.message || context || 'Unknown error';
    const hint = detail.hint || '';
    const actionKey = detail.action;

    const actionMap = {
        load_file: { label: 'Load File', fn: "function(){document.getElementById('file-input').click()}" },
        retry: { label: 'Retry', fn: "function(){previewChain()}" },
        undo: { label: 'Undo', fn: "function(){undo()}" },
        flatten: { label: 'Flatten', fn: "function(){flattenChain()}" },
        refresh: { label: 'Refresh', fn: "function(){location.reload()}" },
        trim: null,
    };

    const action = actionKey ? actionMap[actionKey] : null;
    const fullMsg = hint ? `${message} — ${hint}` : message;
    showToast(fullMsg, 'error', action || null, 10000);
}

function showConfirmDialog(title, message) {
    return new Promise(resolve => {
        // Simple confirm using native dialog for now
        resolve(window.confirm(`${title}\n\n${message}`));
    });
}

// ============ LOADING OVERLAY (canvas processing feedback) ============

function showLoading(message = 'Processing...') {
    let overlay = document.getElementById('loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-message"></div>
                <div class="loading-progress" style="display:none">
                    <div class="loading-progress-bar"><div class="loading-progress-fill"></div></div>
                    <div class="loading-progress-text"></div>
                </div>
            </div>`;
        const canvasArea = document.getElementById('canvas-area');
        if (canvasArea) canvasArea.appendChild(overlay);
    }
    overlay.querySelector('.loading-message').textContent = message;
    overlay.querySelector('.loading-progress').style.display = 'none';
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.style.display = 'none';
}

function updateProgress(current, total, message) {
    const overlay = document.getElementById('loading-overlay');
    if (!overlay) return;
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    const progressEl = overlay.querySelector('.loading-progress');
    progressEl.style.display = 'block';
    overlay.querySelector('.loading-progress-fill').style.width = pct + '%';
    overlay.querySelector('.loading-progress-text').textContent =
        message ? `${message} ${pct}%` : `${pct}%`;
    if (message) overlay.querySelector('.loading-message').textContent = message;
}

// Debounced warning for perform layer sync failures (avoids toast spam during playback)
let _perfSyncWarnLast = 0;
function _perfSyncWarn() {
    const now = Date.now();
    if (now - _perfSyncWarnLast > 5000) {
        _perfSyncWarnLast = now;
        showToast('Layer sync failed — check server connection', 'warning');
    }
}

// Input modal state
let _inputModalCallback = null;

function showInputModal(title, placeholder, callback) {
    _inputModalCallback = callback;
    document.getElementById('input-modal-title').textContent = title;
    const field = document.getElementById('input-modal-field');
    field.value = '';
    field.placeholder = placeholder || '';
    document.getElementById('input-modal-overlay').style.display = 'flex';
    setTimeout(() => field.focus(), 100);
}

function closeInputModal() {
    document.getElementById('input-modal-overlay').style.display = 'none';
    _inputModalCallback = null;
}

function submitInputModal() {
    const value = document.getElementById('input-modal-field').value.trim();
    const cb = _inputModalCallback;
    closeInputModal();
    if (cb && value) cb(value);
}

// Handle Enter key in input modal
document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && document.getElementById('input-modal-overlay').style.display === 'flex') {
        e.preventDefault();
        submitInputModal();
    }
});

// ============ SERVER HEARTBEAT ============

let _heartbeatFailures = 0;
let _heartbeatInterval = null;
let _serverDown = false;

function startHeartbeat() {
    _heartbeatInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API}/api/health`, { signal: AbortSignal.timeout(4000) });
            if (res.ok) {
                if (_serverDown) {
                    _serverDown = false;
                    _heartbeatFailures = 0;
                    document.getElementById('server-banner').style.display = 'none';
                }
            } else {
                _heartbeatFailures++;
            }
        } catch {
            _heartbeatFailures++;
        }
        if (_heartbeatFailures >= 3 && !_serverDown) {
            _serverDown = true;
            document.getElementById('server-banner').style.display = 'flex';
        }
    }, 5000);
}

function restartServer() {
    // In desktop mode, the server thread is managed by desktop.py
    // This just resets heartbeat and waits for recovery
    _heartbeatFailures = 0;
    showToast('Attempting to reconnect...', 'info');
}

// Shortcut reference
function showShortcutRef() {
    document.getElementById('shortcut-overlay').style.display = 'flex';
    // Highlight current mode's shortcuts
    document.querySelectorAll('[data-shortcut-mode]').forEach(el => {
        const mode = el.getAttribute('data-shortcut-mode');
        if (mode === 'common') {
            el.style.opacity = '1'; // Always visible
        } else if (mode === appMode) {
            el.style.opacity = '1'; // Current mode: full visibility
        } else {
            el.style.opacity = '0.3'; // Other modes: dimmed
        }
    });
}
function closeShortcutRef() {
    document.getElementById('shortcut-overlay').style.display = 'none';
}

// ============ HELP PANEL (H key) ============

function showHelpPanel() {
    const overlay = document.getElementById('help-overlay');
    if (!overlay) return;
    overlay.style.display = 'flex';
    // Populate effect reference
    const list = document.getElementById('help-effect-list');
    if (list && effectDefs.length > 0) {
        list.innerHTML = effectDefs.map(e =>
            `<div class="help-effect-item" data-name="${esc(e.name)}">
                <div class="name">${esc(e.name)}</div>
                <div class="desc">${esc(e.description || '')}</div>
            </div>`
        ).join('');
    }
    const search = document.getElementById('help-search');
    if (search) { search.value = ''; search.focus(); }
}

function closeHelpPanel() {
    const overlay = document.getElementById('help-overlay');
    if (overlay) overlay.style.display = 'none';
}

function filterHelpEffects(query) {
    const q = query.toLowerCase();
    document.querySelectorAll('.help-effect-item').forEach(item => {
        const name = (item.dataset.name || '').toLowerCase();
        const desc = (item.querySelector('.desc')?.textContent || '').toLowerCase();
        item.style.display = (name.includes(q) || desc.includes(q)) ? '' : 'none';
    });
}

// ============ ONBOARDING ============

function showOnboarding() {
    if (localStorage.getItem('entropic_onboarded')) return;
    localStorage.setItem('entropic_onboarded', '1');
    showToast('Welcome to Entropic! Press H for help, ? for shortcuts.', 'info', {
        label: 'Show Help',
        fn: "function(){showHelpPanel()}"
    }, 8000);
}

// ============ EFFECT GROUPS (Ableton-style racks) ============

let groupIdCounter = 1000;

function addGroup() {
    const group = {
        id: deviceIdCounter++,
        type: 'group',
        name: 'Group',
        collapsed: false,
        bypassed: false,
        mix: 1.0,
        children: [],
    };

    // If effects are selected, wrap them into the group
    if (selectedLayerId !== null) {
        const idx = chain.findIndex(d => d.id === selectedLayerId);
        if (idx >= 0) {
            const selected = chain.splice(idx, 1)[0];
            group.children.push(selected);
            chain.splice(idx, 0, group);
        } else {
            chain.push(group);
        }
    } else {
        chain.push(group);
    }

    selectedLayerId = group.id;
    pushHistory('Create Group');
    syncChainToRegion();
    renderChain();
    renderLayers();
}

function ungroupSelected() {
    if (selectedLayerId === null) return;
    const idx = chain.findIndex(d => d.id === selectedLayerId);
    if (idx < 0) return;
    const item = chain[idx];
    if (item.type !== 'group') return;

    // Splice children back into parent array
    const children = item.children || [];
    chain.splice(idx, 1, ...children);
    selectedLayerId = children.length > 0 ? children[0].id : null;
    pushHistory('Ungroup');
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

function flattenChainForApi(items) {
    // Recursively flatten chain tree into flat effect array for server
    const result = [];
    for (const item of items) {
        if (item.type === 'group') {
            if (item.bypassed) continue;
            const children = flattenChainForApi(item.children || []);
            // Apply group mix by injecting it into children
            for (const child of children) {
                if (item.mix < 1.0) {
                    child.params = child.params || {};
                    child.params._group_mix = item.mix;
                }
                result.push(child);
            }
        } else {
            if (item.bypassed) continue;
            result.push({
                name: item.name,
                params: { ...item.params, mix: item.mix ?? 1.0 },
            });
        }
    }
    return result;
}

function _countDevices(items) {
    let count = 0;
    for (const item of items) {
        if (item.type === 'group') {
            count += _countDevices(item.children || []);
        } else {
            count++;
        }
    }
    return count;
}

function _findItemInChain(items, id) {
    for (const item of items) {
        if (item.id === id) return item;
        if (item.type === 'group' && item.children) {
            const found = _findItemInChain(item.children, id);
            if (found) return found;
        }
    }
    return null;
}

function toggleGroupCollapse(groupId) {
    const group = _findItemInChain(chain, groupId);
    if (group && group.type === 'group') {
        group.collapsed = !group.collapsed;
        renderChain();
    }
}

function renameGroup(groupId) {
    const group = _findItemInChain(chain, groupId);
    if (!group || group.type !== 'group') return;
    showInputModal('Rename Group', group.name, (newName) => {
        if (newName && newName.trim()) {
            group.name = newName.trim();
            pushHistory(`Rename Group → ${group.name}`);
            renderChain();
        }
    });
}

// Reveal in Finder via pywebview bridge (or no-op in browser mode)
function revealInFinder(path) {
    if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.reveal_in_finder(path);
    } else {
        // Browser fallback — just log
        console.log('Reveal in Finder:', path);
    }
}

// HTML entity escaping to prevent XSS in innerHTML
function esc(str) {
    if (str == null) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
let effectDefs = [];      // Effect definitions from server
let categoryOrder = [];   // Server-provided category ordering
let categoryLabels = {};  // Server-provided category display names
let controlMap = null;    // UI control type mapping (loaded from control-map.json)
let chain = [];           // Current effect chain: [{name, params, bypassed, id}, ...]
let videoLoaded = false;
let currentFrame = 0;
let totalFrames = 100;
let videoFps = 30;
let deviceIdCounter = 0;
let previewDebounce = null;
// Playback frame pre-cache
const frameCache = new Map();       // frame_number -> dataUrl
const frameCacheInFlight = new Set(); // frame numbers currently being fetched
const FRAME_CACHE_LOOKAHEAD = 8;    // how many frames to pre-fetch ahead
const FRAME_CACHE_MAX = 30;         // max cached frames before eviction
let selectedLayerId = null;
let mixLevel = 1.0;              // Wet/dry mix: 0.0 = original, 1.0 = full effect
let appMode = 'timeline';        // 'quick' | 'timeline' | 'perform'

// Feature flags
const FEATURE_QUICK_MODE = false; // Quick mode flagged off — Timeline is default. Code preserved.
let performToggleActive = false;  // Whether the Perform toggle within Timeline mode is active

// Spatial mask drawing state
let maskDrawing = false;
let maskStartX = 0;
let maskStartY = 0;
let maskRect = null;             // {x, y, w, h} in canvas pixels during draw

// ============ LFO MODULATION STATE ============

let lfoState = {
    rate: 1.0,          // Hz
    depth: 0.5,         // 0-1
    phase_offset: 0,    // 0-1
    waveform: 'sine',
    mappings: [],       // [{deviceId, paramName, baseValue, min, max}]
    mapping_mode: false,
    seed: 42,
};
let lfoAnimFrame = null;
let lfoPhase = 0;
let lfoLastTime = 0;

// ============ INFO VIEW (Ableton-style) ============

function showInfoView(name, desc) {
    const el = document.getElementById('info-view-content');
    if (!el) return;
    const def = effectDefs.find(e => e.name === name);
    const cat = def?.category || '';
    el.textContent = `${name} [${cat}] — ${desc}`;
}

// ============ EFFECT HOVER PREVIEW (thumbnail tooltip) ============

let _hoverPreviewTimer = null;
const _hoverPreviewCache = {};  // effectName -> dataUrl

function showEffectHoverPreview(effectName, event) {
    clearTimeout(_hoverPreviewTimer);
    if (!videoLoaded) return;

    // Position the tooltip near the mouse
    let tooltip = document.getElementById('effect-hover-preview');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'effect-hover-preview';
        document.body.appendChild(tooltip);
    }
    tooltip.style.left = (event.clientX + 16) + 'px';
    tooltip.style.top = (event.clientY - 50) + 'px';

    // Show cached immediately if available
    if (_hoverPreviewCache[effectName]) {
        tooltip.innerHTML = `<img src="${_hoverPreviewCache[effectName]}" alt="preview">`;
        tooltip.style.display = 'block';
        return;
    }

    // Debounced fetch
    _hoverPreviewTimer = setTimeout(async () => {
        try {
            tooltip.innerHTML = '<div class="hover-loading">...</div>';
            tooltip.style.display = 'block';
            const res = await fetch(`${API}/api/preview/thumbnail`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ effect_name: effectName, frame_number: currentFrame }),
            });
            if (!res.ok) throw new Error();
            const data = await res.json();
            _hoverPreviewCache[effectName] = data.preview;
            tooltip.innerHTML = `<img src="${data.preview}" alt="preview">`;
        } catch {
            tooltip.style.display = 'none';
        }
    }, 400);
}

function hideEffectHoverPreview() {
    clearTimeout(_hoverPreviewTimer);
    const tooltip = document.getElementById('effect-hover-preview');
    if (tooltip) tooltip.style.display = 'none';
}

function showInfoViewText(text) {
    const el = document.getElementById('info-view-content');
    if (el) el.textContent = text;
}

// ============ CHAIN COMPLEXITY METER ============

function updateChainComplexity(deviceCount) {
    const el = document.getElementById('chain-complexity');
    if (!el) return;
    if (deviceCount === 0) {
        el.textContent = '';
        el.className = '';
        return;
    }
    let label, cls;
    if (deviceCount <= 4) {
        label = 'Light';
        cls = 'low';
    } else if (deviceCount <= 8) {
        label = 'Medium';
        cls = 'medium';
    } else {
        label = 'Heavy';
        cls = 'high';
    }
    const cacheSize = frameCache.size;
    const bufferInfo = cacheSize > 0 ? ` | Buf: ${cacheSize}/${FRAME_CACHE_MAX}` : '';
    el.textContent = `${label} (${deviceCount})${bufferInfo}`;
    el.className = cls;
}

// ============ PERFORM MODE STATE ============

let perfLayers = [];              // Layer configs from server [{layer_id, name, effects, trigger_mode, ...}]
let perfLayerStates = {};         // Client-side layer states {layer_id: {active, opacity, muted, soloed}}
let perfPlaying = false;
let perfRecording = false;        // Explicit recording (R key)
let perfReviewing = false;        // Review playback mode
let perfFrameIndex = 0;
let perfSession = {type:'performance', lanes:[]};  // PerformanceSession dict (auto-buffer)
let perfEventCount = 0;
let perfAnimFrame = null;         // requestAnimationFrame ID
let perfLastFrameTime = 0;
let perfTriggerQueue = [];        // Queued trigger events for next server frame
let perfReviewFrameMap = {};      // Frame->events map for review playback
const PERF_FPS = 15;             // Preview framerate
const PERF_MAX_EVENTS = 50000;   // Buffer cap (same as CLI)
const PERF_LAYER_COLORS = ['#ff4444', '#4488ff', '#44cc44', '#ffcc00'];  // L1-L4
let perfMasterEffects = [];       // Master bus effect chain [{name, params}]
let perfMasterExpanded = false;   // Whether master effects panel is expanded
let perfLayerLfos = {};           // Per-layer LFO state {layer_id: {enabled, waveform, rate, depth, phase}}
let keyboardPerformMode = false;  // M key toggle — Q/W/E/R/A/S/D/F trigger layers
let autoRecording = false;        // Automation arm — record knob movements as timeline automation
let autoRecordLanes = {};         // {deviceId_paramName: [{frame, value}, ...]}
const CAPTURE_BUFFER_SECONDS = 60;
const CAPTURE_BUFFER_MAX_EVENTS = 50000;
let captureBuffer = [];           // [{frame, layerId, param, value, timestamp}]

// ============ HISTORY (Undo/Redo) ============

let history = [];         // Array of snapshots: [{action, chain, timestamp}, ...]
let historyIndex = -1;    // Current position in history

function pushHistory(action) {
    // Discard any future states if we're not at the end
    if (historyIndex < history.length - 1) {
        history = history.splice(0, historyIndex + 1);
    }
    // Deep clone the chain state
    const snapshot = JSON.parse(JSON.stringify(chain));
    history.push({
        action,
        chain: snapshot,
        timestamp: new Date(),
    });
    historyIndex = history.length - 1;
    renderHistory();
    _persistHistory();
}

function undo() {
    if (historyIndex <= 0) return;
    historyIndex--;
    restoreFromHistory(historyIndex);
}

function redo() {
    if (historyIndex >= history.length - 1) return;
    historyIndex++;
    restoreFromHistory(historyIndex);
}

function restoreFromHistory(index) {
    const entry = history[index];
    if (!entry) return;
    chain = JSON.parse(JSON.stringify(entry.chain));
    // Restore deviceIdCounter to avoid ID collisions
    const maxId = chain.reduce((m, d) => Math.max(m, d.id), -1);
    deviceIdCounter = maxId + 1;
    renderChain();
    renderLayers();
    renderHistory();
    _persistHistory();
    schedulePreview();
}

function jumpToHistory(index) {
    if (index < 0 || index >= history.length) return;
    historyIndex = index;
    restoreFromHistory(index);
}

// ============ HISTORY PERSISTENCE (localStorage) ============

function _persistHistory() {
    try {
        const data = history.slice(-50).map(h => ({
            action: h.action,
            chain: h.chain,
            timestamp: h.timestamp.toISOString(),
        }));
        localStorage.setItem('entropic_history', JSON.stringify(data));
        localStorage.setItem('entropic_history_index', String(historyIndex));
    } catch (e) { /* localStorage full or disabled — silently ignore */ }
}

function _loadHistory() {
    try {
        const raw = localStorage.getItem('entropic_history');
        if (!raw) return;
        const data = JSON.parse(raw);
        if (!Array.isArray(data) || data.length === 0) return;
        history = data.map(h => ({
            action: h.action,
            chain: h.chain,
            timestamp: new Date(h.timestamp),
        }));
        const savedIdx = parseInt(localStorage.getItem('entropic_history_index') || '0');
        historyIndex = Math.min(savedIdx, history.length - 1);
        // Restore chain from current history position
        const entry = history[historyIndex];
        if (entry) {
            chain = JSON.parse(JSON.stringify(entry.chain));
            const maxId = chain.reduce((m, d) => Math.max(m, d.id || 0), -1);
            deviceIdCounter = maxId + 1;
        }
    } catch (e) { /* corrupt data — ignore and start fresh */ }
}

function _clearPersistedHistory() {
    localStorage.removeItem('entropic_history');
    localStorage.removeItem('entropic_history_index');
}

// ============ GRIP HANDLE HTML ============

function gripHTML() {
    return `<span class="grip">
        <span class="grip-row"><span class="grip-dot"></span><span class="grip-dot"></span></span>
        <span class="grip-row"><span class="grip-dot"></span><span class="grip-dot"></span></span>
        <span class="grip-row"><span class="grip-dot"></span><span class="grip-dot"></span></span>
    </span>`;
}

// ============ INIT ============

async function init() {
    const [effectsRes, controlsRes] = await Promise.all([
        fetch(`${API}/api/effects`),
        fetch('/static/control-map.json').catch(() => null),
    ]);
    const effectsData = await effectsRes.json();
    // Support both new { effects, categories, category_order } and legacy flat array
    if (Array.isArray(effectsData)) {
        effectDefs = effectsData;
    } else {
        effectDefs = effectsData.effects || [];
        categoryOrder = effectsData.category_order || [];
        categoryLabels = effectsData.categories || {};
    }
    if (controlsRes && controlsRes.ok) {
        controlMap = await controlsRes.json();
    }
    renderBrowser();
    setupDragDrop();
    setupFileInput();
    setupPanelTabs();
    setupKeyboard();
    setupMaskDrawing();
    _loadHistory();
    if (history.length === 0) {
        pushHistory('Open');
    }
    renderChain();
    renderLayers();
    renderHistory();
    startHeartbeat();
    showOnboarding();

    // Initialize timeline editor
    window.timelineEditor = new TimelineEditor('timeline-canvas');

    // Start in timeline mode (default — Quick mode flagged off)
    setMode('timeline');

    // Dismiss boot screen
    const boot = document.getElementById('boot-screen');
    if (boot) {
        boot.classList.add('fade-out');
        setTimeout(() => boot.remove(), 500);
    }
}

// ============ EFFECT BROWSER ============

let browserView = 'category';  // 'category' | 'package' | 'favorites'
let packageDefs = null;        // Loaded on first package view
let browserSearchQuery = '';   // Current search filter

// Favorites (persisted in localStorage)
const _favorites = new Set(JSON.parse(localStorage.getItem('entropic_favorites') || '[]'));
function _saveFavorites() {
    localStorage.setItem('entropic_favorites', JSON.stringify([..._favorites]));
}
function toggleFavorite(name) {
    if (_favorites.has(name)) _favorites.delete(name);
    else _favorites.add(name);
    _saveFavorites();
    renderBrowser();
}

function onBrowserSearch(query) {
    browserSearchQuery = query.trim().toLowerCase();
    renderBrowser();
}

function switchBrowserView(view) {
    browserView = view;
    document.querySelectorAll('.view-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
    renderBrowser();
}

function renderBrowser() {
    if (browserView === 'package') {
        renderBrowserPackages();
    } else if (browserView === 'favorites') {
        renderBrowserFavorites();
    } else {
        renderBrowserCategories();
    }
}

function renderBrowserFavorites() {
    const list = document.getElementById('effect-list');
    const favNames = [..._favorites].filter(n => effectDefs.some(e => e.name === n));
    if (favNames.length === 0) {
        list.innerHTML = '<div style="padding:20px 12px;color:var(--text-dim);font-size:11px;text-align:center">No favorites yet.<br>Right-click any effect &rarr; Add to Favorites</div>';
        return;
    }
    let html = '';
    for (const name of favNames.sort()) {
        const def = effectDefs.find(e => e.name === name);
        const desc = def?.description || '';
        html += `<div class="effect-item" draggable="true" data-effect="${esc(name)}"
                     ondragstart="onBrowserDragStart(event, '${esc(name)}')"
                     data-tooltip="${esc(desc)}">
                    ${gripHTML()}
                    <span class="name">${esc(name)}</span>
                    <span class="fav-star active" onclick="event.stopPropagation();toggleFavorite('${esc(name)}')" title="Remove from favorites">&#9733;</span>
                    <span class="effect-desc">${esc(desc.slice(0, 60))}</span>
                </div>`;
    }
    list.innerHTML = html;
}

// Collapsed state: all folders start collapsed, toggling is tracked here
let _categoriesInitialized = false;
const _collapsedCategories = new Set();

function toggleCategory(cat) {
    if (_collapsedCategories.has(cat)) {
        _collapsedCategories.delete(cat);
    } else {
        _collapsedCategories.add(cat);
    }
    renderBrowserCategories();
}

function _effectMatchesSearch(name, desc) {
    if (!browserSearchQuery) return true;
    return name.toLowerCase().includes(browserSearchQuery) ||
           desc.toLowerCase().includes(browserSearchQuery);
}

function _effectItemHTML(name, desc) {
    const shortDesc = desc.split(' — ')[1] || desc;
    const isFav = _favorites.has(name);
    return `<div class="effect-item" draggable="true" data-effect="${esc(name)}"
                 ondragstart="onBrowserDragStart(event, '${esc(name)}')"
                 onmouseenter="showInfoView('${esc(name)}','${esc(desc.replace(/'/g, "\\'"))}');showEffectHoverPreview('${esc(name)}',event)"
                 onmouseleave="hideEffectHoverPreview()"
                 oncontextmenu="event.preventDefault();showEffectContextMenu(event,'${esc(name)}')"
                 data-tooltip="${esc(desc)}">
                ${gripHTML()}
                <span class="name">${esc(name)}</span>
                <span class="fav-star${isFav ? ' active' : ''}" onclick="event.stopPropagation();toggleFavorite('${esc(name)}')" title="${isFav ? 'Remove from favorites' : 'Add to favorites'}">${isFav ? '&#9733;' : '&#9734;'}</span>
                <span class="effect-desc">${esc(shortDesc.slice(0, 60))}</span>
            </div>`;
}

function showEffectContextMenu(event, name) {
    const isFav = _favorites.has(name);
    const menu = document.getElementById('ctx-menu');
    menu.innerHTML = `
        <div class="ctx-item" onclick="toggleFavorite('${esc(name)}');document.getElementById('ctx-menu').style.display='none'">
            ${isFav ? '&#9733; Remove from Favorites' : '&#9734; Add to Favorites'}
        </div>
        <div class="ctx-item" onclick="addEffect('${esc(name)}');document.getElementById('ctx-menu').style.display='none'">
            Add to Chain
        </div>`;
    menu.style.display = 'block';
    menu.style.left = event.clientX + 'px';
    menu.style.top = event.clientY + 'px';
}

function renderBrowserCategories() {
    const list = document.getElementById('effect-list');

    // Build categories dynamically from effectDefs
    const groups = {};
    for (const def of effectDefs) {
        if (!_effectMatchesSearch(def.name, def.description || '')) continue;
        const cat = (def.category || 'other').toUpperCase();
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(def.name);
    }

    // Use server-provided category order, fall back to hardcoded
    let sorted;
    if (categoryOrder.length > 0) {
        sorted = categoryOrder.map(c => c.toUpperCase()).filter(c => groups[c]);
        // Append any categories not in the server order
        for (const c of Object.keys(groups)) {
            if (!sorted.includes(c)) sorted.push(c);
        }
    } else {
        const order = ['GLITCH', 'DISTORTION', 'TEXTURE', 'COLOR', 'TEMPORAL', 'MODULATION', 'ENHANCE', 'DESTRUCTION'];
        sorted = order.filter(c => groups[c]);
        for (const c of Object.keys(groups)) {
            if (!sorted.includes(c)) sorted.push(c);
        }
    }

    // On first render, open top 3 categories, collapse the rest
    if (!_categoriesInitialized) {
        _categoriesInitialized = true;
        for (let i = 0; i < sorted.length; i++) {
            if (i >= 3) _collapsedCategories.add(sorted[i]);
        }
    }

    // Resolve display label from server categories or fall back to raw key
    function catLabel(cat) {
        const lower = cat.toLowerCase();
        if (categoryLabels[lower]) return categoryLabels[lower];
        return cat;
    }

    // If search is active, expand all matching categories
    const forceExpand = !!browserSearchQuery;

    let html = '';
    for (const cat of sorted) {
        const names = groups[cat];
        if (!names || names.length === 0) continue;
        const collapsed = forceExpand ? false : _collapsedCategories.has(cat);
        const arrow = collapsed ? '&#9654;' : '&#9660;';
        html += `<div class="cat-folder${collapsed ? ' collapsed' : ''}" data-cat="${esc(cat)}">
            <div class="cat-header" onclick="toggleCategory('${esc(cat)}')">
                <span class="cat-arrow">${arrow}</span>
                <span class="cat-name">${esc(catLabel(cat))}</span>
                <span class="count">${names.length}</span>
            </div>
            <div class="cat-items">`;
        for (const name of names.sort()) {
            const desc = effectDefs.find(e => e.name === name)?.description || '';
            html += _effectItemHTML(name, desc);
        }
        html += `</div></div>`;
    }
    if (!html && browserSearchQuery) {
        html = '<div style="padding:20px 12px;color:var(--text-dim);font-size:11px;text-align:center">No effects matching "' + esc(browserSearchQuery) + '"</div>';
    }
    list.innerHTML = html;
}

async function renderBrowserPackages() {
    const list = document.getElementById('effect-list');

    // Load packages on first use
    if (!packageDefs) {
        list.innerHTML = '<div class="loading">Loading packages...</div>';
        try {
            const res = await fetch(`${API}/api/packages`);
            packageDefs = await res.json();
        } catch (e) {
            list.innerHTML = '<div class="loading">Failed to load packages</div>';
            return;
        }
    }

    let html = '';
    for (const pkg of packageDefs) {
        html += `<h3>${esc(pkg.name)} <span class="count">${pkg.recipes.length}</span></h3>`;
        html += `<div class="pkg-desc">${esc(pkg.description)}</div>`;
        for (const recipe of pkg.recipes) {
            // Each recipe is a chain of effects — drag it to apply all at once
            html += `
                <div class="effect-item recipe-item" draggable="true"
                     data-recipe='${JSON.stringify(recipe.effects).replace(/'/g, '&#39;')}'
                     ondragstart="onRecipeDragStart(event, this)"
                     title="${esc(recipe.description)}">
                    ${gripHTML()}
                    <span class="name">${esc(recipe.name)}</span>
                </div>`;
        }
    }
    list.innerHTML = html;
}

function onRecipeDragStart(e, el) {
    const recipeData = el.getAttribute('data-recipe');
    e.dataTransfer.setData('recipe-chain', recipeData);
    el.classList.add('dragging');
    setTimeout(() => el.classList.remove('dragging'), 0);
}

// ============ DRAG AND DROP ============

function onBrowserDragStart(e, effectName) {
    e.dataTransfer.setData('effect-name', effectName);
    e.target.classList.add('dragging');
    setTimeout(() => e.target.classList.remove('dragging'), 0);
}

function setupDragDrop() {
    const rack = document.getElementById('chain-rack');
    const canvas = document.getElementById('canvas-area');

    // Chain rack drop zone
    rack.addEventListener('dragover', e => { e.preventDefault(); rack.classList.add('drag-over'); });
    rack.addEventListener('dragleave', () => rack.classList.remove('drag-over'));
    rack.addEventListener('drop', e => {
        e.preventDefault();
        rack.classList.remove('drag-over');
        // Single effect drag
        const name = e.dataTransfer.getData('effect-name');
        if (name) { addToChain(name); return; }
        // Recipe chain drag (from Package view)
        const recipeData = e.dataTransfer.getData('recipe-chain');
        if (recipeData) {
            try {
                const effects = JSON.parse(recipeData);
                for (const fx of effects) {
                    addToChain(fx.name, fx.params || {});
                }
            } catch (err) { showErrorToast('Invalid recipe data', err.message); }
        }
    });

    // Canvas drop zone (for video files)
    canvas.addEventListener('dragover', e => { e.preventDefault(); canvas.classList.add('drag-over'); });
    canvas.addEventListener('dragleave', () => canvas.classList.remove('drag-over'));
    canvas.addEventListener('drop', e => {
        e.preventDefault();
        canvas.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadVideo(files[0]);
        }
    });

    // Alt+Click on preview to place spatial concentration point on selected device
    canvas.addEventListener('click', e => {
        if (!e.altKey) return;
        const img = document.getElementById('preview-img');
        if (!img || img.style.display === 'none') return;
        const rect = img.getBoundingClientRect();
        const nx = (e.clientX - rect.left) / rect.width;
        const ny = (e.clientY - rect.top) / rect.height;
        if (nx < 0 || nx > 1 || ny < 0 || ny > 1) return;
        // Find selected device
        const sel = document.querySelector('.device.selected');
        if (!sel) return;
        const deviceId = parseInt(sel.dataset.id);
        const device = chain.find(d => d.id === deviceId);
        if (!device) return;
        device.params.concentrate_x = parseFloat(nx.toFixed(3));
        device.params.concentrate_y = parseFloat(ny.toFixed(3));
        if (!device.params.concentrate_radius) device.params.concentrate_radius = 0.2;
        if (!device.params.concentrate_strength) device.params.concentrate_strength = 1.0;
        schedulePreview();
    });
}

// ============ FILE INPUT ============

function setupFileInput() {
    const input = document.getElementById('file-input');
    input.addEventListener('change', () => {
        if (input.files.length > 0) uploadVideo(input.files[0]);
    });

    // Frame scrubber
    document.getElementById('frame-slider').addEventListener('input', e => {
        currentFrame = parseInt(e.target.value);
        const el = document.getElementById('frame-info');
        if (el.style.display === 'block') {
            el.textContent = el.textContent.replace(/Frame \d+\/\d+/, `Frame ${currentFrame}/${totalFrames}`);
        }
        schedulePreview();
    });
}

const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2GB

async function uploadVideo(file) {
    // Client-side validation
    if (file.size > MAX_FILE_SIZE) {
        showErrorToast(`File too large (${(file.size / 1024 / 1024).toFixed(0)}MB). Maximum: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
        return;
    }
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = [
        // Video
        'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'wmv', 'flv', 'ts', 'mts',
        // Image
        'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'webp',
        // GIF
        'gif',
        // Creative raw interpretation
        'pdf', 'zip', 'txt', 'csv', 'json', 'xml', 'html', 'doc', 'docx',
        'wav', 'mp3', 'aiff', 'flac', 'psd', 'ai', 'svg',
    ];
    if (!allowed.includes(ext)) {
        showErrorToast(`Unsupported file type: .${ext}`);
        return;
    }

    const fileNameEl = document.getElementById('file-name');
    fileNameEl.textContent = file.name;
    fileNameEl.classList.add('uploading');
    document.getElementById('empty-state').style.display = 'none';

    const form = new FormData();
    form.append('file', file);
    const fileSizeMB = (file.size / 1024 / 1024).toFixed(0);
    showLoading(`Uploading ${file.name} (${fileSizeMB} MB)...`);

    if (file.size > 50 * 1024 * 1024) {
        showToast(`Large file (${fileSizeMB} MB). Upload may take a moment.`, 'info', null, 5000);
    }

    try {
        const uploadStart = Date.now();
        const data = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `${API}/api/upload`);
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const elapsed = (Date.now() - uploadStart) / 1000;
                    const speed = elapsed > 0 ? e.loaded / elapsed : 0;
                    const speedMB = (speed / 1024 / 1024).toFixed(1);
                    const remaining = speed > 0 ? Math.ceil((e.total - e.loaded) / speed) : 0;
                    const eta = remaining > 0 ? ` — ~${remaining}s remaining` : '';
                    updateProgress(e.loaded, e.total, `Uploading — ${speedMB} MB/s${eta}`);
                }
            };
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try { resolve(JSON.parse(xhr.responseText)); }
                    catch (e) { reject(new Error('Invalid server response')); }
                } else {
                    reject(new Error(`${xhr.status} ${xhr.statusText}`));
                }
            };
            xhr.onerror = () => reject(new Error('Network error'));
            xhr.ontimeout = () => reject(new Error('Upload timed out'));
            xhr.send(form);
        });

        fileNameEl.classList.remove('uploading');
        hideLoading();

        videoLoaded = true;
        totalFrames = data.info.total_frames || 100;
        videoFps = data.info.fps || 30;
        currentFrame = 0;
        _clearPersistedHistory();

        const slider = document.getElementById('frame-slider');
        slider.max = totalFrames - 1;
        slider.value = 0;
        document.getElementById('frame-scrubber').style.display = (appMode === 'quick' && FEATURE_QUICK_MODE) ? 'block' : 'none';

        showPreview(data.preview);
        updateFrameInfo(data.info);
        // Fetch histogram for color analysis (fires even if panel is collapsed — data is cached)
        fetchHistogram();
        const infoStr = data.info.duration
            ? `${file.name} — ${data.info.width}x${data.info.height}, ${totalFrames} frames`
            : `${file.name} — ${data.info.width}x${data.info.height}`;
        showToast(`Loaded: ${infoStr}`, 'success');

        // Suggest perform toggle (toast with action)
        if (appMode === 'timeline' && !performToggleActive) {
            showToast('Try the Perform mixer?', 'info', {
                label: 'Open Mixer',
                fn: "function(){togglePerformPanel()}",
            }, 5000);
        }

        // Sync timeline with loaded video
        if (window.timelineEditor) {
            timelineEditor.fps = data.info.fps || 30;
            timelineEditor.totalFrames = totalFrames;
            // Create a full-length region on Video 1
            timelineEditor.tracks[0].regions = [
                new Region(timelineEditor.nextRegionId++, 0, 0, totalFrames - 1)
            ];
            timelineEditor.playhead = 0;
            timelineEditor.fitToWindow();
        }
    } catch (err) {
        hideLoading();
        showErrorToast(`Upload failed: ${err.message}`, err.stack);
        fileNameEl.classList.remove('uploading');
    }
}

function updateFrameInfo(info) {
    const el = document.getElementById('frame-info');
    if (!info) { el.style.display = 'none'; return; }
    el.style.display = 'block';
    const w = info.width || '?';
    const h = info.height || '?';
    const fps = info.fps ? info.fps.toFixed(1) : '?';
    let label = `${w}x${h} | ${fps}fps | Frame ${currentFrame}/${totalFrames}`;
    const src = info.source_type;
    if (src === 'image') label += ' | Still Image';
    else if (src === 'gif') label += ' | GIF';
    else if (src === 'raw_interpretation') label += ' | Raw Data Viz';
    el.textContent = label;
}

// ============ PANEL TABS ============

function setupPanelTabs() {
    document.querySelectorAll('.panel-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            document.getElementById(`${target}-tab`).classList.add('active');
        });
    });
}

// ============ KEYBOARD SHORTCUTS ============

function setupKeyboard() {
    const isTextInput = () => ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
    const isMod = (e) => e.metaKey || e.ctrlKey;
    const isModalOpen = () => {
        return document.getElementById('export-overlay')?.style.display === 'flex'
            || document.getElementById('input-modal-overlay')?.style.display === 'flex'
            || document.getElementById('shortcut-overlay')?.style.display === 'flex'
            || document.getElementById('help-overlay')?.style.display === 'flex';
    };

    document.addEventListener('keydown', e => {
        // --- Escape: close any open modal ---
        if (e.key === 'Escape') {
            if (document.getElementById('help-overlay')?.style.display === 'flex') {
                closeHelpPanel(); e.preventDefault(); return;
            }
            if (document.getElementById('shortcut-overlay')?.style.display === 'flex') {
                closeShortcutRef(); e.preventDefault(); return;
            }
            if (document.getElementById('input-modal-overlay')?.style.display === 'flex') {
                closeInputModal(); e.preventDefault(); return;
            }
            if (document.getElementById('export-overlay')?.style.display === 'flex') {
                closeExportDialog(); e.preventDefault(); return;
            }
            // Deselect effect
            if (selectedLayerId !== null) {
                selectedLayerId = null;
                renderLayers();
            }
            return;
        }

        // --- Modifier shortcuts (work even in text inputs for some) ---

        // Cmd+Z = Undo
        if (isMod(e) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault(); undo(); return;
        }
        // Cmd+Shift+Z = Redo
        if (isMod(e) && e.key === 'z' && e.shiftKey) {
            e.preventDefault(); redo(); return;
        }
        // Cmd+D = Duplicate selected
        if (isMod(e) && e.key === 'd') {
            e.preventDefault(); duplicateSelected(); return;
        }
        // Cmd+G = Create group from selected
        if (isMod(e) && e.key === 'g' && !e.shiftKey) {
            e.preventDefault(); addGroup(); return;
        }
        // Cmd+Shift+G = Ungroup selected
        if (isMod(e) && e.key === 'g' && e.shiftKey) {
            e.preventDefault(); ungroupSelected(); return;
        }
        // Cmd+O = Open file
        if (isMod(e) && e.key === 'o') {
            e.preventDefault();
            document.getElementById('file-input').click();
            return;
        }
        // Cmd+E = Export
        if (isMod(e) && e.key === 'e') {
            e.preventDefault(); renderVideo(); return;
        }
        // Cmd+S = Save project (any mode)
        if (isMod(e) && e.key === 's') {
            e.preventDefault();
            saveProject();
            return;
        }
        // Cmd+R = Create region from I/O (timeline mode)
        if (isMod(e) && e.key === 'r' && appMode === 'timeline' && window.timelineEditor) {
            e.preventDefault();
            timelineEditor.createRegionFromIO();
            return;
        }
        // Cmd+0 = Fit timeline to window
        if (isMod(e) && (e.key === '0' || e.code === 'Digit0') && appMode === 'timeline' && window.timelineEditor) {
            e.preventDefault();
            timelineEditor.fitToWindow();
            return;
        }
        // Cmd+Shift+C = Capture retroactive buffer
        if (isMod(e) && e.shiftKey && e.key === 'c') {
            e.preventDefault();
            capturePerformBuffer();
            return;
        }
        // Cmd+W = Close (same as quit in single-window)
        if (isMod(e) && e.key === 'w') {
            // Let PyWebView handle this natively
            return;
        }

        // --- Non-modifier shortcuts: skip if typing in text input or modal open ---
        if (isTextInput() || isModalOpen()) return;

        // Space = Play/pause (mode-dependent)
        if (e.code === 'Space' && videoLoaded) {
            e.preventDefault();
            if (appMode === 'perform' || (appMode === 'timeline' && performToggleActive)) {
                perfTogglePlay();
            } else if (appMode === 'timeline' && window.timelineEditor) {
                timelineEditor.togglePlayback();
            } else if (!isShowingOriginal) {
                isShowingOriginal = true;
                const img = document.getElementById('preview-img');
                originalPreviewSrc = img.src;
                fetch(`${API}/api/frame/${currentFrame}`)
                    .then(r => r.json())
                    .then(data => { if (isShowingOriginal) img.src = data.preview; });
            }
            return;
        }

        // --- Perform mode shortcuts (keys 1-8, R, Shift+P, M, Escape, Q/W/E/R/A/S/D/F) ---
        // Active in full Perform mode OR when Perform toggle is on in Timeline mode
        if ((appMode === 'perform' || (appMode === 'timeline' && performToggleActive)) && videoLoaded && perfLayers.length > 0) {
            // Keys 1-8: trigger layers (one-shot fire, blocked during review)
            if (e.key >= '1' && e.key <= '8') {
                e.preventDefault();
                if (!perfReviewing) {
                    const layerId = parseInt(e.key) - 1;
                    perfTriggerLayer(layerId, 'keydown');
                }
                return;
            }
            // M: toggle keyboard perform mode
            if (e.key === 'm') {
                e.preventDefault();
                toggleKeyboardPerformMode();
                return;
            }
            // K: toggle key hint overlay (when in keyboard perform mode)
            if (e.key === 'k' && keyboardPerformMode) {
                e.preventDefault();
                toggleKeyHintOverlay();
                return;
            }
            // Escape: panic + exit keyboard mode
            if (e.key === 'Escape' && keyboardPerformMode) {
                e.preventDefault();
                perfPanic();
                toggleKeyboardPerformMode(false);
                return;
            }
            // Shift+R: toggle automation recording
            if (e.key === 'R' && e.shiftKey) {
                e.preventDefault();
                toggleAutoRecording();
                return;
            }
            // Keyboard perform mode: Q/W/E/R = layers 0-3, A/S/D/F = layers 4-7
            if (keyboardPerformMode && !perfReviewing) {
                const kbMap = { q: 0, w: 1, e: 2, r: 3, a: 4, s: 5, d: 6, f: 7 };
                const layerId = kbMap[e.key.toLowerCase()];
                if (layerId !== undefined) {
                    e.preventDefault();
                    perfTriggerLayer(layerId, 'keydown');
                    return;
                }
            }
            // R: toggle recording (blocked during review, skip if Shift held)
            if (e.key === 'r' && !e.shiftKey && !keyboardPerformMode) {
                e.preventDefault();
                if (!perfReviewing) {
                    perfToggleRecord();
                }
                return;
            }
            // Shift+P: panic
            if (e.key === 'P' && e.shiftKey) {
                e.preventDefault();
                perfPanic();
                return;
            }
        }

        // Delete/Backspace = remove selected
        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedLayerId !== null) {
            e.preventDefault(); removeFromChain(selectedLayerId); return;
        }

        // --- Single-key shortcuts (chain editing) ---

        // [ = Move selected effect UP in chain
        if (e.key === '[' && selectedLayerId !== null) {
            e.preventDefault(); moveDevice(selectedLayerId, -1); return;
        }
        // ] = Move selected effect DOWN in chain
        if (e.key === ']' && selectedLayerId !== null) {
            e.preventDefault(); moveDevice(selectedLayerId, 1); return;
        }
        // B = Toggle bypass on selected
        if (e.key === 'b' && selectedLayerId !== null) {
            e.preventDefault(); toggleBypass(selectedLayerId); return;
        }
        // R = Reset selected to defaults
        if (e.key === 'r' && selectedLayerId !== null) {
            e.preventDefault(); resetDeviceParams(selectedLayerId); return;
        }
        // Up/Down = Select prev/next effect in chain
        if (e.key === 'ArrowUp' && chain.length > 0) {
            e.preventDefault();
            const idx = chain.findIndex(d => d.id === selectedLayerId);
            if (idx > 0) { selectedLayerId = chain[idx - 1].id; renderLayers(); }
            else if (idx === -1) { selectedLayerId = chain[chain.length - 1].id; renderLayers(); }
            return;
        }
        if (e.key === 'ArrowDown' && chain.length > 0) {
            e.preventDefault();
            const idx = chain.findIndex(d => d.id === selectedLayerId);
            if (idx < chain.length - 1 && idx >= 0) { selectedLayerId = chain[idx + 1].id; renderLayers(); }
            else if (idx === -1) { selectedLayerId = chain[0].id; renderLayers(); }
            return;
        }

        // P = Toggle Perform panel (in timeline mode)
        if (e.key === 'p' && appMode === 'timeline') {
            e.preventDefault(); togglePerformPanel(); return;
        }

        // Left/Right = Prev/next frame
        if (e.key === 'ArrowLeft' && videoLoaded) {
            e.preventDefault();
            const jump = e.shiftKey ? 10 : 1;
            currentFrame = Math.max(0, currentFrame - jump);
            document.getElementById('frame-slider').value = currentFrame;
            if (appMode === 'timeline' && window.timelineEditor) {
                timelineEditor.setPlayhead(currentFrame);
            } else {
                schedulePreview();
            }
            return;
        }
        if (e.key === 'ArrowRight' && videoLoaded) {
            e.preventDefault();
            const jump = e.shiftKey ? 10 : 1;
            currentFrame = Math.min(totalFrames - 1, currentFrame + jump);
            document.getElementById('frame-slider').value = currentFrame;
            if (appMode === 'timeline' && window.timelineEditor) {
                timelineEditor.setPlayhead(currentFrame);
            } else {
                schedulePreview();
            }
            return;
        }

        // --- Timeline-only shortcuts ---
        if (appMode === 'timeline' && window.timelineEditor) {
            // I = Set in-point
            if (e.key === 'i') {
                e.preventDefault(); timelineEditor.setInPoint(); return;
            }
            // O = Set out-point
            if (e.key === 'o') {
                e.preventDefault(); timelineEditor.setOutPoint(); return;
            }
            // Home = Jump to start
            if (e.key === 'Home') {
                e.preventDefault(); timelineEditor.setPlayhead(0); return;
            }
            // End = Jump to last frame
            if (e.key === 'End') {
                e.preventDefault(); timelineEditor.setPlayhead(totalFrames - 1); return;
            }
            // + or = = Zoom in
            if (e.key === '+' || e.key === '=') {
                e.preventDefault(); timelineEditor.zoomIn(); return;
            }
            // - = Zoom out
            if (e.key === '-') {
                e.preventDefault(); timelineEditor.zoomOut(); return;
            }
            // M = Mute selected track
            if (e.key === 'm' && !e.shiftKey) {
                e.preventDefault(); timelineEditor.toggleTrackMute(timelineEditor.selectedTrackId); return;
            }
            // Shift+M = Unmute all
            if (e.key === 'M' && e.shiftKey) {
                e.preventDefault(); timelineEditor.unmuteAll(); return;
            }
            // S = Solo selected track (only if no effect selected, else conflicts with existing)
            if (e.key === 's' && selectedLayerId === null) {
                e.preventDefault(); timelineEditor.toggleTrackSolo(timelineEditor.selectedTrackId); return;
            }
            // Delete = delete selected region (if no effect selected)
            if ((e.key === 'Delete' || e.key === 'Backspace') && selectedLayerId === null && timelineEditor.selectedRegionId !== null) {
                e.preventDefault(); timelineEditor.deleteSelectedRegion(); return;
            }
        }

        // Tab = Toggle sidebar
        if (e.key === 'Tab') {
            e.preventDefault();
            const browser = document.getElementById('browser');
            if (browser) {
                browser.style.display = browser.style.display === 'none' ? '' : 'none';
            }
            return;
        }

        // H = Show help panel
        if (e.key === 'h') {
            e.preventDefault(); showHelpPanel(); return;
        }

        // ? = Show shortcut reference
        if (e.key === '?') {
            e.preventDefault(); showShortcutRef(); return;
        }
    });

    document.addEventListener('keyup', e => {
        if (e.code === 'Space' && isShowingOriginal) {
            e.preventDefault();
            isShowingOriginal = false;
            const img = document.getElementById('preview-img');
            if (originalPreviewSrc) img.src = originalPreviewSrc;
        }
        // Perform mode: key release for gate/adsr (blocked during review)
        if ((appMode === 'perform' || (appMode === 'timeline' && performToggleActive)) && !perfReviewing) {
            // Number keys 1-8
            if (e.key >= '1' && e.key <= '8') {
                const layerId = parseInt(e.key) - 1;
                perfTriggerLayer(layerId, 'keyup');
            }
            // Keyboard perform: Q/W/E/R/A/S/D/F keyup for gate/adsr release
            if (keyboardPerformMode) {
                const kbMap = { q: 0, w: 1, e: 2, r: 3, a: 4, s: 5, d: 6, f: 7 };
                const layerId = kbMap[e.key.toLowerCase()];
                if (layerId !== undefined) {
                    perfTriggerLayer(layerId, 'keyup');
                }
            }
        }
    });
}

// ============ EFFECT CHAIN ============

function addToChain(effectName, overrideParams) {
    const def = effectDefs.find(e => e.name === effectName);
    if (!def) return;

    const device = {
        id: deviceIdCounter++,
        name: effectName,
        params: {},
        bypassed: false,
        mix: 1.0,
    };

    // Copy defaults, then apply overrides (from recipe/package)
    for (const [k, v] of Object.entries(def.params)) {
        if (overrideParams && k in overrideParams) {
            device.params[k] = overrideParams[k];
        } else if (v.type === 'xy') {
            device.params[k] = [...v.default];
        } else {
            device.params[k] = v.default;
        }
    }

    // Inject default points for curves effect (list params not serialized by API)
    if (effectName === 'curves' && !device.params.points) {
        device.params.points = [[0, 0], [64, 64], [128, 128], [192, 192], [255, 255]];
    }

    chain.push(device);
    selectedLayerId = device.id;
    pushHistory(`Add ${effectName}`);
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

function removeFromChain(deviceId) {
    const device = chain.find(d => d.id === deviceId);
    chain = chain.filter(d => d.id !== deviceId);
    if (selectedLayerId === deviceId) {
        selectedLayerId = chain.length > 0 ? chain[chain.length - 1].id : null;
    }
    pushHistory(`Remove ${device?.name || 'effect'}`);
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

function toggleBypass(deviceId) {
    const device = _findItemInChain(chain, deviceId);
    if (device) {
        device.bypassed = !device.bypassed;
        const state = device.bypassed ? 'Off' : 'On';
        pushHistory(`${device.name} ${state}`);
        syncChainToRegion();
        renderChain();
        renderLayers();
        schedulePreview();
    }
}

function updateDeviceMix(deviceId, value) {
    const device = _findItemInChain(chain, deviceId);
    if (device) {
        device.mix = parseInt(value) / 100;
        const span = document.querySelector(`.mix-slider[data-device="${deviceId}"]`);
        if (span) {
            const valSpan = span.parentElement.querySelector('.mix-value');
            if (valSpan) valSpan.textContent = `${parseInt(value)}%`;
        }
        schedulePreview();
    }
}

// Blend mode labels (short display names)
const _BLEND_MODES = ['normal', 'multiply', 'screen', 'overlay', 'add', 'difference', 'soft_light'];
function _blendLabel(mode) {
    if (!mode || mode === 'normal') return 'N';
    return {'multiply':'M', 'screen':'S', 'overlay':'O', 'add':'A', 'difference':'D', 'soft_light':'SL'}[mode] || 'N';
}

function toggleBlendMenu(deviceId, btn) {
    // Close existing blend menu if open
    const existing = document.querySelector('.blend-menu');
    if (existing) { existing.remove(); return; }

    const menu = document.createElement('div');
    menu.className = 'blend-menu';
    menu.innerHTML = _BLEND_MODES.map(m =>
        `<div class="blend-option" data-mode="${m}" onclick="setBlendMode(${deviceId}, '${m}', this)">${m.replace('_', ' ')}</div>`
    ).join('');
    btn.parentElement.appendChild(menu);

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closeBM(e) {
            if (!menu.contains(e.target) && e.target !== btn) {
                menu.remove();
                document.removeEventListener('click', closeBM);
            }
        });
    }, 10);
}

function setBlendMode(deviceId, mode, optionEl) {
    const device = _findItemInChain(chain, deviceId);
    if (!device) return;
    if (device.type === 'group') {
        device.blend_mode = mode;
    } else {
        if (!device.params) device.params = {};
        device.params.blend_mode = mode;
    }
    // Update button label
    const btn = optionEl.closest('.device, .device-group')?.querySelector('.blend-toggle');
    if (btn) {
        btn.textContent = _blendLabel(mode);
        btn.classList.toggle('active', mode !== 'normal');
    }
    // Close menu
    const menu = optionEl.closest('.blend-menu');
    if (menu) menu.remove();
    schedulePreview();
}

function duplicateSelected() {
    if (selectedLayerId === null) return;
    const device = chain.find(d => d.id === selectedLayerId);
    if (!device) return;
    const clone = {
        id: deviceIdCounter++,
        name: device.name,
        params: JSON.parse(JSON.stringify(device.params)),
        bypassed: device.bypassed,
        mix: device.mix ?? 1.0,
    };
    // Insert after the selected device
    const idx = chain.findIndex(d => d.id === selectedLayerId);
    chain.splice(idx + 1, 0, clone);
    selectedLayerId = clone.id;
    pushHistory(`Duplicate ${device.name}`);
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

function flattenChain() {
    // Remove all bypassed effects
    const removed = chain.filter(d => d.bypassed).length;
    if (removed === 0) return;
    chain = chain.filter(d => !d.bypassed);
    pushHistory(`Flatten (removed ${removed})`);
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

// ============ PARAMETER PRESETS PER EFFECT ============
// Stored in localStorage: { effectName: { presetName: {params} } }
const _paramPresets = JSON.parse(localStorage.getItem('entropic_param_presets') || '{}');
function _saveParamPresets() {
    localStorage.setItem('entropic_param_presets', JSON.stringify(_paramPresets));
}

function _buildPresetDropdown(device) {
    const presets = _paramPresets[device.name] || {};
    const presetNames = Object.keys(presets);
    if (presetNames.length === 0) {
        return `<select class="device-preset-select" onchange="loadDevicePreset(${device.id}, this.value); this.selectedIndex=0" onclick="event.stopPropagation()">
            <option value="">Presets</option>
            <option value="__save__">Save Current...</option>
            <option value="__default__">Reset to Default</option>
        </select>`;
    }
    let opts = '<option value="">Presets</option>';
    for (const name of presetNames) {
        opts += `<option value="${esc(name)}">${esc(name)}</option>`;
    }
    opts += '<option disabled>---</option>';
    opts += '<option value="__save__">Save Current...</option>';
    opts += '<option value="__default__">Reset to Default</option>';
    if (presetNames.length > 0) {
        opts += '<option value="__delete__">Delete Preset...</option>';
    }
    return `<select class="device-preset-select" onchange="loadDevicePreset(${device.id}, this.value); this.selectedIndex=0" onclick="event.stopPropagation()">${opts}</select>`;
}

function loadDevicePreset(deviceId, presetName) {
    const device = _findItemInChain(chain, deviceId);
    if (!device) return;

    if (presetName === '__save__') {
        const name = prompt('Preset name:');
        if (!name) return;
        if (!_paramPresets[device.name]) _paramPresets[device.name] = {};
        _paramPresets[device.name][name] = JSON.parse(JSON.stringify(device.params));
        _saveParamPresets();
        showToast(`Saved preset: ${name}`, 'success');
        renderChain();
        return;
    }

    if (presetName === '__default__') {
        const def = effectDefs.find(e => e.name === device.name);
        if (def) {
            device.params = JSON.parse(JSON.stringify(def.params));
            pushHistory(`Reset ${device.name} to default`);
            renderChain();
            renderLayers();
            schedulePreview();
            showToast('Reset to default parameters', 'info');
        }
        return;
    }

    if (presetName === '__delete__') {
        const presets = _paramPresets[device.name] || {};
        const names = Object.keys(presets);
        if (names.length === 0) return;
        const name = prompt(`Delete preset (${names.join(', ')}):`);
        if (name && presets[name]) {
            delete presets[name];
            _saveParamPresets();
            showToast(`Deleted preset: ${name}`, 'info');
            renderChain();
        }
        return;
    }

    // Load named preset
    const presets = _paramPresets[device.name] || {};
    if (presets[presetName]) {
        device.params = JSON.parse(JSON.stringify(presets[presetName]));
        pushHistory(`Load preset: ${presetName}`);
        renderChain();
        renderLayers();
        schedulePreview();
        showToast(`Loaded preset: ${presetName}`, 'success');
    }
}

function _renderDeviceHTML(device) {
    // Render a group item
    if (device.type === 'group') {
        const bypassClass = device.bypassed ? 'bypassed' : '';
        const powerClass = device.bypassed ? 'off' : 'on';
        const arrowClass = device.collapsed ? 'collapsed' : '';
        const childrenClass = device.collapsed ? 'collapsed' : '';
        const childCount = (device.children || []).length;
        const childrenHtml = (device.children || []).map(c => _renderDeviceHTML(c)).join('');
        const mixPct = Math.round((device.mix ?? 1.0) * 100);

        return `
            <div class="device-group ${bypassClass}" data-device-id="${device.id}" draggable="true">
                <div class="group-header" onclick="toggleGroupCollapse(${device.id})">
                    <span class="group-collapse-arrow ${arrowClass}">&#9660;</span>
                    <button class="device-power ${powerClass}" onclick="event.stopPropagation(); toggleBypass(${device.id})" title="${device.bypassed ? 'Turn On' : 'Turn Off'}">${device.bypassed ? 'OFF' : 'ON'}</button>
                    <span class="group-name" ondblclick="event.stopPropagation(); renameGroup(${device.id})">${esc(device.name)}</span>
                    <span class="group-badge">${childCount} fx</span>
                    <span class="device-mix" title="Group Mix: ${mixPct}% — 0% = bypass group, 100% = full effect chain">
                        <label>Mix</label>
                        <input type="range" class="mix-slider" min="0" max="100" value="${mixPct}"
                               data-device="${device.id}"
                               oninput="event.stopPropagation(); updateDeviceMix(${device.id}, this.value)"
                               onclick="event.stopPropagation()">
                        <span class="mix-value">${mixPct}%</span>
                    </span>
                    <button class="blend-toggle ${device.blend_mode && device.blend_mode !== 'normal' ? 'active' : ''}"
                            onclick="event.stopPropagation(); toggleBlendMenu(${device.id}, this)"
                            data-tooltip="Blend mode">${_blendLabel(device.blend_mode)}</button>
                </div>
                <div class="group-children ${childrenClass}">
                    ${childrenHtml}
                </div>
            </div>`;
    }

    // Render a normal effect device
    const def = effectDefs.find(e => e.name === device.name);
    const bypassClass = device.bypassed ? 'bypassed' : '';
    const powerClass = device.bypassed ? 'off' : 'on';

    let essentialHtml = '';
    let advancedHtml = '';
    const essentialList = controlMap?.effects?.[device.name]?.essential;

    if (def) {
        for (const [key, spec] of Object.entries(def.params)) {
            const value = device.params[key] ?? spec.default;
            const ctrlSpec = controlMap?.effects?.[device.name]?.params?.[key];
            const ctrlType = ctrlSpec?.control_type || (spec.type === 'string' ? 'dropdown' : spec.type === 'bool' ? 'toggle' : 'knob');
            const html = createControl(device.id, key, spec, value, ctrlType, ctrlSpec);

            if (essentialList && !essentialList.includes(key)) {
                advancedHtml += html;
            } else {
                essentialHtml += html;
            }
        }
    }

    const advancedCount = advancedHtml ? (advancedHtml.match(/class="(param-control|knob-container|dropdown-container|toggle-container)/g) || []).length : 0;
    const advancedToggle = advancedCount > 0
        ? `<button class="params-toggle" onclick="this.nextElementSibling.classList.toggle('open'); this.classList.toggle('open')">All Parameters (${advancedCount})</button><div class="params-advanced">${advancedHtml}</div>`
        : '';

    const mixPct = Math.round((device.mix ?? 1.0) * 100);
    const presetDropdown = _buildPresetDropdown(device);

    return `
        <div class="device ${bypassClass}" data-device-id="${device.id}" draggable="true"
             oncontextmenu="deviceContextMenu(event, ${device.id})">
            <div class="device-header">
                ${gripHTML()}
                <button class="device-power ${powerClass}" onclick="toggleBypass(${device.id})" title="${device.bypassed ? 'Turn On' : 'Turn Off'}">${device.bypassed ? 'OFF' : 'ON'}</button>
                <span class="device-name">${esc(device.name)}</span>
                ${presetDropdown}
                <span class="device-mix" title="Mix: ${mixPct}% — 0% = original frame, 100% = full effect">
                    <label>Mix</label>
                    <input type="range" class="mix-slider" min="0" max="100" value="${mixPct}"
                           data-device="${device.id}"
                           oninput="updateDeviceMix(${device.id}, this.value)"
                           onclick="event.stopPropagation()">
                    <span class="mix-value">${mixPct}%</span>
                </span>
                <button class="blend-toggle ${device.params?.blend_mode && device.params.blend_mode !== 'normal' ? 'active' : ''}"
                        onclick="event.stopPropagation(); toggleBlendMenu(${device.id}, this)"
                        data-tooltip="Blend mode">${_blendLabel(device.params?.blend_mode)}</button>
                <button class="more-btn" onclick="event.stopPropagation(); deviceContextMenu(event, ${device.id})" title="More options">&#8943;</button>
            </div>
            <div class="device-params">
                ${essentialHtml}${advancedToggle}
            </div>
        </div>`;
}

function renderChain() {
    const rack = document.getElementById('chain-rack');
    const totalDevices = _countDevices(chain);
    document.getElementById('chain-count').textContent = `${totalDevices} device${totalDevices !== 1 ? 's' : ''}`;
    updateChainComplexity(totalDevices);

    rack.innerHTML = chain.map(device => _renderDeviceHTML(device)).join('');

    // Re-attach control event listeners
    document.querySelectorAll('.knob').forEach(setupKnobInteraction);
    document.querySelectorAll('.param-dropdown').forEach(setupDropdownInteraction);
    document.querySelectorAll('.param-toggle').forEach(setupToggleInteraction);

    // Setup device reordering
    setupDeviceReorder();

    // Re-apply LFO-mapped state to knob containers
    cleanLfoMappings();
    for (const mapping of lfoState.mappings) {
        const knobEl = document.querySelector(`.knob[data-device="${mapping.deviceId}"][data-param="${mapping.paramName}"]`);
        if (knobEl) {
            const container = knobEl.closest('.knob-container');
            if (container) container.classList.add('lfo-mapped');
        }
    }
    renderLfoPanel();

    // Re-apply automation-mapped state to knob containers
    applyAutomationMappedState();

    // Mark overflowing param panels
    document.querySelectorAll('.device-params').forEach(panel => {
        if (panel.scrollHeight > panel.clientHeight) {
            const total = panel.querySelectorAll('.param-control, .dropdown-container, .toggle-container').length;
            const visible = Array.from(panel.children).filter(c => {
                const rect = c.getBoundingClientRect();
                const parentRect = panel.getBoundingClientRect();
                return rect.bottom <= parentRect.bottom;
            }).length;
            const hidden = total - visible;
            if (hidden > 0) {
                panel.classList.add('has-overflow');
                panel.dataset.overflowHint = `+${hidden} more`;
            }
        } else {
            panel.classList.remove('has-overflow');
        }
    });
}

// ============ LAYERS PANEL (Photoshop-style) ============

function renderLayers() {
    const list = document.getElementById('layers-list');

    // PERFORM MODE: show perform layers instead of chain
    if ((appMode === 'perform' || (appMode === 'timeline' && performToggleActive)) && perfLayers.length > 0) {
        list.innerHTML = perfLayers.map((l, i) => {
            const state = perfLayerStates[l.layer_id] || {};
            const isActive = state.active || l.trigger_mode === 'always_on';
            const opacity = Math.round((state.opacity ?? l.opacity) * 100);
            const color = PERF_LAYER_COLORS[i] || '#888';
            const modeTag = l.trigger_mode.replace('_', ' ');
            const powerClass = state.muted ? 'off' : 'on';
            const activeClass = isActive ? 'selected' : '';
            const mutedClass = state.muted ? 'bypassed-layer' : '';

            return `
                <div class="layer-item ${activeClass} ${mutedClass}"
                     onclick="perfSelectLayerForEdit(${l.layer_id})">
                    <button class="layer-power ${powerClass}"
                          onclick="event.stopPropagation(); perfToggleMute(${l.layer_id})"
                          title="${state.muted ? 'Unmute' : 'Mute'}">${state.muted ? 'OFF' : 'ON'}</button>
                    <span class="layer-color-dot" style="background:${color};width:8px;height:8px;border-radius:50%;flex-shrink:0;"></span>
                    <span class="layer-name">${l.name}</span>
                    <span class="layer-index" style="min-width:32px;">${opacity}%</span>
                    <span class="layer-index">${modeTag}</span>
                </div>`;
        }).join('');
        return;
    }

    // Layers are rendered top-to-bottom (last in chain = top layer, like Photoshop)
    const reversed = [...chain].reverse();

    list.innerHTML = reversed.map((device, i) => {
        const layerNum = chain.length - i;
        const selectedClass = device.id === selectedLayerId ? 'selected' : '';
        const bypassedClass = device.bypassed ? 'bypassed-layer' : '';
        const powerClass = device.bypassed ? 'off' : 'on';

        return `
            <div class="layer-item ${selectedClass} ${bypassedClass}"
                 data-layer-id="${device.id}"
                 onclick="selectLayer(${device.id})"
                 oncontextmenu="layerContextMenu(event, ${device.id})"
                 draggable="true">
                <button class="layer-power ${powerClass}" onclick="event.stopPropagation(); toggleBypass(${device.id})" title="${device.bypassed ? 'Turn On' : 'Turn Off'}">${device.bypassed ? 'OFF' : 'ON'}</button>
                ${gripHTML()}
                <span class="layer-name">${esc(device.name)}</span>
                <span class="layer-index">${layerNum}</span>
                <button class="more-btn" onclick="event.stopPropagation(); layerContextMenu(event, ${device.id})" title="More">&#8943;</button>
            </div>`;
    }).join('');

    if (chain.length === 0) {
        list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-dim);font-size:11px;">No effects added yet</div>';
    }

    // Setup layer drag reorder
    setupLayerReorder();
}

function selectLayer(deviceId) {
    selectedLayerId = deviceId;
    renderLayers();
}

function setupLayerReorder() {
    const items = document.querySelectorAll('.layer-item[draggable]');
    items.forEach(item => {
        item.addEventListener('dragstart', e => {
            e.dataTransfer.setData('layer-id', item.dataset.layerId);
        });
        item.addEventListener('dragover', e => {
            e.preventDefault();
            if (e.dataTransfer.types.includes('layer-id')) {
                item.style.borderTopColor = 'var(--accent)';
                item.style.borderTopWidth = '2px';
            }
        });
        item.addEventListener('dragleave', () => {
            item.style.borderTopColor = '';
            item.style.borderTopWidth = '';
        });
        item.addEventListener('drop', e => {
            item.style.borderTopColor = '';
            item.style.borderTopWidth = '';
            const fromId = parseInt(e.dataTransfer.getData('layer-id'));
            const toId = parseInt(item.dataset.layerId);
            if (!isNaN(fromId) && fromId !== toId) {
                reorderChain(fromId, toId);
            }
        });
    });
}

// ============ HISTORY PANEL (Photoshop-style) ============

function renderHistory() {
    const list = document.getElementById('history-list');

    // Render most recent first (reverse display order)
    const indices = history.map((_, i) => i).reverse();
    list.innerHTML = indices.map(i => {
        const entry = history[i];
        let cls = '';
        if (i === historyIndex) cls = 'current';
        else if (i > historyIndex) cls = 'future';

        const time = entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        // Pick icon based on action
        let icon = '+';
        if (entry.action.startsWith('Remove')) icon = '-';
        else if (entry.action.includes('Off') || entry.action.includes('On')) icon = '~';
        else if (entry.action.startsWith('Reorder')) icon = '=';
        else if (entry.action.startsWith('Duplicate')) icon = '++';
        else if (entry.action.startsWith('Flatten')) icon = '[]';
        else if (entry.action === 'Open') icon = '>';

        return `
            <div class="history-item ${cls}" onclick="jumpToHistory(${i})">
                <span class="history-icon">${icon}</span>
                <span class="history-text">${entry.action}</span>
                <span class="history-time">${time}</span>
            </div>`;
    }).join('');

    // Auto-scroll to current
    const currentEl = list.querySelector('.current');
    if (currentEl) currentEl.scrollIntoView({ block: 'nearest' });
}

// ============ MOOG KNOBS ============

function createControl(deviceId, paramName, spec, value, ctrlType, ctrlSpec) {
    const label = ctrlSpec?.label || paramName;
    if (ctrlType === 'dropdown') {
        return createDropdown(deviceId, paramName, spec, value, label, ctrlSpec);
    } else if (ctrlType === 'toggle') {
        return createToggle(deviceId, paramName, spec, value, label);
    } else {
        return createKnob(deviceId, paramName, spec, value, label);
    }
}

function createDropdown(deviceId, paramName, spec, value, label, ctrlSpec) {
    const options = ctrlSpec?.options || spec.options || [];
    let optionsHtml = '';
    // If we have options from the control map
    if (options.length > 0) {
        optionsHtml = options.map(o =>
            `<option value="${o}" ${o === value ? 'selected' : ''}>${o}</option>`
        ).join('');
    } else if (typeof value === 'string') {
        // Fallback: just show current value
        optionsHtml = `<option value="${value}" selected>${value}</option>`;
    }
    const tooltip = `${label}: ${value} (${options.length} options)`;
    return `
        <div class="param-control dropdown-container" title="${tooltip}">
            <label>${label}</label>
            <select class="param-dropdown" data-device="${deviceId}" data-param="${paramName}">
                ${optionsHtml}
            </select>
        </div>`;
}

function createToggle(deviceId, paramName, spec, value, label) {
    const checked = value ? 'checked' : '';
    const tooltip = `${label}: ${value ? 'ON' : 'OFF'} (click to toggle)`;
    return `
        <div class="param-control toggle-container" title="${tooltip}">
            <label>${label}</label>
            <button class="param-toggle ${value ? 'on' : ''}" data-device="${deviceId}" data-param="${paramName}"
                    data-value="${value ? '1' : '0'}">
                ${value ? 'ON' : 'OFF'}
            </button>
        </div>`;
}

function setupDropdownInteraction(selectEl) {
    selectEl.addEventListener('change', () => {
        const deviceId = parseInt(selectEl.dataset.device);
        const paramName = selectEl.dataset.param;
        const device = chain.find(d => d.id === deviceId);
        if (device) {
            device.params[paramName] = selectEl.value;
            pushHistory(`${device.name}: ${paramName}`);
            syncChainToRegion();
            schedulePreview();
        }
    });
}

function setupToggleInteraction(btnEl) {
    btnEl.addEventListener('click', () => {
        const deviceId = parseInt(btnEl.dataset.device);
        const paramName = btnEl.dataset.param;
        const device = chain.find(d => d.id === deviceId);
        if (device) {
            const newVal = !device.params[paramName];
            device.params[paramName] = newVal;
            btnEl.dataset.value = newVal ? '1' : '0';
            btnEl.classList.toggle('on', newVal);
            btnEl.textContent = newVal ? 'ON' : 'OFF';
            pushHistory(`${device.name}: ${paramName}`);
            syncChainToRegion();
            schedulePreview();
        }
    });
}

function createKnob(deviceId, paramName, spec, value, label) {
    label = label || paramName;
    let normalized;
    if (spec.type === 'bool') {
        normalized = value ? 1 : 0;
    } else if (spec.type === 'xy') {
        normalized = (value[0] - spec.min) / (spec.max - spec.min);
        value = value[0]; // Show x value
    } else if (spec.min > 0 && spec.max / spec.min >= 10 && spec.type === 'float') {
        // Log scaling for wide-range float params
        normalized = (Math.log(Math.max(spec.min, value)) - Math.log(spec.min)) / (Math.log(spec.max) - Math.log(spec.min));
    } else {
        normalized = (value - spec.min) / (spec.max - spec.min);
    }

    const angle = -135 + normalized * 270; // -135 to +135
    const arcLen = 48 * Math.PI;
    const dashLen = normalized * arcLen * 0.75;

    const displayVal = typeof value === 'number'
        ? (Number.isInteger(value) ? value : value.toFixed(2))
        : value;

    const tooltipDesc = spec.description ? ` — ${spec.description}` : '';
    const tooltip = `${label}: ${displayVal} (range: ${spec.min}–${spec.max})${tooltipDesc}`;

    // Sweet spot zone arc (subtle green indicator)
    const sweetMin = spec.sweet_min !== undefined ? (spec.sweet_min - spec.min) / (spec.max - spec.min) : 0.1;
    const sweetMax = spec.sweet_max !== undefined ? (spec.sweet_max - spec.min) / (spec.max - spec.min) : 0.9;
    const zoneStart = sweetMin * arcLen * 0.75;
    const zoneLen = (sweetMax - sweetMin) * arcLen * 0.75;
    const zoneOffset = -arcLen * 0.125 - zoneStart;

    // Danger zone arcs (red at extreme ends: 0-5% and 95-100%)
    const dangerEndStart = 0.95 * arcLen * 0.75;
    const dangerEndLen = 0.05 * arcLen * 0.75;
    const dangerEndOffset = -arcLen * 0.125 - dangerEndStart;
    const dangerStartLen = 0.05 * arcLen * 0.75;
    const dangerStartOffset = -arcLen * 0.125;

    return `
        <div class="knob-container" data-tooltip="${tooltip}">
            <label>${label}</label>
            <div class="knob" data-device="${deviceId}" data-param="${paramName}"
                 data-min="${spec.min}" data-max="${spec.max}" data-type="${spec.type}"
                 data-ui-min="${spec.ui_min !== undefined ? spec.ui_min : spec.min}" data-ui-max="${spec.ui_max !== undefined ? spec.ui_max : spec.max}"
                 data-value="${typeof value === 'object' ? value[0] : value}">
                <svg viewBox="0 0 48 48">
                    <circle class="arc-track" cx="24" cy="24" r="20"
                        stroke-dasharray="${arcLen * 0.75} ${arcLen}"
                        stroke-dashoffset="${-arcLen * 0.125}"
                        transform="rotate(135 24 24)"/>
                    <circle class="arc-danger" cx="24" cy="24" r="20"
                        stroke-dasharray="${dangerStartLen} ${arcLen}"
                        stroke-dashoffset="${dangerStartOffset}"
                        transform="rotate(135 24 24)"/>
                    <circle class="arc-zone" cx="24" cy="24" r="20"
                        stroke-dasharray="${zoneLen} ${arcLen}"
                        stroke-dashoffset="${zoneOffset}"
                        transform="rotate(135 24 24)"/>
                    <circle class="arc-danger" cx="24" cy="24" r="20"
                        stroke-dasharray="${dangerEndLen} ${arcLen}"
                        stroke-dashoffset="${dangerEndOffset}"
                        transform="rotate(135 24 24)"/>
                    <circle class="arc-fill" cx="24" cy="24" r="20"
                        stroke-dasharray="${dashLen} ${arcLen}"
                        stroke-dashoffset="${-arcLen * 0.125}"
                        transform="rotate(135 24 24)"/>
                </svg>
                <div class="indicator" style="transform: translateX(-50%) rotate(${angle}deg)"></div>
            </div>
            <span class="knob-value">${displayVal}</span>
        </div>`;
}

function setupKnobInteraction(knobEl) {
    let startY, startValue;

    const onMove = (e) => {
        const dy = startY - (e.clientY || e.touches?.[0]?.clientY || startY);
        const sensitivity = e.shiftKey ? 0.001 : 0.005;
        const min = parseFloat(knobEl.dataset.uiMin || knobEl.dataset.min);
        const max = parseFloat(knobEl.dataset.uiMax || knobEl.dataset.max);
        const fullMin = parseFloat(knobEl.dataset.min);
        const fullMax = parseFloat(knobEl.dataset.max);
        const range = max - min;
        const type = knobEl.dataset.type;

        // Use log scaling when parameter has wide range with positive bounds
        // This spreads the "sweet spot" across more of the knob travel
        const useLog = min > 0 && max / min >= 10 && type === 'float';
        let newValue;
        if (useLog) {
            const logMin = Math.log(min);
            const logMax = Math.log(max);
            const logStart = Math.log(Math.max(min, startValue));
            const logVal = logStart + dy * sensitivity * (logMax - logMin);
            newValue = Math.exp(Math.max(logMin, Math.min(logMax, logVal)));
        } else {
            newValue = startValue + dy * sensitivity * range;
        }
        newValue = Math.max(fullMin, Math.min(fullMax, newValue));

        if (type === 'int') newValue = Math.round(newValue);

        knobEl.dataset.value = newValue;
        updateKnobVisual(knobEl, newValue, fullMin, fullMax, type);

        // Update data model
        const rawDeviceId = knobEl.dataset.device;
        const paramName = knobEl.dataset.param;

        if (typeof rawDeviceId === 'string' && rawDeviceId.startsWith('mfx-')) {
            // Master bus effect knob
            const fxIdx = parseInt(rawDeviceId.slice(4));
            if (perfMasterEffects[fxIdx]) {
                perfMasterEffects[fxIdx].params[paramName] = newValue;
                perfSyncMasterEffects();
            }
        } else {
            const deviceId = parseInt(rawDeviceId);
            const device = chain.find(d => d.id === deviceId);
            if (device) {
                const def = effectDefs.find(e => e.name === device.name);
                const spec = def?.params[paramName];
                if (spec?.type === 'xy') {
                    device.params[paramName] = [newValue, 0];
                } else if (spec?.type === 'bool') {
                    device.params[paramName] = newValue > 0.5;
                } else {
                    device.params[paramName] = newValue;
                }
                // Automation recording: capture knob movements during playback
                if (autoRecording && perfPlaying) {
                    autoRecordParam(deviceId, paramName, newValue, fullMin, fullMax);
                }
            }
        }

        schedulePreview();
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.removeEventListener('touchmove', onMove);
        document.removeEventListener('touchend', onUp);

        // Push history after knob adjustment is done
        const rawId = knobEl.dataset.device;
        if (typeof rawId === 'string' && rawId.startsWith('mfx-')) {
            // Master bus — no chain history needed
        } else {
            const deviceId = parseInt(rawId);
            const paramName = knobEl.dataset.param;
            const device = chain.find(d => d.id === deviceId);
            if (device) {
                pushHistory(`${device.name}: ${paramName}`);
                syncChainToRegion();
            }
        }
    };

    const onDown = (e) => {
        // Block dragging if LFO-mapped
        const container = knobEl.closest('.knob-container');
        if (container && container.classList.contains('lfo-mapped')) {
            e.preventDefault();
            return;
        }
        e.preventDefault();
        startY = e.clientY || e.touches?.[0]?.clientY;
        startValue = parseFloat(knobEl.dataset.value);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        document.addEventListener('touchmove', onMove);
        document.addEventListener('touchend', onUp);
    };

    knobEl.addEventListener('mousedown', onDown);
    knobEl.addEventListener('touchstart', onDown);

    // Right-click to show knob context menu (Create Automation Lane, etc.)
    knobEl.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        e.stopPropagation();
        knobContextMenu(e, knobEl);
    });

    // Click on value text to type a specific number
    const container = knobEl.closest('.knob-container');
    const valueSpan = container?.querySelector('.knob-value');
    if (valueSpan) {
        valueSpan.addEventListener('click', (e) => {
            e.stopPropagation();
            if (valueSpan.querySelector('.knob-value-input')) return; // already editing

            const deviceId = parseInt(knobEl.dataset.device);
            const paramName = knobEl.dataset.param;
            const device = chain.find(d => d.id === deviceId);
            if (!device) return;
            const def = effectDefs.find(ef => ef.name === device.name);
            const spec = def?.params[paramName];
            if (!spec) return;

            const currentVal = parseFloat(knobEl.dataset.value);
            const displayVal = spec.type === 'int' ? Math.round(currentVal) : currentVal.toFixed(2);

            const input = document.createElement('input');
            input.type = 'number';
            input.className = 'knob-value-input';
            input.value = displayVal;
            input.step = spec.type === 'int' ? '1' : '0.01';
            input.min = spec.min;
            input.max = spec.max;

            const originalText = valueSpan.textContent;
            valueSpan.textContent = '';
            valueSpan.appendChild(input);
            input.select();
            input.focus();

            const commit = () => {
                let newVal = parseFloat(input.value);
                if (isNaN(newVal)) {
                    cancel();
                    return;
                }
                newVal = Math.max(spec.min, Math.min(spec.max, newVal));
                if (spec.type === 'int') newVal = Math.round(newVal);

                knobEl.dataset.value = newVal;
                updateKnobVisual(knobEl, newVal, spec.min, spec.max, spec.type);
                if (spec.type === 'xy') {
                    device.params[paramName] = [newVal, 0];
                } else if (spec.type === 'bool') {
                    device.params[paramName] = newVal > 0.5;
                } else {
                    device.params[paramName] = newVal;
                }
                pushHistory(`${device.name}: ${paramName}`);
                syncChainToRegion();
                schedulePreview();
            };

            const cancel = () => {
                if (input.parentElement === valueSpan) {
                    valueSpan.textContent = originalText;
                }
            };

            input.addEventListener('keydown', (ke) => {
                ke.stopPropagation(); // prevent app shortcuts
                if (ke.key === 'Enter') {
                    commit();
                } else if (ke.key === 'Escape') {
                    cancel();
                }
            });

            input.addEventListener('blur', () => {
                // Only commit if input is still in DOM (not already cancelled)
                if (input.parentElement === valueSpan) {
                    commit();
                }
            });
        });
    }

    // Double-click to reset to default
    knobEl.addEventListener('dblclick', () => {
        const deviceId = parseInt(knobEl.dataset.device);
        const paramName = knobEl.dataset.param;
        const device = chain.find(d => d.id === deviceId);
        if (!device) return;
        const def = effectDefs.find(e => e.name === device.name);
        const spec = def?.params[paramName];
        if (!spec) return;
        const defaultVal = spec.type === 'xy' ? spec.default[0] : spec.default;
        knobEl.dataset.value = defaultVal;
        updateKnobVisual(knobEl, defaultVal, spec.min ?? 0, spec.max ?? 1, spec.type);
        if (spec.type === 'xy') {
            device.params[paramName] = [defaultVal, 0];
        } else {
            device.params[paramName] = defaultVal;
        }
        pushHistory(`Reset ${device.name}: ${paramName}`);
        syncChainToRegion();
        schedulePreview();
    });
}

function updateKnobVisual(knobEl, value, min, max, type) {
    const useLog = min > 0 && max / min >= 10 && type === 'float';
    const normalized = useLog
        ? (Math.log(Math.max(min, value)) - Math.log(min)) / (Math.log(max) - Math.log(min))
        : (value - min) / (max - min);
    const angle = -135 + normalized * 270;
    const arcLen = 48 * Math.PI;
    const dashLen = normalized * arcLen * 0.75;

    const indicator = knobEl.querySelector('.indicator');
    const arcFill = knobEl.querySelector('.arc-fill');
    const valueSpan = knobEl.parentElement.querySelector('.knob-value');

    if (indicator) indicator.style.transform = `translateX(-50%) rotate(${angle}deg)`;
    if (arcFill) arcFill.setAttribute('stroke-dasharray', `${dashLen} ${arcLen}`);
    if (valueSpan && !valueSpan.querySelector('.knob-value-input')) {
        valueSpan.textContent = type === 'int' ? Math.round(value) : value.toFixed(2);
    }
}

// ============ LFO MODULATION ============

const LFO_WAVEFORMS = ['sine','saw','square','triangle','ramp_up','ramp_down','noise','random','bin'];

function lfoWaveform(phase, waveform) {
    const p = ((phase % 1) + 1) % 1; // wrap to 0-1
    switch (waveform) {
        case 'sine':     return 0.5 + 0.5 * Math.sin(2 * Math.PI * p);
        case 'saw':      return p;
        case 'square':   return p < 0.5 ? 1.0 : 0.0;
        case 'triangle': return p < 0.5 ? 2 * p : 2 * (1 - p);
        case 'ramp_up':  return p;
        case 'ramp_down':return 1.0 - p;
        case 'noise': {
            // Pseudo-noise: use a simple hash of quantized phase
            const bucket = Math.floor(p * 64);
            let h = ((lfoState.seed * 2654435761 + bucket * 40503) >>> 0) / 0xFFFFFFFF;
            return Math.max(0, Math.min(1, h));
        }
        case 'random': {
            const bucket = Math.floor(p * 4);
            let h = ((lfoState.seed * 2654435761 + bucket * 40503) >>> 0) / 0xFFFFFFFF;
            return Math.max(0, Math.min(1, h));
        }
        case 'bin':      return Math.sin(2 * Math.PI * p) > 0 ? 1.0 : 0.0;
        default:         return 0.5;
    }
}

function startLfoAnimation() {
    if (lfoAnimFrame) return;
    lfoLastTime = performance.now();
    lfoPhase = 0;

    function tick(now) {
        const dt = (now - lfoLastTime) / 1000;
        lfoLastTime = now;

        if (lfoState.rate > 0) {
            lfoPhase = (lfoPhase + dt * lfoState.rate) % 1.0;
        }

        const phase = (lfoPhase + lfoState.phase_offset) % 1.0;
        const lfoVal = lfoWaveform(phase, lfoState.waveform);
        const bipolar = (lfoVal - 0.5) * 2.0;

        for (const mapping of lfoState.mappings) {
            const device = chain.find(d => d.id === mapping.deviceId);
            if (!device) continue;

            const paramRange = mapping.max - mapping.min;
            const modulated = mapping.baseValue + bipolar * lfoState.depth * paramRange * 0.5;
            const clamped = Math.max(mapping.min, Math.min(mapping.max, modulated));
            device.params[mapping.paramName] = clamped;

            // Update knob visual
            const knobEl = document.querySelector(`.knob[data-device="${mapping.deviceId}"][data-param="${mapping.paramName}"]`);
            if (knobEl) {
                knobEl.dataset.value = clamped;
                updateKnobVisual(knobEl, clamped, mapping.min, mapping.max, knobEl.dataset.type);
            }
        }

        // Update waveform mini-display
        drawLfoWaveformDisplay();

        schedulePreview();
        lfoAnimFrame = requestAnimationFrame(tick);
    }
    lfoAnimFrame = requestAnimationFrame(tick);
}

function stopLfoAnimation() {
    if (lfoAnimFrame) {
        cancelAnimationFrame(lfoAnimFrame);
        lfoAnimFrame = null;
    }
}

function renderLfoPanel() {
    const panel = document.getElementById('lfo-panel');
    if (!panel) return;

    // Always show the LFO panel (it's part of the chain area)
    panel.classList.add('visible');

    const mappingPills = lfoState.mappings.map((m, i) => {
        const device = chain.find(d => d.id === m.deviceId);
        const label = device ? `${device.name}:${m.paramName}` : m.paramName;
        return `<span class="lfo-mapping-pill" onclick="unmapParam(${m.deviceId}, '${esc(m.paramName)}')">
            ${esc(label)} <span class="pill-x">&times;</span>
        </span>`;
    }).join('');

    const waveformOptions = LFO_WAVEFORMS.map(wf =>
        `<option value="${wf}" ${wf === lfoState.waveform ? 'selected' : ''}>${wf}</option>`
    ).join('');

    panel.innerHTML = `
        <div class="lfo-header">
            <span>LFO</span>
            <button class="lfo-map-btn" onclick="toggleMapMode()">Map</button>
            <button class="lfo-clear-btn" onclick="clearAllMappings()">Clear</button>
        </div>
        <div class="lfo-body">
            <div class="knob-container" style="width:52px">
                <label>Rate</label>
                <div class="knob lfo-knob" data-lfo-param="rate" data-value="${lfoState.rate}" data-min="0" data-max="10" data-type="float"
                     style="width:36px;height:36px;">
                    <div class="indicator"></div>
                    <svg viewBox="0 0 44 44" style="width:44px;height:44px;top:-4px;left:-4px;">
                        <circle class="arc-track" cx="22" cy="22" r="18" transform="rotate(135 22 22)"
                                stroke-dasharray="${44*Math.PI*0.75} ${44*Math.PI}" />
                        <circle class="arc-fill" cx="22" cy="22" r="18" transform="rotate(135 22 22)"
                                stroke-dasharray="0 ${44*Math.PI}" />
                    </svg>
                </div>
                <span class="knob-value">${lfoState.rate.toFixed(1)}</span>
            </div>
            <div class="knob-container" style="width:52px">
                <label>Depth</label>
                <div class="knob lfo-knob" data-lfo-param="depth" data-value="${lfoState.depth}" data-min="0" data-max="1" data-type="float"
                     style="width:36px;height:36px;">
                    <div class="indicator"></div>
                    <svg viewBox="0 0 44 44" style="width:44px;height:44px;top:-4px;left:-4px;">
                        <circle class="arc-track" cx="22" cy="22" r="18" transform="rotate(135 22 22)"
                                stroke-dasharray="${44*Math.PI*0.75} ${44*Math.PI}" />
                        <circle class="arc-fill" cx="22" cy="22" r="18" transform="rotate(135 22 22)"
                                stroke-dasharray="0 ${44*Math.PI}" />
                    </svg>
                </div>
                <span class="knob-value">${lfoState.depth.toFixed(2)}</span>
            </div>
            <div class="knob-container" style="width:52px">
                <label>Phase</label>
                <div class="knob lfo-knob" data-lfo-param="phase_offset" data-value="${lfoState.phase_offset}" data-min="0" data-max="1" data-type="float"
                     style="width:36px;height:36px;">
                    <div class="indicator"></div>
                    <svg viewBox="0 0 44 44" style="width:44px;height:44px;top:-4px;left:-4px;">
                        <circle class="arc-track" cx="22" cy="22" r="18" transform="rotate(135 22 22)"
                                stroke-dasharray="${44*Math.PI*0.75} ${44*Math.PI}" />
                        <circle class="arc-fill" cx="22" cy="22" r="18" transform="rotate(135 22 22)"
                                stroke-dasharray="0 ${44*Math.PI}" />
                    </svg>
                </div>
                <span class="knob-value">${lfoState.phase_offset.toFixed(2)}</span>
            </div>
            <select class="lfo-waveform-select" onchange="onLfoWaveformChange(this.value)">
                ${waveformOptions}
            </select>
            <canvas class="lfo-waveform-display" width="200" height="30"></canvas>
        </div>
        <div class="lfo-mappings">${mappingPills}</div>
    `;

    // Setup LFO knob interactions
    panel.querySelectorAll('.lfo-knob').forEach(setupLfoKnobInteraction);

    // Update LFO knob visuals to match current state
    panel.querySelectorAll('.lfo-knob').forEach(knobEl => {
        const param = knobEl.dataset.lfoParam;
        const val = lfoState[param];
        const min = parseFloat(knobEl.dataset.min);
        const max = parseFloat(knobEl.dataset.max);
        updateKnobVisual(knobEl, val, min, max, 'float');
    });

    drawLfoWaveformDisplay();
}

function setupLfoKnobInteraction(knobEl) {
    let startY, startValue;

    const onMove = (e) => {
        const dy = startY - (e.clientY || e.touches?.[0]?.clientY || startY);
        const sensitivity = e.shiftKey ? 0.001 : 0.005;
        const min = parseFloat(knobEl.dataset.min);
        const max = parseFloat(knobEl.dataset.max);
        const range = max - min;
        let newValue = startValue + dy * sensitivity * range;
        newValue = Math.max(min, Math.min(max, newValue));
        knobEl.dataset.value = newValue;
        updateKnobVisual(knobEl, newValue, min, max, 'float');
        const param = knobEl.dataset.lfoParam;
        lfoState[param] = newValue;
        const valueSpan = knobEl.parentElement.querySelector('.knob-value');
        if (valueSpan) valueSpan.textContent = newValue.toFixed(param === 'rate' ? 1 : 2);
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.removeEventListener('touchmove', onMove);
        document.removeEventListener('touchend', onUp);
    };

    const onDown = (e) => {
        e.preventDefault();
        e.stopPropagation();
        startY = e.clientY || e.touches?.[0]?.clientY;
        startValue = parseFloat(knobEl.dataset.value);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        document.addEventListener('touchmove', onMove);
        document.addEventListener('touchend', onUp);
    };

    knobEl.addEventListener('mousedown', onDown);
    knobEl.addEventListener('touchstart', onDown);
}

function drawLfoWaveformDisplay() {
    const canvas = document.querySelector('.lfo-waveform-display');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Draw waveform shape
    ctx.strokeStyle = '#7b61ff';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let x = 0; x < w; x++) {
        const phase = (x / w + lfoState.phase_offset) % 1.0;
        const val = lfoWaveform(phase, lfoState.waveform);
        const y = h - val * h * lfoState.depth - (h * (1 - lfoState.depth) * 0.5);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Draw current phase indicator (vertical line)
    if (lfoAnimFrame) {
        const px = ((lfoPhase + lfoState.phase_offset) % 1.0) * w;
        ctx.strokeStyle = '#ff3d3d';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(px, 0);
        ctx.lineTo(px, h);
        ctx.stroke();
    }
}

function onLfoWaveformChange(wf) {
    lfoState.waveform = wf;
    drawLfoWaveformDisplay();
}

function toggleMapMode() {
    if (lfoState.mapping_mode) {
        exitMapMode();
    } else {
        enterMapMode();
    }
}

function enterMapMode() {
    lfoState.mapping_mode = true;
    document.body.classList.add('lfo-map-mode');

    // Add click listeners to all knobs in the chain
    document.querySelectorAll('#chain-rack .knob-container').forEach(container => {
        const knob = container.querySelector('.knob');
        if (!knob) return;
        // Skip already-mapped, bool, or string params
        const type = knob.dataset.type;
        if (type === 'string' || type === 'bool') return;
        if (container.classList.contains('lfo-mapped')) return;
        knob._lfoMapHandler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            mapParamToLfo(knob);
        };
        knob.addEventListener('click', knob._lfoMapHandler, { capture: true });
    });
}

function exitMapMode() {
    lfoState.mapping_mode = false;
    document.body.classList.remove('lfo-map-mode');

    // Remove map click listeners
    document.querySelectorAll('#chain-rack .knob').forEach(knob => {
        if (knob._lfoMapHandler) {
            knob.removeEventListener('click', knob._lfoMapHandler, { capture: true });
            delete knob._lfoMapHandler;
        }
    });
}

function mapParamToLfo(knobEl) {
    const deviceId = parseInt(knobEl.dataset.device);
    const paramName = knobEl.dataset.param;
    const min = parseFloat(knobEl.dataset.min);
    const max = parseFloat(knobEl.dataset.max);
    const baseValue = parseFloat(knobEl.dataset.value);

    // Check if already mapped
    const existing = lfoState.mappings.find(m => m.deviceId === deviceId && m.paramName === paramName);
    if (existing) {
        exitMapMode();
        return;
    }

    lfoState.mappings.push({ deviceId, paramName, baseValue, min, max });

    // Mark knob as mapped
    const container = knobEl.closest('.knob-container');
    if (container) container.classList.add('lfo-mapped');

    exitMapMode();

    // Start animation if first mapping
    if (lfoState.mappings.length === 1) {
        startLfoAnimation();
    }

    renderLfoPanel();
}

function unmapParam(deviceId, paramName) {
    const idx = lfoState.mappings.findIndex(m => m.deviceId === deviceId && m.paramName === paramName);
    if (idx === -1) return;

    const mapping = lfoState.mappings[idx];

    // Restore base value
    const device = chain.find(d => d.id === deviceId);
    if (device) {
        device.params[paramName] = mapping.baseValue;
    }

    lfoState.mappings.splice(idx, 1);

    // Remove lfo-mapped class
    const knobEl = document.querySelector(`.knob[data-device="${deviceId}"][data-param="${paramName}"]`);
    if (knobEl) {
        const container = knobEl.closest('.knob-container');
        if (container) container.classList.remove('lfo-mapped');
        updateKnobVisual(knobEl, mapping.baseValue, mapping.min, mapping.max, knobEl.dataset.type);
    }

    // Stop animation if no mappings left
    if (lfoState.mappings.length === 0) {
        stopLfoAnimation();
    }

    renderLfoPanel();
    schedulePreview();
}

function clearAllMappings() {
    // Restore all base values
    for (const mapping of [...lfoState.mappings]) {
        unmapParam(mapping.deviceId, mapping.paramName);
    }
}

// --- Operator Mapping Expansion ---

function knobContextMenu(e, knobEl) {
    const deviceId = parseInt(knobEl.dataset.device);
    const paramName = knobEl.dataset.param;
    const device = chain.find(d => d.id === deviceId);
    if (!device) return;

    const idx = chain.findIndex(d => d.id === deviceId);
    const container = knobEl.closest('.knob-container');
    const isLfoMapped = container?.classList.contains('lfo-mapped');
    const isAutoMapped = container?.classList.contains('auto-mapped');

    const items = [];

    // Automation lane actions
    if (window.timelineEditor) {
        const selectedRegion = window.timelineEditor.findRegion(window.timelineEditor.selectedRegionId);
        if (selectedRegion) {
            const existingLane = window.timelineEditor.automationLanes.find(
                l => l.regionId === selectedRegion.id && l.effectIndex === idx && l.paramName === paramName
            );
            if (existingLane) {
                items.push({ label: 'Show Automation Lane', action: 'showLane', data: { laneId: existingLane.id } });
                items.push({ label: 'Delete Automation Lane', action: 'deleteLaneFromKnob', data: { laneId: existingLane.id } });
            } else {
                items.push({ label: 'Create Automation Lane', action: 'createLaneFromKnob', data: { regionId: selectedRegion.id, effectIndex: idx, paramName } });
            }
            items.push('---');
        }
    }

    // LFO mapping actions
    if (isLfoMapped) {
        items.push({ label: 'Unmap from LFO', action: 'unmapLfo', data: { deviceId, paramName } });
    } else {
        items.push({ label: 'Map to LFO', action: 'mapToLfo', data: { knobEl } });
    }

    ctxTarget = { type: 'knob', id: deviceId };
    showContextMenu(e, items);
}

function handleKnobCtxAction(action, itemData) {
    if (!itemData) return;
    switch (action) {
        case 'createLaneFromKnob': {
            const { regionId, effectIndex, paramName } = itemData;
            const lane = window.timelineEditor.addAutomationLane(regionId, effectIndex, paramName);
            window.timelineEditor.selectedLaneId = lane.id;
            window.timelineEditor.automationVisible = true;
            window.timelineEditor.draw();
            applyAutomationMappedState();
            showToast(`Automation lane: ${paramName}`, 'success');
            break;
        }
        case 'showLane': {
            const { laneId } = itemData;
            window.timelineEditor.selectedLaneId = laneId;
            window.timelineEditor.automationVisible = true;
            window.timelineEditor.draw();
            break;
        }
        case 'deleteLaneFromKnob': {
            const { laneId } = itemData;
            window.timelineEditor.removeAutomationLane(laneId);
            applyAutomationMappedState();
            showToast('Automation lane deleted', 'info');
            break;
        }
        case 'unmapLfo': {
            const { deviceId, paramName } = itemData;
            unmapParam(deviceId, paramName);
            break;
        }
        case 'mapToLfo': {
            const { knobEl } = itemData;
            mapParamToLfo(knobEl);
            break;
        }
    }
}

function applyAutomationMappedState() {
    // Remove all existing auto-mapped classes
    document.querySelectorAll('.knob-container.auto-mapped').forEach(c => {
        c.classList.remove('auto-mapped');
        c.style.removeProperty('--auto-lane-color');
    });

    if (!window.timelineEditor) return;
    const editor = window.timelineEditor;
    const selectedRegion = editor.findRegion(editor.selectedRegionId);
    if (!selectedRegion) return;

    // For each automation lane targeting this region, mark the knob
    for (const lane of editor.automationLanes) {
        if (lane.regionId !== selectedRegion.id) continue;
        const device = chain[lane.effectIndex];
        if (!device) continue;
        const knobEl = document.querySelector(`.knob[data-device="${device.id}"][data-param="${lane.paramName}"]`);
        if (!knobEl) continue;
        const container = knobEl.closest('.knob-container');
        if (!container) continue;
        container.classList.add('auto-mapped');
        container.style.setProperty('--auto-lane-color', lane.color);
    }
}

function buildLfoConfig() {
    if (lfoState.mappings.length === 0) return null;

    const mappings = lfoState.mappings.map(m => {
        // Convert deviceId to effect_idx (position in non-bypassed chain)
        const activeChain = chain.filter(d => !d.bypassed);
        const idx = activeChain.findIndex(d => d.id === m.deviceId);
        if (idx === -1) return null;
        return {
            effect_idx: idx,
            param: m.paramName,
            base_value: m.baseValue,
            min: m.min,
            max: m.max,
        };
    }).filter(Boolean);

    if (mappings.length === 0) return null;

    return {
        rate: lfoState.rate,
        depth: lfoState.depth,
        phase_offset: lfoState.phase_offset,
        waveform: lfoState.waveform,
        seed: lfoState.seed,
        mappings,
    };
}

// Clean orphaned LFO mappings when chain changes
function cleanLfoMappings() {
    const deviceIds = new Set(chain.map(d => d.id));
    const removed = lfoState.mappings.filter(m => !deviceIds.has(m.deviceId));
    if (removed.length > 0) {
        lfoState.mappings = lfoState.mappings.filter(m => deviceIds.has(m.deviceId));
        if (lfoState.mappings.length === 0) stopLfoAnimation();
    }
}

// ============ DEVICE REORDER ============

function setupDeviceReorder() {
    const devices = document.querySelectorAll('.device');
    devices.forEach(dev => {
        dev.addEventListener('dragstart', e => {
            e.dataTransfer.setData('reorder-id', dev.dataset.deviceId);
        });
        dev.addEventListener('dragover', e => {
            e.preventDefault();
            if (e.dataTransfer.types.includes('reorder-id')) {
                dev.style.borderLeftColor = 'var(--accent)';
            }
        });
        dev.addEventListener('dragleave', () => {
            dev.style.borderLeftColor = '';
        });
        dev.addEventListener('drop', e => {
            dev.style.borderLeftColor = '';
            const fromId = parseInt(e.dataTransfer.getData('reorder-id'));
            const toId = parseInt(dev.dataset.deviceId);
            if (!isNaN(fromId) && fromId !== toId) {
                reorderChain(fromId, toId);
            }
        });
    });
}

function reorderChain(fromId, toId) {
    const fromIdx = chain.findIndex(d => d.id === fromId);
    const toIdx = chain.findIndex(d => d.id === toId);
    if (fromIdx === -1 || toIdx === -1) return;

    const [device] = chain.splice(fromIdx, 1);
    chain.splice(toIdx, 0, device);
    pushHistory(`Reorder ${device.name}`);
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

// ============ PREVIEW ============

function schedulePreview(fromPlayhead) {
    if (!videoLoaded) return;
    clearTimeout(previewDebounce);
    // During timeline playback, skip debounce for fluid updates
    if (window.timelineEditor?.isPlaying) {
        // If called from param/chain change (not playhead advance), invalidate cache
        if (!fromPlayhead && frameCache.size > 0) clearFrameCache();
        previewChain();
        return;
    }
    // Non-playback call: invalidate cache (params/chain may have changed)
    if (frameCache.size > 0) clearFrameCache();
    previewDebounce = setTimeout(previewChain, 50);
}

async function previewChain() {
    if (!videoLoaded) return;
    // Perform mode uses its own preview loop — skip
    if ((appMode === 'perform' || performToggleActive) && perfPlaying) return;

    const isPlaying = window.timelineEditor?.isPlaying;

    // During playback, check frame cache first
    if (isPlaying && frameCache.has(currentFrame)) {
        showPreview(frameCache.get(currentFrame));
        updateMaskOverlay();
        prefetchFrames(currentFrame);
        return;
    }

    try {
        let res;
        const usePerformPreview = (appMode === 'perform' || (appMode === 'timeline' && performToggleActive)) && perfLayers.length > 0;
        if (usePerformPreview) {
            // Perform mode: send trigger events for ADSR processing
            const events = perfTriggerQueue.splice(0);
            const body = { frame_number: currentFrame };
            if (events.length > 0) body.trigger_events = events;
            res = await fetch(`${API}/api/perform/frame`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
        } else if (appMode === 'timeline' && window.timelineEditor) {
            // Timeline mode: send all active regions to server
            const regions = timelineEditor.getActiveRegions().map(r => ({
                start: r.startFrame,
                end: r.endFrame,
                effects: (r.effects || []).filter(e => !e.bypassed),
                muted: timelineEditor.isTrackMuted(r.trackId),
                mask: r.mask || null,
            }));
            res = await fetch(`${API}/api/preview/timeline`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame_number: currentFrame, regions, mix: mixLevel }),
            });
        } else {
            // Flat chain behavior (Quick mode legacy / fallback)
            const activeEffects = chain
                .filter(d => !d.bypassed)
                .map(d => ({ name: d.name, params: { ...d.params, mix: d.mix ?? 1.0 } }));
            res = await fetch(`${API}/api/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ effects: activeEffects, frame_number: currentFrame, mix: mixLevel }),
            });
        }
        const data = await res.json();
        showPreview(data.preview);
        updateMaskOverlay();

        // Cache the result during playback
        if (isPlaying) {
            frameCache.set(currentFrame, data.preview);
            prefetchFrames(currentFrame);
        }

        // Show warning if video-level effects were skipped
        if (data.warning) {
            showErrorToast(data.warning);
        }
        // Sync perform mode UI with server envelope states
        if (data.layer_states && (appMode === 'perform' || performToggleActive)) {
            perfSyncWithServer(data.layer_states);
        }
    } catch (err) {
        if (err.response) {
            try { handleApiError(await err.response.json(), 'Preview failed'); } catch (_) {}
        } else {
            showToast('Preview failed: ' + err.message, 'warning');
        }
    }
}

// Pre-fetch upcoming frames during playback (fire-and-forget, overlapped)
function prefetchFrames(fromFrame) {
    if (appMode !== 'timeline' || !window.timelineEditor) return;

    // Evict old frames if cache is too large
    if (frameCache.size > FRAME_CACHE_MAX) {
        const keysToDelete = [];
        for (const key of frameCache.keys()) {
            if (key < fromFrame - 2) keysToDelete.push(key);
            if (frameCache.size - keysToDelete.length <= FRAME_CACHE_MAX / 2) break;
        }
        keysToDelete.forEach(k => frameCache.delete(k));
    }

    for (let i = 1; i <= FRAME_CACHE_LOOKAHEAD; i++) {
        const targetFrame = fromFrame + i;
        if (targetFrame >= totalFrames) break;
        if (frameCache.has(targetFrame) || frameCacheInFlight.has(targetFrame)) continue;

        frameCacheInFlight.add(targetFrame);
        fetchFrameForCache(targetFrame).then(dataUrl => {
            if (dataUrl && window.timelineEditor?.isPlaying) {
                frameCache.set(targetFrame, dataUrl);
            }
            frameCacheInFlight.delete(targetFrame);
        }).catch(() => {
            frameCacheInFlight.delete(targetFrame);
        });
    }
}

// Fetch a single frame for the pre-cache
async function fetchFrameForCache(frameNum) {
    const regions = window.timelineEditor.getActiveRegions().map(r => ({
        start: r.startFrame,
        end: r.endFrame,
        effects: (r.effects || []).filter(e => !e.bypassed),
        muted: window.timelineEditor.isTrackMuted(r.trackId),
        mask: r.mask || null,
    }));
    const res = await fetch(`${API}/api/preview/timeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame_number: frameNum, regions, mix: mixLevel }),
    });
    const data = await res.json();
    return data.preview;
}

function clearFrameCache() {
    frameCache.clear();
    frameCacheInFlight.clear();
}

function showPreview(dataUrl) {
    const img = document.getElementById('preview-img');
    img.src = dataUrl;
    img.style.display = 'block';
    document.getElementById('empty-state').style.display = 'none';
    // Show diff toolbar when we have a preview
    const dt = document.getElementById('diff-toolbar');
    if (dt) dt.style.display = 'flex';
    // Auto-update diff if active
    if (_diffMode && _diffRef) diffShow(_diffMode);
}

// ============ FRAME DIFF COMPARISON TOOL ============
let _diffRef = null;   // reference ImageData
let _diffMode = null;  // 'diff' | 'split' | null

function diffCapture() {
    const img = document.getElementById('preview-img');
    if (!img.src || img.style.display === 'none') return;
    const c = document.createElement('canvas');
    c.width = img.naturalWidth;
    c.height = img.naturalHeight;
    const ctx = c.getContext('2d');
    ctx.drawImage(img, 0, 0);
    _diffRef = ctx.getImageData(0, 0, c.width, c.height);
}

function diffShow(mode) {
    if (!_diffRef) { diffCapture(); return; }
    const img = document.getElementById('preview-img');
    const dc = document.getElementById('diff-canvas');
    if (!img.src || img.style.display === 'none' || !dc) return;
    dc.width = img.naturalWidth;
    dc.height = img.naturalHeight;
    dc.style.display = 'block';
    const ctx = dc.getContext('2d');
    // Draw current frame
    const tc = document.createElement('canvas');
    tc.width = dc.width; tc.height = dc.height;
    const tctx = tc.getContext('2d');
    tctx.drawImage(img, 0, 0);
    const cur = tctx.getImageData(0, 0, dc.width, dc.height);
    _diffMode = mode;
    if (mode === 'diff') {
        // R/B heatmap of absolute pixel difference
        const out = ctx.createImageData(dc.width, dc.height);
        for (let i = 0; i < cur.data.length; i += 4) {
            const dr = Math.abs(cur.data[i] - _diffRef.data[i]);
            const dg = Math.abs(cur.data[i+1] - _diffRef.data[i+1]);
            const db = Math.abs(cur.data[i+2] - _diffRef.data[i+2]);
            const d = (dr + dg + db) / 3;
            out.data[i] = Math.min(255, d * 4);     // Red = difference
            out.data[i+1] = 0;
            out.data[i+2] = Math.min(255, (255 - d * 4));  // Blue = similarity
            out.data[i+3] = 255;
        }
        ctx.putImageData(out, 0, 0);
    } else if (mode === 'split') {
        // Left = reference, Right = current
        const half = Math.floor(dc.width / 2);
        const refCanvas = document.createElement('canvas');
        refCanvas.width = dc.width; refCanvas.height = dc.height;
        const rctx = refCanvas.getContext('2d');
        rctx.putImageData(_diffRef, 0, 0);
        ctx.drawImage(refCanvas, 0, 0, half, dc.height, 0, 0, half, dc.height);
        ctx.drawImage(img, half, 0, dc.width - half, dc.height, half, 0, dc.width - half, dc.height);
        // Divider line
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(half, 0);
        ctx.lineTo(half, dc.height);
        ctx.stroke();
    }
}

function diffClear() {
    _diffRef = null;
    _diffMode = null;
    const dc = document.getElementById('diff-canvas');
    if (dc) { dc.style.display = 'none'; }
}

// ============ CONTEXT MENU ============

let ctxTarget = null; // {type: 'device'|'layer'|'canvas', id: ...}

function showContextMenu(e, items) {
    e.preventDefault();
    e.stopPropagation();
    const menu = document.getElementById('ctx-menu');

    menu.innerHTML = items.map((item, idx) => {
        if (item === '---') return '<div class="ctx-sep"></div>';
        if (item.disabled) {
            return `<div class="ctx-item disabled">${item.label}</div>`;
        }
        const cls = item.danger ? 'ctx-item danger' : 'ctx-item';
        const shortcut = item.shortcut ? `<span class="ctx-shortcut">${item.shortcut}</span>` : '';
        const dataAttr = item.data ? ` data-ctx-idx="${idx}"` : '';
        return `<div class="${cls}"${dataAttr} onclick="ctxAction('${item.action}', ${idx}); hideContextMenu()">${item.label}${shortcut}</div>`;
    }).join('');
    // Stash items for data lookup
    menu._items = items;

    // Position near cursor, keep on screen
    const x = Math.min(e.clientX, window.innerWidth - 180);
    const y = Math.min(e.clientY, window.innerHeight - items.length * 30);
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.classList.add('visible');
}

function hideContextMenu() {
    document.getElementById('ctx-menu').classList.remove('visible');
    ctxTarget = null;
}

// Close menu on click anywhere
document.addEventListener('click', hideContextMenu);

function ctxAction(action, itemIdx) {
    if (!ctxTarget) return;
    const id = ctxTarget.id;
    const menu = document.getElementById('ctx-menu');
    const itemData = menu._items?.[itemIdx]?.data;
    switch (action) {
        case 'duplicate':
            selectedLayerId = id;
            duplicateSelected();
            break;
        case 'remove':
            removeFromChain(id);
            break;
        case 'bypass':
            toggleBypass(id);
            break;
        case 'moveUp':
            moveDevice(id, -1);
            break;
        case 'moveDown':
            moveDevice(id, 1);
            break;
        case 'solo':
            soloDevice(id);
            break;
        case 'flatten':
            flattenChain();
            break;
        case 'clearAll':
            if (chain.length === 0) return;
            chain = [];
            selectedLayerId = null;
            pushHistory('Clear all');
            syncChainToRegion();
            renderChain();
            renderLayers();
            schedulePreview();
            break;
        case 'resetParams':
            resetDeviceParams(id);
            break;
        case 'freezeRegion':
            freezeRegion(id);
            break;
        case 'unfreezeRegion':
            unfreezeRegion(id);
            break;
        case 'flattenRegion':
            flattenRegion(id);
            break;
        case 'automate':
            // Region-level automate action (from onRegionRightClick)
            if (window.timelineEditor && itemData) {
                const { regionId, effectIndex, paramName } = itemData;
                const lane = window.timelineEditor.addAutomationLane(regionId, effectIndex, paramName);
                window.timelineEditor.selectedLaneId = lane.id;
                window.timelineEditor.automationVisible = true;
                window.timelineEditor.draw();
                showToast(`Automation lane: ${paramName}`, 'success');
            }
            break;
        case 'simplifyLane':
            if (window.timelineEditor && window._laneCtxData) {
                window.timelineEditor.simplifyLane(window._laneCtxData.lane.id);
            }
            break;
        case 'deleteLane':
            if (window.timelineEditor && window._laneCtxData) {
                window.timelineEditor.removeAutomationLane(window._laneCtxData.lane.id);
                showToast('Automation lane deleted', 'info');
            }
            break;
        case 'flattenLaneToStatic':
            if (window.timelineEditor && window._laneCtxData) {
                // Convert automation to per-frame step values and remove the lane
                const lcd = window._laneCtxData;
                const lane = lcd.lane;
                const region = window.timelineEditor.findRegion(lane.regionId);
                if (region) {
                    // Bake each frame value
                    for (let f = region.startFrame; f <= region.endFrame; f++) {
                        const val = window.timelineEditor.getLaneValue(lane, f);
                        if (val !== null && region.effects[lane.effectIndex]) {
                            // Store baked value in the effect's params
                            // (This is a simplified flatten - stores last frame's value)
                        }
                    }
                    // Store the final value (at playhead) as static
                    const staticVal = window.timelineEditor.getLaneValue(lane, window.timelineEditor.playhead);
                    if (staticVal !== null && region.effects[lane.effectIndex]) {
                        region.effects[lane.effectIndex].params[lane.paramName] = staticVal;
                    }
                    window.timelineEditor.removeAutomationLane(lane.id);
                    showToast('Lane flattened to static value', 'info');
                    renderChain();
                    schedulePreview();
                }
            }
            break;
        // Knob context menu actions (right-click on knob)
        case 'createLaneFromKnob':
        case 'showLane':
        case 'deleteLaneFromKnob':
        case 'unmapLfo':
        case 'mapToLfo':
            handleKnobCtxAction(action, itemData);
            break;
        default:
            // Handle parameter switching on automation lanes
            if (action.startsWith('switchParam_') && window.timelineEditor && window._laneCtxData) {
                const newParam = action.replace('switchParam_', '');
                const lane = window._laneCtxData.lane;
                lane.paramName = newParam;
                lane.keyframes = [];  // Clear keyframes since param changed
                window.timelineEditor.draw();
                showToast(`Lane switched to: ${newParam}`, 'info');
                break;
            }
            // Handle shape insertion
            if (action.startsWith('shape_') && window.timelineEditor && window._laneCtxData) {
                const shapeName = action.replace('shape_', '');
                const lcd = window._laneCtxData;
                window.timelineEditor.insertShape(lcd.lane, shapeName, lcd.shapeStart, lcd.shapeEnd);
                showToast(`Inserted: ${shapeName}`, 'success');
                break;
            }
            // Handle automation lane creation: automate_{effectIndex}_{paramName}
            if (action.startsWith('automate_') && window.timelineEditor) {
                const parts = action.split('_');
                const effectIndex = parseInt(parts[1]);
                const paramName = parts.slice(2).join('_');
                const selectedRegion = window.timelineEditor.findRegion(window.timelineEditor.selectedRegionId);
                if (selectedRegion) {
                    const lane = window.timelineEditor.addAutomationLane(selectedRegion.id, effectIndex, paramName);
                    window.timelineEditor.selectedLaneId = lane.id;
                    window.timelineEditor.automationVisible = true;
                    window.timelineEditor.draw();
                    applyAutomationMappedState();
                    showToast(`Automation lane: ${paramName}`, 'success');
                }
            }
            break;
    }
}

function deviceContextMenu(e, deviceId) {
    ctxTarget = { type: 'device', id: deviceId };
    const device = chain.find(d => d.id === deviceId);
    const idx = chain.findIndex(d => d.id === deviceId);
    const def = effectDefs.find(ed => ed.name === device?.name);

    // Build automation submenu items for numeric params
    const automateItems = [];
    if (def && window.timelineEditor) {
        const selectedRegion = window.timelineEditor.findRegion(window.timelineEditor.selectedRegionId);
        if (selectedRegion) {
            for (const [key, spec] of Object.entries(def.params)) {
                if (spec.type === 'string' || spec.type === 'bool') continue;
                const existing = window.timelineEditor.automationLanes.find(
                    l => l.regionId === selectedRegion.id && l.effectIndex === idx && l.paramName === key
                );
                if (!existing) {
                    automateItems.push({
                        label: `Automate: ${key}`,
                        action: `automate_${idx}_${key}`,
                    });
                }
            }
        }
    }

    const items = [
        { label: device?.bypassed ? 'Turn On' : 'Turn Off', action: 'bypass', shortcut: 'Click power' },
        { label: 'Isolate (hide others)', action: 'solo' },
        '---',
        { label: 'Duplicate', action: 'duplicate', shortcut: 'Cmd+D' },
        { label: 'Reset Parameters', action: 'resetParams' },
        '---',
        { label: 'Move Up', action: 'moveUp', shortcut: idx > 0 ? '' : '(first)' },
        { label: 'Move Down', action: 'moveDown', shortcut: idx < chain.length - 1 ? '' : '(last)' },
    ];

    if (automateItems.length > 0) {
        items.push('---');
        items.push(...automateItems);
    }

    items.push('---');
    items.push({ label: 'Remove', action: 'remove', danger: true, shortcut: 'Del' });

    showContextMenu(e, items);
}

function layerContextMenu(e, deviceId) {
    ctxTarget = { type: 'layer', id: deviceId };
    const device = chain.find(d => d.id === deviceId);
    showContextMenu(e, [
        { label: device?.bypassed ? 'Show Layer' : 'Hide Layer', action: 'bypass' },
        { label: 'Isolate Layer', action: 'solo' },
        '---',
        { label: 'Duplicate Layer', action: 'duplicate' },
        { label: 'Reset Parameters', action: 'resetParams' },
        '---',
        { label: 'Flatten Visible', action: 'flatten' },
        { label: 'Clear All Layers', action: 'clearAll', danger: true },
        '---',
        { label: 'Delete Layer', action: 'remove', danger: true },
    ]);
}

function moveDevice(deviceId, direction) {
    const idx = chain.findIndex(d => d.id === deviceId);
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= chain.length) return;
    const [device] = chain.splice(idx, 1);
    chain.splice(newIdx, 0, device);
    pushHistory(`Move ${device.name}`);
    renderChain();
    renderLayers();
    schedulePreview();
}

function soloDevice(deviceId) {
    chain.forEach(d => { d.bypassed = d.id !== deviceId; });
    const device = chain.find(d => d.id === deviceId);
    pushHistory(`Isolate ${device?.name}`);
    syncChainToRegion();
    renderChain();
    renderLayers();
    schedulePreview();
}

function resetDeviceParams(deviceId) {
    const device = chain.find(d => d.id === deviceId);
    if (!device) return;
    const def = effectDefs.find(e => e.name === device.name);
    if (!def) return;
    for (const [k, v] of Object.entries(def.params)) {
        if (v.type === 'xy') {
            device.params[k] = [...v.default];
        } else {
            device.params[k] = v.default;
        }
    }
    pushHistory(`Reset ${device.name}`);
    syncChainToRegion();
    renderChain();
    schedulePreview();
}

// ============ RANDOMIZE ============

async function randomizeChain() {
    try {
        const res = await fetch(`${API}/api/randomize`);
        const data = await res.json();
        // Clear chain and add random effects
        chain = [];
        for (const eff of data.effects) {
            const def = effectDefs.find(e => e.name === eff.name);
            if (!def) continue;
            const device = {
                id: deviceIdCounter++,
                name: eff.name,
                params: eff.params,
                bypassed: false,
            };
            chain.push(device);
        }
        selectedLayerId = chain.length > 0 ? chain[chain.length - 1].id : null;
        pushHistory('Randomize');
        renderChain();
        renderLayers();
        schedulePreview();
        // Show undo toast so user can revert if they didn't want random
        showToast('Chain randomized', 'info', {
            label: 'Undo',
            fn: "function(){undo()}"
        }, 6000);
    } catch (err) {
        showErrorToast('Randomize failed: ' + err.message);
    }
}

// ============ WET/DRY MIX ============

function onMixChange(value) {
    mixLevel = parseInt(value) / 100;
    const el = document.getElementById('mix-value');
    if (el) el.textContent = `${parseInt(value)}%`;
    schedulePreview();
}

// ============ RENDER / EXPORT ============

function renderVideo() {
    if (!videoLoaded) { showToast('Load a file first.', 'info'); return; }
    if (chain.length === 0) { showToast('Add at least one effect.', 'info'); return; }
    openExportDialog();
}

function openExportDialog() {
    document.getElementById('export-overlay').style.display = 'flex';
    document.getElementById('export-mix').value = mixLevel * 100;
    document.getElementById('export-mix-val').textContent = Math.round(mixLevel * 100) + '%';
    onExportFormatChange();
    // Pre-populate range fields from video state
    const fps = videoFps || 30;
    const totalSec = (totalFrames / fps).toFixed(1);
    const curSec = (currentFrame / fps).toFixed(1);
    const outEl = document.getElementById('export-out');
    if (outEl && !outEl.value) outEl.value = totalSec;
    const inEl = document.getElementById('export-in');
    if (inEl) inEl.value = curSec;
}

function closeExportDialog() {
    document.getElementById('export-overlay').style.display = 'none';
}

function onExportFormatChange() {
    const fmt = document.getElementById('export-format').value;
    document.getElementById('h264-quality-row').style.display = (fmt === 'mp4' || fmt === 'webm') ? 'flex' : 'none';
    document.getElementById('h264-preset-row').style.display = fmt === 'mp4' ? 'flex' : 'none';
    document.getElementById('prores-row').style.display = fmt === 'mov' ? 'flex' : 'none';
    document.getElementById('gif-row').style.display = fmt === 'gif' ? 'flex' : 'none';
}

function onExportResChange() {
    const val = document.getElementById('export-resolution').value;
    document.getElementById('custom-dims-row').style.display = val === 'custom' ? 'flex' : 'none';
}

function onExportRangeChange() {
    const mode = document.getElementById('export-range').value;
    document.getElementById('export-duration-row').style.display = mode === 'playhead' ? 'flex' : 'none';
    document.getElementById('export-range-row').style.display = mode === 'custom' ? 'flex' : 'none';
}

async function startExport() {
    const btn = document.getElementById('export-go-btn');
    const origText = btn.textContent;
    btn.textContent = 'Exporting...';
    btn.disabled = true;

    const effects = chain.filter(d => !d.bypassed).map(d => ({
        name: d.name,
        params: { ...d.params },
    }));

    const fmt = document.getElementById('export-format').value;
    const resPre = document.getElementById('export-resolution').value;
    const scaleFactor = document.getElementById('export-scale').value;

    const settings = {
        format: fmt,
        effects,
        mix: parseInt(document.getElementById('export-mix').value) / 100,
        audio_mode: document.getElementById('export-audio').value,
        scale_algorithm: document.getElementById('export-algo').value,
    };

    // Resolution
    if (resPre === 'custom') {
        settings.width = parseInt(document.getElementById('export-width').value) || null;
        settings.height = parseInt(document.getElementById('export-height').value) || null;
    } else if (resPre !== 'source') {
        settings.resolution_preset = resPre;
    }

    // Scale factor overrides resolution
    if (scaleFactor) {
        settings.scale_factor = parseFloat(scaleFactor);
    }

    // FPS
    const fpsVal = document.getElementById('export-fps').value;
    if (fpsVal) settings.fps_preset = fpsVal;

    // Format-specific
    if (fmt === 'mp4') {
        settings.h264_crf = parseInt(document.getElementById('export-crf').value);
        settings.h264_preset = document.getElementById('export-h264-preset').value;
    } else if (fmt === 'mov') {
        settings.prores_profile = document.getElementById('export-prores').value;
    } else if (fmt === 'gif') {
        settings.gif_colors = parseInt(document.getElementById('export-gif-colors').value);
    } else if (fmt === 'webm') {
        settings.webm_crf = parseInt(document.getElementById('export-crf').value);
    }

    // Include LFO config if active
    const lfoConfig = buildLfoConfig();
    if (lfoConfig) settings.lfo_config = lfoConfig;

    // Trim / range selection
    const rangeMode = document.getElementById('export-range').value;
    if (rangeMode === 'playhead') {
        const fps = videoFps || 30;
        const durationSec = parseFloat(document.getElementById('export-duration').value) || 30;
        settings.trim = {
            mode: 'time',
            start_time: currentFrame / fps,
            end_time: (currentFrame / fps) + durationSec,
        };
    } else if (rangeMode === 'custom') {
        const inTime = parseFloat(document.getElementById('export-in').value) || 0;
        const outTime = parseFloat(document.getElementById('export-out').value);
        settings.trim = {
            mode: 'time',
            start_time: inTime,
            end_time: isNaN(outTime) ? null : outTime,
        };
    }

    // In timeline mode, include regions data
    if (appMode === 'timeline' && window.timelineEditor) {
        settings.timeline_regions = timelineEditor.getActiveRegions().map(r => ({
            start: r.startFrame,
            end: r.endFrame,
            effects: (r.effects || []).filter(e => !e.bypassed),
            mask: r.mask || null,
        }));
    }

    showLoading('Exporting...');
    // Poll render progress during export
    const progressInterval = setInterval(async () => {
        try {
            const pRes = await fetch(`${API}/api/render/progress`);
            const prog = await pRes.json();
            if (prog.active && prog.total_frames > 0) {
                updateProgress(prog.current_frame, prog.total_frames,
                    `${prog.phase === 'encoding' ? 'Encoding' : 'Processing'} frame ${prog.current_frame}/${prog.total_frames}`);
            }
        } catch (_) {}
    }, 500);

    try {
        const endpoint = (appMode === 'timeline' && settings.timeline_regions)
            ? `${API}/api/export/timeline`
            : `${API}/api/export`;
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        clearInterval(progressInterval);
        const data = await res.json();
        if (data.status === 'ok') {
            closeExportDialog();
            const sizeMB = data.size_mb ? `${data.size_mb}MB` : '';
            const frames = data.frames ? `${data.frames} frames` : '';
            const dims = data.width && data.height ? `${data.width}x${data.height}` : '';
            const parts = [data.format?.toUpperCase(), dims, frames, sizeMB].filter(Boolean);
            const safePath = (data.path || '').replace(/'/g, "\\'");
            const fileName = safePath.split('/').pop();
            showToast(`Export complete: ${fileName}\n${parts.join(' | ')}`, 'success', {
                label: 'Reveal in Finder',
                fn: `function(){revealInFinder('${safePath}')}`
            }, 12000);
        } else {
            handleApiError(data, 'Export failed');
        }
    } catch (err) {
        clearInterval(progressInterval);
        showErrorToast(`Export error: ${err.message}`);
    } finally {
        hideLoading();
        btn.textContent = origText;
        btn.disabled = false;
    }
}

// ============ A/B COMPARE (Space Bar) ============

let originalPreviewSrc = null;
let isShowingOriginal = false;

// ============ MODE SWITCHING (Timeline / Perform) ============

function setMode(mode) {
    // Feature flag: redirect Quick mode requests to Timeline
    if (mode === 'quick' && !FEATURE_QUICK_MODE) {
        mode = 'timeline';
    }

    // Block mode switch during perform playback (Norman: prevent mode errors)
    if (perfPlaying && appMode === 'perform' && mode !== 'perform') {
        showToast('Stop playback first (Space)', 'info');
        return;
    }

    // Warn about unsaved perform data when leaving perform mode
    if (appMode === 'perform' && mode !== 'perform' && perfEventCount > 0) {
        if (!confirm('You have unsaved performance data. Leave Perform mode?')) return;
    }

    // Stop perform playback if leaving perform mode
    if (appMode === 'perform' && mode !== 'perform') {
        perfStop();
    }

    // When leaving timeline mode, deactivate perform toggle
    if (appMode === 'timeline' && mode !== 'timeline') {
        setPerformToggle(false);
    }

    appMode = mode;
    const appEl = document.getElementById('app');

    // Toggle CSS classes
    appEl.classList.remove('quick-mode', 'perform-mode');
    if (mode === 'quick') appEl.classList.add('quick-mode');
    else if (mode === 'perform') appEl.classList.add('perform-mode');

    // Update mode toggle buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // Update mode badge
    const badge = document.getElementById('mode-badge');
    if (badge) {
        badge.textContent = mode.toUpperCase();
    }

    // Show/hide frame scrubber
    const scrubber = document.getElementById('frame-scrubber');
    if (scrubber) {
        scrubber.style.display = (mode === 'quick' && videoLoaded) ? 'block' : 'none';
    }

    // When entering timeline mode, sync timeline with current state
    if (mode === 'timeline' && window.timelineEditor) {
        timelineEditor.setPlayhead(currentFrame);
        timelineEditor.resize();
    }

    // Deselect region when switching to quick mode
    if (mode === 'quick' && window.timelineEditor) {
        timelineEditor.selectedRegionId = null;
    }

    // When entering perform mode
    if (mode === 'perform') {
        if (!videoLoaded) {
            showToast('Load a video first', 'info');
            appMode = 'timeline';
            appEl.classList.remove('perform-mode');
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === 'timeline');
            });
            if (badge) badge.textContent = 'TIMELINE';
            return;
        }
        perfInitLayers();
    }

    schedulePreview();
}

// ============ PERFORM TOGGLE (within Timeline mode) ============

function setPerformToggle(active) {
    performToggleActive = active;
    const appEl = document.getElementById('app');
    const toggleBtn = document.getElementById('perform-toggle-btn');

    if (active) {
        appEl.classList.add('timeline-perform');
        if (toggleBtn) toggleBtn.classList.add('active');
        // Initialize perform layers if not already loaded
        if (videoLoaded && perfLayers.length === 0) {
            perfInitLayers();
        } else if (perfLayers.length > 0) {
            renderMixer();
        }
    } else {
        appEl.classList.remove('timeline-perform');
        if (toggleBtn) toggleBtn.classList.remove('active');
    }
}

function togglePerformPanel() {
    if (!videoLoaded) {
        showToast('Load a video first', 'info');
        return;
    }
    setPerformToggle(!performToggleActive);
}

// ============ TIMELINE ↔ APP SYNC ============

function onTimelinePlayheadChange(frame) {
    currentFrame = frame;
    const slider = document.getElementById('frame-slider');
    if (slider) slider.value = frame;
    const el = document.getElementById('frame-info');
    if (el && el.style.display === 'block') {
        el.textContent = el.textContent.replace(/Frame \d+\/\d+/, `Frame ${currentFrame}/${totalFrames}`);
    }
    schedulePreview(true);
}

function onRegionSelect(region) {
    if (!window.timelineEditor) return;
    timelineEditor.selectedRegionId = region.id;

    // Load region's effects into the chain rack
    chain = region.effects.map(eff => ({
        id: deviceIdCounter++,
        name: eff.name,
        params: JSON.parse(JSON.stringify(eff.params || {})),
        bypassed: eff.bypassed || false,
    }));
    selectedLayerId = chain.length > 0 ? chain[chain.length - 1].id : null;

    renderChain();
    renderLayers();
    updateMaskOverlay();
    timelineEditor.draw();
}

function onRegionDeselect() {
    if (appMode !== 'timeline') return;
    // When no region is selected, show empty chain
    chain = [];
    selectedLayerId = null;
    renderChain();
    renderLayers();
    clearMaskOverlay();
}

function onRegionRightClick(e, region) {
    const items = [];
    const isFrozen = region._frozen || false;

    // Freeze/Flatten actions
    if (!isFrozen && region.effects && region.effects.length > 0) {
        items.push({ label: 'Freeze Region', action: 'freezeRegion' });
    }
    if (isFrozen) {
        items.push({ label: 'Unfreeze Region', action: 'unfreezeRegion' });
        items.push({ label: 'Flatten (Destructive)', action: 'flattenRegion', danger: true });
    }

    // Automation submenu
    if (region.effects && region.effects.length > 0) {
        const automateItems = [];
        region.effects.forEach((effect, effectIndex) => {
            if (!effect.params) return;
            const paramNames = Object.keys(effect.params).filter(key => {
                const val = effect.params[key];
                return typeof val === 'number' && !isNaN(val);
            });
            if (paramNames.length === 0) return;

            automateItems.push({ label: `${effect.name}`, disabled: true });
            paramNames.forEach(paramName => {
                automateItems.push({
                    label: `  ${paramName}`,
                    action: 'automate',
                    data: { regionId: region.id, effectIndex, paramName }
                });
            });
        });

        if (automateItems.length > 0) {
            if (items.length > 0) items.push('---');
            items.push({ label: 'Add Automation Lane ▸', disabled: true });
            items.push(...automateItems);
        }
    }

    if (items.length === 0) {
        showToast('Add effects to this region first', 'info');
        return;
    }

    ctxTarget = { type: 'region', id: region.id };
    showContextMenu(e, items);
}

async function freezeRegion(regionId) {
    const region = window.timelineEditor?.findRegion(regionId);
    if (!region || !region.effects || region.effects.length === 0) return;

    showToast('Freezing region...', 'info');

    const autoData = window.timelineEditor?.getAutomationSessionData();
    try {
        const resp = await fetch(`${API}/api/timeline/freeze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                region_id: regionId,
                start_frame: region.startFrame,
                end_frame: region.endFrame,
                effects: region.effects,
                automation: autoData?.lanes?.length > 0 ? autoData : null,
                mix: 1.0,
            }),
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            region._frozen = true;
            region._frozenPath = data.path;
            region._originalEffects = JSON.parse(JSON.stringify(region.effects));
            window.timelineEditor?.draw();
            showToast(`Frozen: ${data.frames} frames (${data.size_mb}MB)`, 'success');
        } else {
            showToast('Freeze failed', 'error');
        }
    } catch (err) {
        showToast(`Freeze error: ${err.message}`, 'error');
    }
}

async function unfreezeRegion(regionId) {
    const region = window.timelineEditor?.findRegion(regionId);
    if (!region) return;

    try {
        await fetch(`${API}/api/timeline/freeze/${regionId}`, { method: 'DELETE' });
    } catch (e) { /* cleanup is optional */ }

    region._frozen = false;
    delete region._frozenPath;
    if (region._originalEffects) {
        region.effects = region._originalEffects;
        delete region._originalEffects;
    }
    window.timelineEditor?.draw();
    showToast('Region unfrozen', 'info');
}

async function flattenRegion(regionId) {
    const region = window.timelineEditor?.findRegion(regionId);
    if (!region || !region._frozen) return;

    const confirmed = await showConfirmDialog(
        'Flatten Region',
        'This will permanently bake effects into this region. The original effects and automation will be removed. Continue?'
    );
    if (!confirmed) return;

    // Remove all effects and automation for this region
    region.effects = [];
    region._frozen = false;
    region.label = (region.label || '') + ' [flattened]';
    delete region._originalEffects;

    // Remove automation lanes for this region
    if (window.timelineEditor) {
        window.timelineEditor.automationLanes = window.timelineEditor.automationLanes.filter(
            l => l.regionId !== regionId
        );
        window.timelineEditor.draw();
    }

    showToast('Region flattened (effects baked)', 'success');
    renderChain();
    renderLayers();
}

function syncChainToRegion() {
    if (appMode !== 'timeline') return;
    if (!window.timelineEditor || !timelineEditor.selectedRegionId) return;
    const region = timelineEditor.findRegion(timelineEditor.selectedRegionId);
    if (!region) return;
    region.effects = chain.map(d => ({
        name: d.name,
        params: JSON.parse(JSON.stringify(d.params)),
        bypassed: d.bypassed,
    }));
}

// ============ PROJECT SAVE/LOAD ============

function getProjectState() {
    const state = {
        name: document.getElementById('file-name').textContent || 'Untitled',
        mode: appMode,
        timeline: window.timelineEditor ? timelineEditor.serialize() : null,
        chain: chain.map(d => ({ name: d.name, params: d.params, bypassed: d.bypassed, mix: d.mix ?? 1.0 })),
        mixLevel,
        currentFrame,
        totalFrames,
    };
    // Include perform mode data (full perform mode or timeline+perform toggle)
    if ((appMode === 'perform' || performToggleActive) && perfLayers.length > 0) {
        state.perfLayers = perfLayers;
        state.perfLayerStates = perfLayerStates;
        state.perfSession = perfSession;
        state.perfFrameIndex = perfFrameIndex;
        state.perfMasterEffects = perfMasterEffects;
        // Save LFO state (strip transient _showCfg flag)
        const lfoSave = {};
        for (const [id, lfo] of Object.entries(perfLayerLfos)) {
            lfoSave[id] = { enabled: lfo.enabled, waveform: lfo.waveform, rate: lfo.rate, depth: lfo.depth };
        }
        state.perfLayerLfos = lfoSave;
    }
    return state;
}

async function saveProject() {
    const project = getProjectState();
    showInputModal('Save Project', 'Project name', async (name) => {
        project.name = name;
        try {
            const res = await fetch(`${API}/api/project/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(project),
            });
            const data = await res.json();
            if (data.status === 'ok') {
                showToast(`Project saved: ${name}`, 'success', {
                    label: 'Reveal in Finder',
                    fn: `function(){revealInFinder('${(data.path || '').replace(/'/g, "\\'")}')}`,
                }, 6000);
            }
        } catch (err) {
            showErrorToast(`Save failed: ${err.message}`);
        }
    });
}

async function loadProject() {
    try {
        // First list available projects
        const listRes = await fetch(`${API}/api/project/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const listData = await listRes.json();
        const projects = listData.projects || [];

        if (projects.length === 0) {
            showToast('No saved projects found', 'info');
            return;
        }

        // For now, load the most recent project (future: show a picker)
        const latest = projects[0];
        const loadRes = await fetch(`${API}/api/project/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: latest.path }),
        });
        const loadData = await loadRes.json();

        if (loadData.status === 'ok' && loadData.project) {
            const p = loadData.project;

            // Restore mode
            if (p.mode) setMode(p.mode);

            // Restore timeline
            if (p.timeline && window.timelineEditor) {
                timelineEditor.deserialize(p.timeline);
            }

            // Restore chain
            if (p.chain) {
                chain = p.chain.map(d => ({
                    id: deviceIdCounter++,
                    name: d.name,
                    params: JSON.parse(JSON.stringify(d.params || {})),
                    bypassed: d.bypassed || false,
                    mix: d.mix ?? 1.0,
                }));
                selectedLayerId = chain.length > 0 ? chain[chain.length - 1].id : null;
                renderChain();
                renderLayers();
            }

            // Restore mix
            if (p.mixLevel !== undefined) {
                mixLevel = p.mixLevel;
                const _ms = document.getElementById('mix-slider');
                const _mv = document.getElementById('mix-value');
                if (_ms) _ms.value = mixLevel * 100;
                if (_mv) _mv.textContent = Math.round(mixLevel * 100) + '%';
            }

            // Restore perform mode state
            if (p.perfLayers) {
                perfLayers = p.perfLayers;
                perfLayerStates = p.perfLayerStates || {};
                perfSession = p.perfSession || {type:'performance', lanes:[]};
                perfFrameIndex = p.perfFrameIndex || 0;
                perfMasterEffects = p.perfMasterEffects || [];
                if (appMode === 'perform') renderMixer();
            }

            pushHistory('Load Project');
            schedulePreview();
            showToast(`Project loaded: ${p.name || latest.name}`, 'success');
        }
    } catch (err) {
        showErrorToast(`Load failed: ${err.message}`);
    }
}

// ============ SPATIAL MASK (Rectangle Selection on Canvas) ============

function setupMaskDrawing() {
    const canvasArea = document.getElementById('canvas-area');
    const img = document.getElementById('preview-img');
    if (!canvasArea || !img) return;

    let maskOverlay = document.getElementById('mask-overlay');
    if (!maskOverlay) {
        maskOverlay = document.createElement('div');
        maskOverlay.id = 'mask-overlay';
        maskOverlay.style.cssText = 'position:absolute;border:2px dashed #4caf50;pointer-events:none;display:none;z-index:10;box-shadow:0 0 0 9999px rgba(0,0,0,0.3);';
        canvasArea.appendChild(maskOverlay);
    }

    canvasArea.addEventListener('mousedown', e => {
        if (appMode !== 'timeline') return;
        if (!window.timelineEditor || !timelineEditor.selectedRegionId) return;
        if (e.target !== img && e.target !== canvasArea) return;
        if (e.button !== 0) return;

        // Alt+click to start mask drawing
        if (!e.altKey) return;

        e.preventDefault();
        maskDrawing = true;
        const rect = img.getBoundingClientRect();
        maskStartX = e.clientX - rect.left;
        maskStartY = e.clientY - rect.top;
    });

    document.addEventListener('mousemove', e => {
        if (!maskDrawing) return;
        const img = document.getElementById('preview-img');
        const rect = img.getBoundingClientRect();
        const curX = e.clientX - rect.left;
        const curY = e.clientY - rect.top;

        const x = Math.min(maskStartX, curX);
        const y = Math.min(maskStartY, curY);
        const w = Math.abs(curX - maskStartX);
        const h = Math.abs(curY - maskStartY);

        maskOverlay.style.display = 'block';
        maskOverlay.style.left = (img.offsetLeft + x) + 'px';
        maskOverlay.style.top = (img.offsetTop + y) + 'px';
        maskOverlay.style.width = w + 'px';
        maskOverlay.style.height = h + 'px';

        maskRect = { x, y, w, h, imgW: rect.width, imgH: rect.height };
    });

    document.addEventListener('mouseup', e => {
        if (!maskDrawing) return;
        maskDrawing = false;

        if (!maskRect || maskRect.w < 5 || maskRect.h < 5) {
            // Too small — clear mask
            clearMaskForSelectedRegion();
            return;
        }

        // Convert to 0-1 ratios
        const mask = {
            x: Math.max(0, maskRect.x / maskRect.imgW),
            y: Math.max(0, maskRect.y / maskRect.imgH),
            w: Math.min(1, maskRect.w / maskRect.imgW),
            h: Math.min(1, maskRect.h / maskRect.imgH),
        };

        // Apply to selected region
        if (window.timelineEditor && timelineEditor.selectedRegionId) {
            const region = timelineEditor.findRegion(timelineEditor.selectedRegionId);
            if (region) {
                region.mask = mask;
                showToast(`Mask set: ${Math.round(mask.w * 100)}% x ${Math.round(mask.h * 100)}%`, 'success');
                schedulePreview();
            }
        }

        maskRect = null;
    });
}

function clearMaskForSelectedRegion() {
    if (window.timelineEditor && timelineEditor.selectedRegionId) {
        const region = timelineEditor.findRegion(timelineEditor.selectedRegionId);
        if (region) {
            region.mask = null;
            showToast('Mask cleared (full frame)', 'info');
            clearMaskOverlay();
            schedulePreview();
        }
    }
}

function updateMaskOverlay() {
    const overlay = document.getElementById('mask-overlay');
    if (!overlay) return;

    if (!window.timelineEditor || !timelineEditor.selectedRegionId) {
        overlay.style.display = 'none';
        return;
    }

    const region = timelineEditor.findRegion(timelineEditor.selectedRegionId);
    if (!region || !region.mask) {
        overlay.style.display = 'none';
        return;
    }

    const img = document.getElementById('preview-img');
    if (!img || img.style.display === 'none') {
        overlay.style.display = 'none';
        return;
    }

    const rect = img.getBoundingClientRect();
    const canvasRect = img.parentElement.getBoundingClientRect();
    const m = region.mask;

    overlay.style.display = 'block';
    overlay.style.left = (img.offsetLeft + m.x * rect.width) + 'px';
    overlay.style.top = (img.offsetTop + m.y * rect.height) + 'px';
    overlay.style.width = (m.w * rect.width) + 'px';
    overlay.style.height = (m.h * rect.height) + 'px';
}

function clearMaskOverlay() {
    const overlay = document.getElementById('mask-overlay');
    if (overlay) overlay.style.display = 'none';
}

// ============ PRESETS ============

let presets = [];

function switchBrowserTab(tab) {
    document.querySelectorAll('.browser-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.browser-panel').forEach(p => p.classList.remove('active'));
    document.querySelector(`.browser-tab[data-btab="${tab}"]`).classList.add('active');
    document.getElementById(`${tab}-panel`).classList.add('active');
    if (tab === 'presets' && presets.length === 0) loadPresets();
}

async function loadPresets() {
    try {
        const res = await fetch(`${API}/api/presets`);
        const data = await res.json();
        presets = data.presets || [];
        renderPresets();
    } catch (err) {
        showToast('Failed to load presets', 'warning');
    }
}

function renderPresets() {
    const list = document.getElementById('preset-list');
    if (presets.length === 0) {
        list.innerHTML = '<div style="padding:12px;color:var(--text-dim);font-size:11px;">No presets yet. Add effects and save a preset.</div>';
        return;
    }

    // Group by category
    const grouped = {};
    for (const p of presets) {
        const cat = p.category || 'Uncategorized';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(p);
    }

    let html = '';
    for (const [cat, items] of Object.entries(grouped)) {
        html += `<div class="preset-cat-header">${esc(cat)}</div>`;
        for (const p of items) {
            const tags = (p.tags || []).map(t => `<span class="preset-tag">${esc(t)}</span>`).join('');
            html += `
                <div class="preset-item" onclick="loadPreset(${JSON.stringify(JSON.stringify(p.effects))}, ${p.lfo ? JSON.stringify(JSON.stringify(p.lfo)) : 'null'})" title="${esc(p.description || '')}">
                    <div class="preset-name">${esc(p.name)}</div>
                    <div class="preset-desc">${esc(p.description || '')}</div>
                    ${tags ? `<div class="preset-tags">${tags}</div>` : ''}
                </div>`;
        }
    }
    list.innerHTML = html;
}

function loadPreset(effectsJson, lfoJson) {
    // Clear LFO state
    clearAllMappings();

    const effects = JSON.parse(effectsJson);
    chain = [];
    for (const eff of effects) {
        const def = effectDefs.find(e => e.name === eff.name);
        if (!def) continue;
        const params = {};
        for (const [k, v] of Object.entries(def.params)) {
            params[k] = eff.params && eff.params[k] !== undefined ? eff.params[k] : v.default;
        }
        chain.push({
            id: ++deviceIdCounter,
            name: eff.name,
            params,
            bypassed: false,
        });
    }

    // Restore LFO state if present
    if (lfoJson) {
        const lfo = JSON.parse(lfoJson);
        lfoState.rate = lfo.rate ?? 1.0;
        lfoState.depth = lfo.depth ?? 0.5;
        lfoState.phase_offset = lfo.phase_offset ?? 0;
        lfoState.waveform = lfo.waveform ?? 'sine';
        lfoState.seed = lfo.seed ?? 42;
        // Re-map using new device IDs (mappings reference deviceId by chain position)
        if (lfo.mappings && Array.isArray(lfo.mappings)) {
            for (const m of lfo.mappings) {
                // Find the device by matching name position in chain
                const device = chain[m.deviceId] || chain.find((d, i) => i === m.deviceId);
                if (device) {
                    lfoState.mappings.push({
                        deviceId: device.id,
                        paramName: m.paramName,
                        baseValue: m.baseValue,
                        min: m.min,
                        max: m.max,
                    });
                }
            }
            if (lfoState.mappings.length > 0) startLfoAnimation();
        }
    }

    pushHistory('Load Preset');
    renderChain();
    renderLayers();
    schedulePreview();
}

async function saveCurrentAsPreset() {
    if (chain.length === 0) { showToast('Add effects to the chain first.', 'info'); return; }
    showInputModal('Save Preset', 'Preset name', async (name) => {
        await _doSavePreset(name, '');
    });
}

async function _doSavePreset(name, desc) {
    const effects = chain.filter(d => !d.bypassed).map(d => ({
        name: d.name,
        params: { ...d.params },
    }));

    try {
        const res = await fetch(`${API}/api/presets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, effects, description: desc, tags: [],
                lfo: lfoState.mappings.length > 0 ? {
                    rate: lfoState.rate, depth: lfoState.depth,
                    phase_offset: lfoState.phase_offset, waveform: lfoState.waveform,
                    seed: lfoState.seed, mappings: lfoState.mappings,
                } : undefined }),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            await loadPresets();
            showToast(`Preset "${name}" saved.`, 'success');
        }
    } catch (err) {
        showErrorToast(`Failed to save preset: ${err.message}`);
    }
}

// ============ PERFORM MODE ============

// --- Init ---
async function perfInitLayers() {
    // If chain had effects, migrate them to L2 (handoff from Timeline/Quick)
    let quickChain = null;
    if (chain.length > 0) {
        quickChain = chain.filter(d => !d.bypassed).map(d => ({
            name: d.name,
            params: { ...d.params },
        }));
    }

    try {
        const res = await fetch(`${API}/api/perform/init`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto: true }),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            perfLayers = data.layers;

            // Handoff: existing chain -> L2 effects (L1 is always-on base)
            if (quickChain && quickChain.length > 0 && perfLayers.length > 1) {
                perfLayers[1].effects = quickChain;
                perfLayers[1].name = 'Chain Import';
                // Sync migrated effects to server LayerStack
                fetch(`${API}/api/perform/update_layer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ layer_id: perfLayers[1].layer_id, effects: quickChain }),
                }).catch(() => showToast('Layer sync failed', 'warning'));
            }

            // Init client-side states
            perfLayerStates = {};
            for (const l of perfLayers) {
                perfLayerStates[l.layer_id] = {
                    active: l.trigger_mode === 'always_on',
                    opacity: l.opacity,
                    muted: false,
                    soloed: false,
                };
            }

            // Reset perform state
            perfFrameIndex = 0;
            perfPlaying = false;
            perfRecording = false;
            perfSession = { type: 'performance', lanes: [] };
            perfEventCount = 0;
            perfMasterEffects = data.master_effects || [];
            // Restore per-layer LFO state
            perfLayerLfos = {};
            if (data.perfLayerLfos) {
                for (const [id, lfo] of Object.entries(data.perfLayerLfos)) {
                    perfLayerLfos[id] = { ...lfo, phase: 0, _showCfg: false };
                }
            }

            // Update transport
            perfUpdateTransport();

            // Set duration from video info
            const durEl = document.getElementById('perf-duration');
            if (durEl && totalFrames > 0) {
                const info = totalFrames / 30; // Approximate
                durEl.textContent = formatTime(info);
            }

            const scrubber = document.querySelector('#perf-scrubber input');
            if (scrubber) scrubber.max = totalFrames - 1;

            renderMixer();
            schedulePreview();
        }
    } catch (err) {
        showErrorToast(`Perform init failed: ${err.message}`);
    }
}

// --- Mixer Panel Rendering ---
function renderTriggerContent(mode, isActive) {
    switch (mode) {
        case 'toggle':
            return `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="10" height="10" stroke="currentColor" stroke-width="2" fill="none"/>
            </svg>`;

        case 'gate':
            return `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" fill="${isActive ? 'currentColor' : 'none'}"/>
            </svg>`;

        case 'adsr':
            return `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" class="adsr-ring">
                <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" fill="none"
                    stroke-dasharray="37.7" stroke-dashoffset="94"/>
            </svg>`;

        case 'one_shot':
            return `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 2 L9.5 6.5 L14 6.5 L10.5 9.5 L12 14 L8 11 L4 14 L5.5 9.5 L2 6.5 L6.5 6.5 Z"
                    fill="currentColor" stroke="currentColor" stroke-width="1"/>
            </svg>`;

        case 'always_on':
            return `<div class="always-on-dot"></div>`;

        default:
            return isActive ? 'ON' : 'OFF';
    }
}

function renderMixer() {
    const mixer = document.getElementById('mixer');
    if (!mixer) return;

    let html = '';
    for (let i = 0; i < perfLayers.length; i++) {
        const l = perfLayers[i];
        const state = perfLayerStates[l.layer_id] || {};
        const color = PERF_LAYER_COLORS[i] || '#888';
        const isActive = state.active || false;
        const opacity = state.opacity ?? l.opacity;
        const isMuted = state.muted || false;
        const isSoloed = state.soloed || false;

        // Effect chain summary
        const effectNames = (l.effects || []).map(e => e.name).join(' + ') || 'No effects';

        // Trigger mode display
        const triggerModes = ['toggle', 'gate', 'adsr', 'one_shot', 'always_on'];

        html += `
        <div class="channel-strip ${isActive ? 'active-strip' : ''}" data-layer-id="${l.layer_id}"
             draggable="true"
             ondragstart="perfDragStart(event, ${l.layer_id})"
             ondragover="perfDragOver(event)"
             ondragleave="perfDragLeave(event)"
             ondrop="perfDrop(event, ${l.layer_id})"
             ondragend="perfDragEnd(event)">
            <div class="channel-strip-header">
                <span class="strip-color" style="background:${color}"></span>
                <span class="strip-key">${i + 1}</span>
                <span class="strip-name">${esc(l.name)}</span>
            </div>
            <button class="strip-trigger mode-${l.trigger_mode} ${isActive ? 'lit' : ''}"
                    ${l.trigger_mode === 'always_on' ? '' : `onmousedown="perfTriggerLayer(${l.layer_id}, 'keydown')" onmouseup="perfTriggerLayer(${l.layer_id}, 'keyup')"`}>
                ${renderTriggerContent(l.trigger_mode, isActive)}
            </button>
            <div class="strip-effects" onclick="perfSelectLayerForEdit(${l.layer_id})" title="Click to edit effects">${esc(effectNames)}</div>
            <div class="strip-selectors">
                <select onchange="perfSetTriggerMode(${l.layer_id}, this.value)">
                    ${triggerModes.map(m => `<option value="${m}" ${m === l.trigger_mode ? 'selected' : ''}>${m.replace('_', ' ')}</option>`).join('')}
                </select>
                <select onchange="perfSetAdsrPreset(${l.layer_id}, this.value)">
                    <option value="pluck" ${l.adsr_preset === 'pluck' ? 'selected' : ''}>pluck</option>
                    <option value="sustain" ${l.adsr_preset === 'sustain' ? 'selected' : ''}>sustain</option>
                    <option value="stab" ${l.adsr_preset === 'stab' ? 'selected' : ''}>stab</option>
                    <option value="pad" ${l.adsr_preset === 'pad' ? 'selected' : ''}>pad</option>
                </select>
                <select onchange="perfSetBlendMode(${l.layer_id}, this.value)" title="Blend mode">
                    ${['normal','multiply','screen','overlay','add','difference','soft_light'].map(m =>
                        `<option value="${m}" ${(l.blend_mode || 'normal') === m ? 'selected' : ''}>${m.replace('_', ' ')}</option>`
                    ).join('')}
                </select>
                <select onchange="perfSetChokeGroup(${l.layer_id}, this.value)" title="Choke group">
                    <option value="" ${l.choke_group == null ? 'selected' : ''}>No choke</option>
                    <option value="0" ${l.choke_group === 0 ? 'selected' : ''}>Choke A</option>
                    <option value="1" ${l.choke_group === 1 ? 'selected' : ''}>Choke B</option>
                    <option value="2" ${l.choke_group === 2 ? 'selected' : ''}>Choke C</option>
                </select>
            </div>
            <div class="strip-fader-wrap">
                <input type="range" class="strip-fader" min="0" max="100" value="${Math.round(opacity * 100)}"
                       oninput="perfSetOpacity(${l.layer_id}, this.value / 100)">
                <span class="strip-fader-val">${Math.round(opacity * 100)}%</span>
            </div>
            <div class="strip-lfo-row">
                <button class="strip-lfo-btn ${(perfLayerLfos[l.layer_id] || {}).enabled ? 'lfo-active' : ''}"
                        onclick="perfToggleLayerLfo(${l.layer_id})"
                        title="Toggle opacity LFO">LFO</button>
                <button class="strip-lfo-cfg-btn"
                        onclick="perfShowLfoCfg(${l.layer_id})"
                        title="Configure LFO">&#9881;</button>
            </div>
            ${(perfLayerLfos[l.layer_id] || {})._showCfg ? `
            <div class="strip-lfo-cfg" data-lfo-layer="${l.layer_id}">
                <label>Wave
                <select onchange="perfSetLfoParam(${l.layer_id}, 'waveform', this.value)">
                    ${['sine','square','saw','triangle','bin','ramp_up','ramp_down'].map(w =>
                        `<option value="${w}" ${((perfLayerLfos[l.layer_id] || {}).waveform || 'sine') === w ? 'selected' : ''}>${w}</option>`
                    ).join('')}
                </select></label>
                <label>Rate
                <input type="range" min="0.1" max="10" step="0.1"
                       value="${(perfLayerLfos[l.layer_id] || {}).rate || 1}"
                       oninput="perfSetLfoParam(${l.layer_id}, 'rate', parseFloat(this.value)); this.nextElementSibling.textContent=this.value+'Hz'"
                ><span class="lfo-rate-val">${(perfLayerLfos[l.layer_id] || {}).rate || 1}Hz</span></label>
                <label>Depth
                <input type="range" min="0" max="100" step="1"
                       value="${((perfLayerLfos[l.layer_id] || {}).depth || 1) * 100}"
                       oninput="perfSetLfoParam(${l.layer_id}, 'depth', this.value / 100); this.nextElementSibling.textContent=this.value+'%'"
                ><span class="lfo-depth-val">${Math.round(((perfLayerLfos[l.layer_id] || {}).depth || 1) * 100)}%</span></label>
            </div>` : ''}
            <div class="strip-bottom">
                <button class="${isMuted ? 'muted' : ''}" onclick="perfToggleMute(${l.layer_id})">M</button>
                <button class="${isSoloed ? 'soloed' : ''}" onclick="perfToggleSolo(${l.layer_id})">S</button>
            </div>
        </div>`;
    }

    // Master strip with master bus effects
    const masterFxNames = perfMasterEffects.map(e => e.name).join(' → ') || 'No effects';
    const masterFxCount = perfMasterEffects.length;
    html += `
    <div class="channel-strip master-strip">
        <div class="channel-strip-header">
            <span class="strip-color" style="background:var(--text-dim)"></span>
            <span class="strip-name">MASTER</span>
        </div>
        <div class="master-fx-section">
            <div class="master-fx-header" onclick="perfToggleMasterExpand()">
                <span class="master-fx-label">Bus FX${masterFxCount > 0 ? ` (${masterFxCount})` : ''}</span>
                <span class="master-fx-toggle">${perfMasterExpanded ? '▾' : '▸'}</span>
            </div>
            ${perfMasterExpanded ? `
            <div class="master-fx-list">
                ${perfMasterEffects.map((fx, idx) => {
                    const def = effectDefs.find(e => e.name === fx.name);
                    let paramsHtml = '';
                    if (def && def.params) {
                        for (const [key, spec] of Object.entries(def.params)) {
                            if (spec.type === 'string') continue; // skip dropdowns in compact view
                            const value = fx.params[key] ?? spec.default;
                            paramsHtml += createKnob(`mfx-${idx}`, key, spec, value, key);
                        }
                    }
                    return `
                    <div class="master-fx-item">
                        <div class="master-fx-item-header">
                            <span class="master-fx-name">${esc(fx.name)}</span>
                            <button class="master-fx-remove" onclick="perfRemoveMasterEffect(${idx})" title="Remove">×</button>
                        </div>
                        ${paramsHtml ? `<div class="master-fx-params">${paramsHtml}</div>` : ''}
                    </div>`;
                }).join('')}
                <select class="master-fx-add" onchange="perfAddMasterEffect(this.value); this.selectedIndex=0;">
                    <option value="">+ Add effect...</option>
                    ${effectDefs.map(e => `<option value="${e.name}">${e.name}</option>`).join('')}
                </select>
            </div>
            ` : ''}
        </div>
        <!-- Master fader removed — no audio routing in a video tool -->
        <div class="strip-bottom">
            <button onclick="perfPanic()" title="Reset all layers to initial state (Shift+P)">PANIC</button>
        </div>
        <div style="padding:4px 0;font-size:9px;color:var(--text-dim);text-align:center;">Preview: ${PERF_FPS}fps</div>
    </div>`;

    mixer.innerHTML = html;

    // Bind master bus effect knobs
    mixer.querySelectorAll('.master-fx-params .knob').forEach(setupKnobInteraction);
}

// --- Layer Triggers (3-tier feedback) ---
function perfTriggerLayer(layerId, eventType) {
    const layer = perfLayers.find(l => l.layer_id === layerId);
    if (!layer) return;
    const state = perfLayerStates[layerId];
    if (!state) return;

    // Respect mute
    if (state.muted) return;

    const mode = layer.trigger_mode;

    if (mode === 'always_on') return; // No-op

    if (eventType === 'keydown') {
        if (mode === 'toggle') {
            state.active = !state.active;
        } else if (mode === 'gate' || mode === 'adsr' || mode === 'one_shot') {
            state.active = true;
        }
        // Client-side choke group: deactivate other layers in same group
        if (state.active && layer.choke_group != null && layer.choke_group >= 0) {
            for (const other of perfLayers) {
                if (other.layer_id !== layerId && other.choke_group === layer.choke_group) {
                    const otherState = perfLayerStates[other.layer_id];
                    if (otherState && otherState.active) {
                        otherState.active = false;
                        perfUpdateStripVisuals(other.layer_id);
                        // Flash the choked strip
                        const chokedStrip = document.querySelector(`.channel-strip[data-layer-id="${other.layer_id}"]`);
                        if (chokedStrip) {
                            chokedStrip.classList.add('choked-flash');
                            setTimeout(() => chokedStrip.classList.remove('choked-flash'), 300);
                        }
                    }
                }
            }
        }
        // Queue trigger event for server ADSR processing
        perfTriggerQueue.push({ layer_id: layerId, event: 'on' });
        // Record event for automation
        perfRecordEvent(layerId, 'active', state.active ? 1.0 : 0.0);
        // Retroactive buffer: always capture regardless of recording state
        captureBufferPush(layerId, 'active', state.active ? 1.0 : 0.0);
    } else if (eventType === 'keyup') {
        if (mode === 'gate') {
            state.active = false;
            perfRecordEvent(layerId, 'active', 0.0);
            captureBufferPush(layerId, 'active', 0.0);
        }
        if (mode === 'adsr' || mode === 'gate') {
            // Queue trigger_off for server ADSR release phase
            perfTriggerQueue.push({ layer_id: layerId, event: 'off' });
        }
        // Toggle, one_shot: no-op on keyup (server handles auto-release)
    }

    // Tier 1: INSTANT visual feedback (0ms, client-side only)
    perfUpdateStripVisuals(layerId);

    // Tier 2: Server preview (throttled)
    if (!perfPlaying) {
        schedulePreview();
    }
}

function perfUpdateStripVisuals(layerId) {
    const strip = document.querySelector(`.channel-strip[data-layer-id="${layerId}"]`);
    if (!strip) return;
    const state = perfLayerStates[layerId];
    const trigger = strip.querySelector('.strip-trigger');
    const layer = perfLayers.find(l => l.layer_id === layerId);

    if (state.active) {
        strip.classList.add('active-strip');
        if (trigger) {
            trigger.classList.add('lit');
            if (layer && (layer.trigger_mode === 'toggle' || layer.trigger_mode === 'gate' ||
                          layer.trigger_mode === 'adsr' || layer.trigger_mode === 'one_shot')) {
                // SVG icons handle their own visual state via CSS
            } else {
                trigger.textContent = 'ON';
            }
        }
    } else {
        strip.classList.remove('active-strip');
        if (trigger) {
            trigger.classList.remove('lit');
            if (layer && (layer.trigger_mode === 'toggle' || layer.trigger_mode === 'gate' ||
                          layer.trigger_mode === 'adsr' || layer.trigger_mode === 'one_shot')) {
                // SVG icons handle their own visual state via CSS
            } else {
                trigger.textContent = 'OFF';
            }
        }
    }
    renderLayers();
}

// --- Layer Configuration ---
function perfSetTriggerMode(layerId, mode) {
    const layer = perfLayers.find(l => l.layer_id === layerId);
    if (layer) {
        layer.trigger_mode = mode;
        const state = perfLayerStates[layerId];
        if (state) {
            state.active = (mode === 'always_on');
        }
        // Sync to server LayerStack (resets envelope)
        fetch(`${API}/api/perform/update_layer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ layer_id: layerId, trigger_mode: mode }),
        }).catch(() => _perfSyncWarn());
        renderMixer();
    }
}

function perfSetAdsrPreset(layerId, preset) {
    const layer = perfLayers.find(l => l.layer_id === layerId);
    if (layer) {
        layer.adsr_preset = preset;
        // Sync to server LayerStack (recreates envelope)
        fetch(`${API}/api/perform/update_layer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ layer_id: layerId, adsr_preset: preset }),
        }).catch(() => _perfSyncWarn());
    }
}

function perfSetBlendMode(layerId, mode) {
    const layer = perfLayers.find(l => l.layer_id === layerId);
    if (layer) {
        layer.blend_mode = mode;
        // Sync to server LayerStack
        fetch(`${API}/api/perform/update_layer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ layer_id: layerId, blend_mode: mode }),
        }).catch(() => _perfSyncWarn());
        if (!perfPlaying) schedulePreview();
    }
}

function perfSetChokeGroup(layerId, value) {
    const layer = perfLayers.find(l => l.layer_id === layerId);
    if (layer) {
        layer.choke_group = value === '' ? null : parseInt(value);
        // Sync to server LayerStack
        fetch(`${API}/api/perform/update_layer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ layer_id: layerId, choke_group: layer.choke_group }),
        }).catch(() => _perfSyncWarn());
    }
}

function perfSetOpacity(layerId, value) {
    const state = perfLayerStates[layerId];
    if (state) {
        state.opacity = value;
        perfRecordEvent(layerId, 'opacity', value);
    }
    // Queue opacity change for server ADSR processing
    perfTriggerQueue.push({ layer_id: layerId, event: 'opacity', value: value });
    // Update fader value display
    const strip = document.querySelector(`.channel-strip[data-layer-id="${layerId}"]`);
    if (strip) {
        const valSpan = strip.querySelector('.strip-fader-val');
        if (valSpan) valSpan.textContent = Math.round(value * 100) + '%';
    }
    if (!perfPlaying) schedulePreview();
}

function perfToggleMute(layerId) {
    const state = perfLayerStates[layerId];
    if (state) {
        state.muted = !state.muted;
        if (state.muted) state.active = false;
        renderMixer();
        renderLayers();
        if (!perfPlaying) schedulePreview();
    }
}

function perfToggleSolo(layerId) {
    const state = perfLayerStates[layerId];
    if (state) {
        state.soloed = !state.soloed;
        // If any layer is soloed, mute all non-soloed layers
        const anySoloed = Object.values(perfLayerStates).some(s => s.soloed);
        if (anySoloed) {
            for (const [lid, s] of Object.entries(perfLayerStates)) {
                s.muted = !s.soloed;
            }
        } else {
            for (const [lid, s] of Object.entries(perfLayerStates)) {
                s.muted = false;
            }
        }
        renderMixer();
        renderLayers();
        if (!perfPlaying) schedulePreview();
    }
}

function perfSelectLayerForEdit(layerId) {
    const layer = perfLayers.find(l => l.layer_id === layerId);
    if (!layer) return;

    // Load layer's effects into the chain rack for editing
    chain = (layer.effects || []).map(eff => ({
        id: deviceIdCounter++,
        name: eff.name,
        params: JSON.parse(JSON.stringify(eff.params || {})),
        bypassed: false,
    }));
    selectedLayerId = chain.length > 0 ? chain[chain.length - 1].id : null;

    // Store which perform layer we're editing
    window._perfEditingLayerId = layerId;

    renderChain();
    renderLayers();
    showToast(`Editing L${layerId + 1}: ${layer.name}`, 'info', null, 2000);
}

// Override syncChainToRegion to also sync to perform layer
const _origSyncChainToRegion = syncChainToRegion;
syncChainToRegion = function() {
    _origSyncChainToRegion();

    // If editing a perform layer, sync chain back to server LayerStack
    if (appMode === 'perform' && window._perfEditingLayerId !== undefined) {
        const layer = perfLayers.find(l => l.layer_id === window._perfEditingLayerId);
        if (layer) {
            const effects = chain.map(d => ({
                name: d.name,
                params: JSON.parse(JSON.stringify(d.params)),
            }));
            layer.effects = effects;
            // Sync effects to server LayerStack
            fetch(`${API}/api/perform/update_layer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ layer_id: layer.layer_id, effects }),
            }).catch(() => _perfSyncWarn());
            renderMixer();
        }
    }
};

// --- Drag-to-Reorder Channel Strips ---
let perfDragSourceId = null;

function perfDragStart(event, layerId) {
    perfDragSourceId = layerId;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', layerId);
    event.currentTarget.classList.add('dragging');
}

function perfDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    const target = event.currentTarget;
    if (!target.classList.contains('master-strip')) {
        target.classList.add('drag-over');
    }
}

function perfDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

function perfDrop(event, targetLayerId) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');

    if (perfDragSourceId === null || perfDragSourceId === targetLayerId) return;

    // Find indices in perfLayers array
    const sourceIdx = perfLayers.findIndex(l => l.layer_id === perfDragSourceId);
    const targetIdx = perfLayers.findIndex(l => l.layer_id === targetLayerId);

    if (sourceIdx === -1 || targetIdx === -1) return;

    // Swap positions in array
    const [sourceLayer] = perfLayers.splice(sourceIdx, 1);
    perfLayers.splice(targetIdx, 0, sourceLayer);

    // Reassign z_order values (left = 0 = bottom, right = top)
    perfReorderLayers();
}

function perfDragEnd(event) {
    document.querySelectorAll('.channel-strip').forEach(strip => {
        strip.classList.remove('dragging', 'drag-over');
    });
    perfDragSourceId = null;
}

async function perfReorderLayers() {
    // Assign z_order based on position (index = z_order)
    const updates = [];
    for (let i = 0; i < perfLayers.length; i++) {
        const layer = perfLayers[i];
        if (layer.z_order !== i) {
            layer.z_order = i;
            updates.push(
                fetch(`${API}/api/perform/update_layer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ layer_id: layer.layer_id, z_order: i }),
                }).catch(() => _perfSyncWarn())
            );
        }
    }

    // Wait for all updates to complete
    await Promise.all(updates);

    // Re-render mixer and update preview
    renderMixer();
    renderLayers();
    if (!perfPlaying) {
        schedulePreview();
    }
}

// --- Playback Loop ---
function perfTogglePlay() {
    if (perfPlaying) {
        perfStop();
    } else {
        perfStart();
    }
}

function perfStart() {
    if (!videoLoaded || perfLayers.length === 0) return;
    perfPlaying = true;
    perfLastFrameTime = performance.now();

    const btn = document.getElementById('perf-play-btn');
    if (btn) btn.innerHTML = '&#9646;&#9646; Pause';

    // Disable mode buttons during playback (Norman: prevent mode errors)
    document.querySelectorAll('.mode-btn').forEach(b => {
        if (b.dataset.mode !== 'perform') b.disabled = true;
    });

    perfLoop();
}

function perfStop() {
    perfPlaying = false;
    perfReviewing = false;
    if (perfAnimFrame) {
        cancelAnimationFrame(perfAnimFrame);
        perfAnimFrame = null;
    }

    const btn = document.getElementById('perf-play-btn');
    if (btn) btn.innerHTML = '&#9654; Play';

    // Hide event density timeline if exists
    const canvas = document.getElementById('perf-event-density');
    if (canvas) canvas.dataset.active = 'false';

    // Re-enable mode buttons
    document.querySelectorAll('.mode-btn').forEach(b => b.disabled = false);

    // Auto-commit automation lanes if recording was armed
    if (autoRecording && Object.keys(autoRecordLanes).length > 0) {
        autoCommitLanes();
        autoRecording = false;
        const autoBtn = document.getElementById('perf-auto-btn');
        if (autoBtn) autoBtn.classList.remove('auto-armed');
    }
}

async function perfLoop() {
    if (!perfPlaying) return;

    const now = performance.now();
    const elapsed = now - perfLastFrameTime;
    const frameInterval = 1000 / PERF_FPS;

    if (elapsed >= frameInterval) {
        perfLastFrameTime = now - (elapsed % frameInterval);
        perfFrameIndex++;

        // Loop video
        if (perfFrameIndex >= totalFrames) {
            if (perfLooping) {
                perfFrameIndex = 0;
            } else {
                perfStop();
                return;
            }
        }

        // Drain trigger queue and send with this frame
        let events = [];

        if (perfReviewing) {
            // Review mode: read events from recorded frame map
            if (perfReviewFrameMap[perfFrameIndex]) {
                for (const evt of perfReviewFrameMap[perfFrameIndex]) {
                    if (evt.param === 'active') {
                        // Convert active parameter to on/off event
                        events.push({
                            layer_id: evt.layer_id,
                            event: evt.value > 0 ? 'on' : 'off',
                        });
                    } else if (evt.param === 'opacity') {
                        events.push({
                            layer_id: evt.layer_id,
                            event: 'opacity',
                            value: evt.value,
                        });
                    }
                }
            }
            // Update event density timeline position
            perfUpdateEventDensityPosition();
        } else {
            // Live mode: drain trigger queue
            events = perfTriggerQueue.splice(0);

            // Add muted layers as opacity=0 events (server needs to know)
            for (const l of perfLayers) {
                const s = perfLayerStates[l.layer_id];
                if (s && s.muted && l._active) {
                    events.push({ layer_id: l.layer_id, event: 'opacity', value: 0.0 });
                }
            }
        }

        // Inject per-layer LFO opacity modulation
        const lfoDt = 1 / PERF_FPS;
        for (const l of perfLayers) {
            const lfoOpacity = perfComputeLayerLfoOpacity(l.layer_id, lfoDt);
            if (lfoOpacity !== null) {
                const s = perfLayerStates[l.layer_id];
                if (s && !s.muted) {
                    // LFO modulates the base opacity (fader value * LFO)
                    const baseOpacity = s.opacity ?? l.opacity;
                    events.push({ layer_id: l.layer_id, event: 'opacity', value: baseOpacity * lfoOpacity });
                }
            }
        }

        try {
            const res = await fetch(`${API}/api/perform/frame`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    frame_number: perfFrameIndex,
                    trigger_events: events.length > 0 ? events : undefined,
                }),
            });
            const data = await res.json();
            if (data.preview) {
                showPreview(data.preview);
            }
            // Tier 3: Sync UI with server envelope states
            if (data.layer_states) {
                perfSyncWithServer(data.layer_states);
            }
        } catch (err) {
            // Server disconnect — auto-pause (Norman: error prevention)
            if (_serverDown) {
                perfStop();
                showToast('Playback paused: server disconnected', 'error');
                return;
            }
        }

        perfUpdateTransport();
    }

    perfAnimFrame = requestAnimationFrame(perfLoop);
}

function perfSyncWithServer(serverStates) {
    /**
     * Sync client UI with server's computed ADSR envelope states.
     * Server is the source of truth for envelope phase + computed opacity.
     * Client keeps mute/solo state locally.
     */
    for (const ss of serverStates) {
        const state = perfLayerStates[ss.layer_id];
        if (!state) continue;

        // Update active state from server (ADSR may have auto-released)
        state.active = ss.active;
        state.serverOpacity = ss.current_opacity;
        state.envelopePhase = ss.phase;
        state.envelopeLevel = ss.envelope_level;

        // Update strip visuals with envelope info
        const strip = document.querySelector(`.channel-strip[data-layer-id="${ss.layer_id}"]`);
        if (!strip) continue;

        // Update active indicator
        if (ss.active || ss.current_opacity > 0.001) {
            strip.classList.add('active-strip');
            strip.querySelector('.strip-trigger')?.classList.add('lit');
        } else {
            strip.classList.remove('active-strip');
            strip.querySelector('.strip-trigger')?.classList.remove('lit');
        }

        // Update envelope phase indicator on ADSR ring (if present)
        const ring = strip.querySelector('.adsr-ring');
        if (ring) {
            ring.dataset.phase = ss.phase;
            ring.style.setProperty('--env-level', ss.envelope_level);
        }

        // Update fader readout with server-computed opacity
        const faderVal = strip.querySelector('.strip-fader-val');
        if (faderVal) {
            faderVal.textContent = Math.round(ss.current_opacity * 100) + '%';
        }
    }
}

// --- Transport Controls ---
function perfUpdateTransport() {
    const timeEl = document.getElementById('perf-time');
    const frameEl = document.getElementById('perf-frame');
    const eventEl = document.getElementById('perf-event-count');
    const scrubber = document.querySelector('#perf-scrubber input');

    if (timeEl) timeEl.textContent = formatTime(perfFrameIndex / 30);
    if (frameEl) frameEl.textContent = `F:${perfFrameIndex}`;
    if (eventEl) eventEl.textContent = `${perfEventCount} events`;
    if (scrubber) scrubber.value = perfFrameIndex;

    // Update HUD overlay
    const hudRec = document.getElementById('perf-hud-rec');
    const hudTime = document.getElementById('perf-hud-time');
    const hudEvents = document.getElementById('perf-hud-events');
    if (hudRec) hudRec.textContent = perfReviewing ? '[REVIEW]' : (perfRecording ? '[REC]' : (autoRecording ? '[AUTO]' : '[BUF]'));
    if (hudTime) hudTime.textContent = formatTime(perfFrameIndex / 30);
    if (hudEvents) hudEvents.textContent = `${perfEventCount} ev`;
    updateCaptureBufferIndicator();
}

function perfScrub(value) {
    if (perfRecording) { showToast('Cannot scrub while recording', 'info', null, 1500); return; }
    perfFrameIndex = parseInt(value);
    perfUpdateTransport();
    if (!perfPlaying) schedulePreview();
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${m}:${String(s).padStart(2, '0')}:${String(ms).padStart(2, '0')}`;
}

// --- Recording ---
function perfToggleRecord() {
    perfRecording = !perfRecording;
    const btn = document.getElementById('perf-rec-btn');

    const scrubber = document.querySelector('#perf-scrubber input');
    if (perfRecording) {
        // Clear buffer for fresh take
        perfSession = { type: 'performance', lanes: [] };
        perfEventCount = 0;
        if (btn) btn.classList.add('recording');
        if (scrubber) { scrubber.disabled = true; scrubber.style.opacity = '0.3'; }
        showToast('Recording armed — buffer cleared', 'info', null, 2000);
    } else {
        if (btn) btn.classList.remove('recording');
        if (scrubber) { scrubber.disabled = false; scrubber.style.opacity = '1'; }
        if (perfEventCount > 0) {
            showToast(`Recording stopped: ${perfEventCount} events`, 'success', {
                label: 'Save',
                fn: 'perfSaveSession',
            }, 10000);
            showToast('Review your performance', 'info', {
                label: 'Review',
                fn: 'perfReviewStart',
            }, 10000);
            showToast('Bake triggers into timeline automation', 'info', {
                label: 'Bake to Timeline',
                fn: 'perfBakeToTimeline',
            }, 10000);
            showToast('Or discard this take', 'info', {
                label: 'Discard',
                fn: 'perfDiscardSession',
            }, 10000);
        } else {
            showToast('Recording stopped (no events)', 'info', null, 2000);
        }
    }
    perfUpdateTransport();
}

function perfRecordEvent(layerId, param, value) {
    if (perfEventCount >= PERF_MAX_EVENTS) {
        if (perfEventCount === PERF_MAX_EVENTS) {
            showToast(`Buffer full (${PERF_MAX_EVENTS} events)`, 'error');
        }
        return;
    }

    // Always auto-buffer (CLI pattern)
    // Find or create lane in perfSession
    let lane = perfSession.lanes.find(l =>
        l.layer_id === layerId && l.param === param
    );
    if (!lane) {
        lane = {
            type: 'midi_event',
            effect_idx: layerId,
            layer_id: layerId,
            param: param,
            keyframes: [],
            curve: 'step',
        };
        perfSession.lanes.push(lane);
    }
    lane.keyframes.push([perfFrameIndex, value]);
    perfEventCount++;

    // Show warning at 90% capacity
    if (perfEventCount === Math.floor(PERF_MAX_EVENTS * 0.9)) {
        showToast(`Buffer 90% full (${perfEventCount}/${PERF_MAX_EVENTS})`, 'error');
    }

    perfUpdateTransport();
}

// --- Panic ---
function perfPanic() {
    // Reset all layer states (client)
    for (const l of perfLayers) {
        const state = perfLayerStates[l.layer_id];
        if (state) {
            state.active = l.trigger_mode === 'always_on';
            state.muted = false;
            state.soloed = false;
        }
        // Queue panic for each layer on server
        perfTriggerQueue.push({ layer_id: l.layer_id, event: 'panic' });
        // Reset LFO phase (keep settings, just restart)
        if (perfLayerLfos[l.layer_id]) {
            perfLayerLfos[l.layer_id].phase = 0;
        }
    }
    renderMixer();
    showToast('ALL LAYERS RESET', 'info', null, 1000);
    if (!perfPlaying) schedulePreview();
}

// --- Master Bus Effects ---
function perfToggleMasterExpand() {
    perfMasterExpanded = !perfMasterExpanded;
    renderMixer();
}

function perfAddMasterEffect(effectName) {
    if (!effectName) return;
    if (perfMasterEffects.length >= 10) {
        showToast('Max 10 master bus effects', 'error');
        return;
    }
    perfMasterEffects.push({ name: effectName, params: {} });
    perfSyncMasterEffects();
    renderMixer();
}

function perfRemoveMasterEffect(idx) {
    perfMasterEffects.splice(idx, 1);
    perfSyncMasterEffects();
    renderMixer();
}

function perfSyncMasterEffects() {
    fetch(`${API}/api/perform/master`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ effects: perfMasterEffects }),
    }).catch(() => showToast('Failed to sync master effects', 'error'));
    if (!perfPlaying) schedulePreview();
}

// --- Per-Layer Opacity LFO ---

function perfToggleLayerLfo(layerId) {
    if (!perfLayerLfos[layerId]) {
        perfLayerLfos[layerId] = { enabled: true, waveform: 'sine', rate: 1, depth: 1, phase: 0, _showCfg: false };
    } else {
        perfLayerLfos[layerId].enabled = !perfLayerLfos[layerId].enabled;
    }
    renderMixer();
}

function perfShowLfoCfg(layerId) {
    if (!perfLayerLfos[layerId]) {
        perfLayerLfos[layerId] = { enabled: false, waveform: 'sine', rate: 1, depth: 1, phase: 0, _showCfg: true };
    } else {
        perfLayerLfos[layerId]._showCfg = !perfLayerLfos[layerId]._showCfg;
    }
    renderMixer();
}

function perfSetLfoParam(layerId, param, value) {
    if (!perfLayerLfos[layerId]) return;
    perfLayerLfos[layerId][param] = value;
}

function perfComputeLayerLfoOpacity(layerId, dt) {
    const lfo = perfLayerLfos[layerId];
    if (!lfo || !lfo.enabled) return null;

    // Advance phase
    lfo.phase = (lfo.phase + dt * lfo.rate) % 1.0;

    // Compute LFO value (0..1) using the existing lfoWaveform function
    const raw = lfoWaveform(lfo.phase, lfo.waveform);

    // Apply depth: interpolate between 1.0 (no mod) and raw
    const modulated = 1.0 - lfo.depth * (1.0 - raw);
    return Math.max(0, Math.min(1, modulated));
}

// --- Keyboard Perform Mode ---
function toggleKeyboardPerformMode(forceState) {
    keyboardPerformMode = forceState !== undefined ? forceState : !keyboardPerformMode;
    const app = document.getElementById('app');
    const hud = document.getElementById('perf-hud-keyboard');
    const overlay = document.getElementById('keyboard-hint-overlay');

    if (keyboardPerformMode) {
        if (app) app.classList.add('keyboard-perform-active');
        if (hud) hud.style.display = '';
        showToast('Keyboard Perform: ON (Q/W/E/R = L1-L4, A/S/D/F = L5-L8, Esc = exit)', 'info', null, 3000);
    } else {
        if (app) app.classList.remove('keyboard-perform-active');
        if (hud) hud.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
    }
}

function toggleKeyHintOverlay() {
    const overlay = document.getElementById('keyboard-hint-overlay');
    if (!overlay) return;
    overlay.style.display = overlay.style.display === 'none' ? '' : 'none';
}

// --- Automation Recording ---
function toggleAutoRecording() {
    autoRecording = !autoRecording;
    const btn = document.getElementById('perf-auto-btn');

    if (autoRecording) {
        if (btn) btn.classList.add('auto-armed');
        autoRecordLanes = {};
        showToast('Automation armed — move knobs during playback to record', 'info', null, 3000);
    } else {
        if (btn) btn.classList.remove('auto-armed');
        autoCommitLanes();
    }
}

function autoRecordParam(deviceId, paramName, value, min, max) {
    const key = `${deviceId}_${paramName}`;
    if (!autoRecordLanes[key]) {
        autoRecordLanes[key] = { deviceId, paramName, min, max, keyframes: [] };
    }
    const lane = autoRecordLanes[key];
    // Thin: skip if frame delta < 3 (10fps at 30fps playback) or value change < 0.01
    const last = lane.keyframes[lane.keyframes.length - 1];
    if (last) {
        const frameDelta = perfFrameIndex - last.frame;
        const range = max - min || 1;
        const valueDelta = Math.abs(value - last.value) / range;
        if (frameDelta < 3 && valueDelta < 0.01) return;
    }
    // Normalize to 0-1
    const normValue = min === max ? 0.5 : (value - min) / (max - min);
    lane.keyframes.push({ frame: perfFrameIndex, value: Math.max(0, Math.min(1, normValue)) });

    // Visual: mark knob as recording
    const knobEl = document.querySelector(`.knob[data-device="${deviceId}"][data-param="${paramName}"]`);
    if (knobEl) {
        const container = knobEl.closest('.knob-container');
        if (container && !container.classList.contains('auto-recording')) {
            container.classList.add('auto-recording');
        }
    }
}

function autoCommitLanes() {
    const keys = Object.keys(autoRecordLanes);
    if (keys.length === 0) {
        showToast('No automation recorded', 'info', null, 2000);
        return;
    }

    if (!window.timelineEditor) {
        showToast('Timeline not initialized — cannot commit automation', 'error');
        return;
    }

    const te = window.timelineEditor;
    const region = te.findRegion(te.selectedRegionId) || (te.tracks[0]?.regions?.[0]);
    if (!region) {
        showToast('No timeline region — create a region first', 'error');
        return;
    }

    let lanesCreated = 0;
    let totalKeyframes = 0;
    for (const key of keys) {
        const data = autoRecordLanes[key];
        if (data.keyframes.length === 0) continue;

        // Find effect index in region chain
        const device = chain.find(d => d.id === data.deviceId);
        if (!device) continue;
        const effectIdx = chain.indexOf(device);
        if (effectIdx < 0) continue;

        const lane = te.addAutomationLane(region.id, effectIdx, data.paramName);
        for (const kf of data.keyframes) {
            lane.keyframes.push({
                frame: region.startFrame + kf.frame,
                value: kf.value,
                curve: 'linear',
            });
        }
        lane.keyframes.sort((a, b) => a.frame - b.frame);
        lanesCreated++;
        totalKeyframes += data.keyframes.length;
    }

    // Clear recording CSS
    document.querySelectorAll('.knob-container.auto-recording').forEach(el => {
        el.classList.remove('auto-recording');
    });

    autoRecordLanes = {};
    te.draw();
    showToast(`Automation recorded: ${lanesCreated} param${lanesCreated !== 1 ? 's' : ''}, ${totalKeyframes} keyframes`, 'success');
}

// --- Retroactive Capture Buffer ---
function captureBufferPush(layerId, param, value) {
    if (captureBuffer.length >= CAPTURE_BUFFER_MAX_EVENTS) {
        captureBuffer.shift();
    }
    captureBuffer.push({
        frame: perfFrameIndex,
        layerId,
        param,
        value,
        timestamp: performance.now(),
    });
    // Evict events older than buffer window
    const cutoffFrame = perfFrameIndex - (CAPTURE_BUFFER_SECONDS * PERF_FPS);
    while (captureBuffer.length > 0 && captureBuffer[0].frame < cutoffFrame) {
        captureBuffer.shift();
    }
}

function capturePerformBuffer() {
    if (captureBuffer.length === 0) {
        showToast('Nothing to capture — perform first', 'info', null, 2000);
        return;
    }

    // Group events by layerId + param → create perfSession-compatible lanes
    const laneMap = {};
    for (const ev of captureBuffer) {
        const key = `${ev.layerId}_${ev.param}`;
        if (!laneMap[key]) {
            laneMap[key] = {
                type: 'midi_event',
                effect_idx: ev.layerId,
                layer_id: ev.layerId,
                param: ev.param,
                keyframes: [],
                curve: 'step',
            };
        }
        laneMap[key].keyframes.push([ev.frame, ev.value]);
    }

    const lanes = Object.values(laneMap);
    const eventCount = captureBuffer.length;
    const durationSec = captureBuffer.length > 0
        ? ((captureBuffer[captureBuffer.length - 1].frame - captureBuffer[0].frame) / PERF_FPS).toFixed(1)
        : 0;

    // Merge into perfSession for review/bake/save
    perfSession = { type: 'performance', lanes };
    perfEventCount = eventCount;
    captureBuffer = [];

    // Update buffer indicator
    updateCaptureBufferIndicator();

    showToast(`Captured ${eventCount} events (${durationSec}s)`, 'success', null, 3000);
    showToast('Review your captured performance', 'info', {
        label: 'Review',
        fn: 'perfReviewStart',
    }, 10000);
    showToast('Bake captures into timeline automation', 'info', {
        label: 'Bake to Timeline',
        fn: 'perfBakeToTimeline',
    }, 10000);
    showToast('Or discard this capture', 'info', {
        label: 'Discard',
        fn: 'perfDiscardSession',
    }, 10000);

    perfUpdateTransport();
}

function updateCaptureBufferIndicator() {
    const el = document.getElementById('perf-hud-buffer');
    if (!el) return;
    if (captureBuffer.length === 0) {
        el.textContent = '';
        return;
    }
    const durationSec = Math.floor((captureBuffer[captureBuffer.length - 1].frame - captureBuffer[0].frame) / PERF_FPS);
    el.textContent = `Buf: ${durationSec}s`;
}

// --- Save & Render ---
async function perfSaveSession() {
    if (perfEventCount === 0) {
        showToast('No performance data to save', 'info');
        return;
    }

    const layersConfig = perfLayers.map(l => ({
        ...l,
        video_path: '', // Server fills this in
    }));

    try {
        const res = await fetch(`${API}/api/perform/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                layers_config: layersConfig,
                events: perfSession,
                duration_frames: perfFrameIndex,
            }),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            showToast(`Performance saved: ${data.name}`, 'success', {
                label: 'Reveal in Finder',
                fn: `function(){revealInFinder('${(data.path || '').replace(/'/g, "\\'")}')}`,
            }, 6000);
        }
    } catch (err) {
        showErrorToast(`Save failed: ${err.message}`);
    }
}

async function perfRender() {
    if (perfEventCount === 0) {
        showToast('No performance data to render', 'info');
        return;
    }

    const btn = document.querySelector('.transport-right .primary');
    const origText = btn ? btn.textContent : '';
    if (btn) { btn.textContent = 'Rendering...'; btn.disabled = true; }
    showLoading('Rendering performance...');

    try {
        const res = await fetch(`${API}/api/perform/render`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                layers_config: perfLayers,
                events: perfSession,
                duration_frames: perfFrameIndex,
                fps: 30,
                crf: 18,
            }),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            const fullPath = data.dir ? `${data.dir}/${data.path}` : data.path;
            showToast(`Rendered: ${data.size_mb}MB @ ${data.fps}fps`, 'success', {
                label: 'Reveal in Finder',
                fn: `function(){revealInFinder('${(fullPath || '').replace(/'/g, "\\'")}')}`,
            }, 8000);
        } else {
            showErrorToast(`Render failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        showErrorToast(`Render error: ${err.message}`);
    } finally {
        hideLoading();
        if (btn) { btn.textContent = origText; btn.disabled = false; }
    }
}

// --- Loop Toggle ---
let perfLooping = true; // Default: loop on

function perfToggleLoop() {
    perfLooping = !perfLooping;
    const btn = document.getElementById('perf-loop-btn');
    if (btn) {
        btn.style.background = perfLooping ? 'var(--accent-secondary)' : '';
        btn.style.color = perfLooping ? '#000' : '';
    }
    showToast(perfLooping ? 'Loop: ON' : 'Loop: OFF', 'info', null, 1500);
}

// --- Bake Perform to Timeline ---
function perfBakeToTimeline() {
    if (perfEventCount === 0) {
        showToast('No performance data to bake', 'info');
        return;
    }
    if (!window.timelineEditor) {
        showToast('Timeline not initialized', 'error');
        return;
    }

    const te = window.timelineEditor;
    // Find the first region (or selected region) to attach automation to
    const region = te.findRegion(te.selectedRegionId) || (te.tracks[0]?.regions?.[0]);
    if (!region) {
        showToast('No timeline region to bake into — create a region first', 'error');
        return;
    }

    let lanesCreated = 0;
    for (const perfLane of perfSession.lanes) {
        // Map perform layer_id to effect index in the region's chain
        const effectIdx = perfLane.effect_idx;
        if (effectIdx >= (region.effects || []).length) continue;

        // Create automation lane
        const paramName = perfLane.param || 'mix';
        const lane = te.addAutomationLane(region.id, effectIdx, paramName);

        // Convert perform keyframes (absolute frame, value) to automation breakpoints
        for (const [frame, value] of perfLane.keyframes) {
            // Normalize value to 0-1 range (perform values may vary)
            const normValue = typeof value === 'number' ? Math.max(0, Math.min(1, value)) : (value ? 1 : 0);
            lane.keyframes.push({
                frame: region.startFrame + frame,
                value: normValue,
                curve: perfLane.curve || 'step',
            });
        }
        lane.keyframes.sort((a, b) => a.frame - b.frame);
        lanesCreated++;
    }

    te.draw();
    showToast(`Baked ${lanesCreated} perform lane${lanesCreated !== 1 ? 's' : ''} to timeline`, 'success');
}

// --- Discard Session ---
function perfDiscardSession() {
    perfSession = { type: 'performance', lanes: [] };
    perfEventCount = 0;
    perfUpdateTransport();
    showToast('Performance discarded', 'info', null, 2000);
}

// --- Review Mode ---
function perfReviewStart() {
    if (perfEventCount === 0) {
        showToast('No performance to review', 'info');
        return;
    }

    // Build frame->events map from perfSession
    perfReviewFrameMap = {};
    for (const lane of perfSession.lanes) {
        const layerId = lane.layer_id;
        const param = lane.param;
        for (const [frame, value] of lane.keyframes) {
            if (!perfReviewFrameMap[frame]) {
                perfReviewFrameMap[frame] = [];
            }
            perfReviewFrameMap[frame].push({ layer_id: layerId, param, value });
        }
    }

    // Reset to start — clear all layer states so review is clean
    perfFrameIndex = 0;
    perfReviewing = true;
    perfPlaying = true;
    for (const l of perfLayers) {
        const state = perfLayerStates[l.layer_id];
        if (state) {
            state.active = l.trigger_mode === 'always_on';
        }
    }
    // Reset server envelopes too
    perfTriggerQueue = perfLayers.map(l => ({ layer_id: l.layer_id, event: 'panic' }));

    // Render event density timeline
    perfRenderEventDensity();

    // Start playback
    perfUpdateTransport();
    showToast('Review playback started', 'info', null, 2000);
    perfLoop();
}

function perfReviewStop() {
    perfReviewing = false;
    perfPlaying = false;
    if (perfAnimFrame) {
        cancelAnimationFrame(perfAnimFrame);
        perfAnimFrame = null;
    }
    showToast('Review stopped', 'info', null, 1500);
}

function perfRenderEventDensity() {
    // Create or get canvas for event density timeline
    let canvas = document.getElementById('perf-event-density');
    if (!canvas) {
        // Insert canvas after scrubber
        const scrubber = document.getElementById('perf-scrubber');
        if (!scrubber) return;

        canvas = document.createElement('canvas');
        canvas.id = 'perf-event-density';
        canvas.width = scrubber.offsetWidth || 600;
        canvas.height = 20;
        scrubber.parentNode.insertBefore(canvas, scrubber.nextSibling);
    }

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, width, height);

    // Compute event density per time bucket
    const buckets = new Array(width).fill(0);
    const framesPerPixel = Math.max(1, totalFrames / width);

    for (const frame in perfReviewFrameMap) {
        const pixelX = Math.floor(parseInt(frame) / framesPerPixel);
        if (pixelX >= 0 && pixelX < width) {
            buckets[pixelX] += perfReviewFrameMap[frame].length;
        }
    }

    const maxDensity = Math.max(...buckets, 1);

    // Draw density bars
    for (let x = 0; x < width; x++) {
        const density = buckets[x];
        if (density > 0) {
            const intensity = density / maxDensity;
            const alpha = 0.3 + intensity * 0.7;
            ctx.fillStyle = `rgba(255, 107, 53, ${alpha})`;
            const barHeight = Math.max(2, height * intensity);
            ctx.fillRect(x, height - barHeight, 1, barHeight);
        }
    }

    // Update playback position in timeline during review
    canvas.dataset.active = 'true';
}

function perfUpdateEventDensityPosition() {
    const canvas = document.getElementById('perf-event-density');
    if (!canvas || canvas.dataset.active !== 'true') return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Redraw base timeline
    perfRenderEventDensity();

    // Draw playback position line
    if (totalFrames > 0) {
        const x = Math.floor((perfFrameIndex / totalFrames) * width);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
}

// --- beforeunload: warn about unsaved performance data ---
window.addEventListener('beforeunload', e => {
    if ((appMode === 'perform' || performToggleActive) && perfEventCount > 0) {
        e.preventDefault();
        e.returnValue = 'You have unsaved performance data. Leave?';
    }
});

// ============ COLOR SUITE: HISTOGRAM, CURVES EDITOR, HSL/COLOR BALANCE ============

// --- Histogram Panel ---
function toggleHistogramPanel() {
    const panel = document.getElementById('histogram-panel');
    panel.classList.toggle('collapsed');
    if (!panel.classList.contains('collapsed')) {
        fetchHistogram();
    }
}

let _histogramPending = false;
async function fetchHistogram() {
    if (!videoLoaded || _histogramPending) return;
    _histogramPending = true;
    try {
        const res = await fetch(`${API}/api/histogram`, { method: 'POST' });
        if (!res.ok) return;
        const data = await res.json();
        drawHistogram(data);
    } catch (e) {
        // Silent fail — histogram is non-critical
    } finally {
        _histogramPending = false;
    }
}

function drawHistogram(data) {
    const canvas = document.getElementById('histogram-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;   // 256
    const h = canvas.height;  // 100

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0a0a0c';
    ctx.fillRect(0, 0, w, h);

    // Find max across all channels for Y-axis scaling
    const allMax = Math.max(
        Math.max(...data.r),
        Math.max(...data.g),
        Math.max(...data.b),
        Math.max(...data.luma)
    );
    if (allMax === 0) return;

    const channels = [
        { bins: data.luma, color: 'rgba(255,255,255,0.2)' },
        { bins: data.b, color: 'rgba(0,128,255,0.3)' },
        { bins: data.g, color: 'rgba(0,255,0,0.3)' },
        { bins: data.r, color: 'rgba(255,0,0,0.3)' },
    ];

    for (const ch of channels) {
        ctx.beginPath();
        ctx.moveTo(0, h);
        for (let i = 0; i < 256; i++) {
            const barH = (ch.bins[i] / allMax) * h;
            ctx.lineTo(i, h - barH);
        }
        ctx.lineTo(255, h);
        ctx.closePath();
        ctx.fillStyle = ch.color;
        ctx.fill();
    }
}

// Hook into preview updates to refresh histogram
const _origPreviewChain = previewChain;
previewChain = async function() {
    await _origPreviewChain();
    // After preview updates, refresh histogram if panel is open
    const panel = document.getElementById('histogram-panel');
    if (panel && !panel.classList.contains('collapsed')) {
        fetchHistogram();
    }
};

// --- Curves Canvas Editor ---
// Tracks per-device curves state: { [deviceId]: { channel, points: {master, r, g, b} } }
const curvesState = {};

function getCurvesKey(deviceId) {
    if (!curvesState[deviceId]) {
        curvesState[deviceId] = {
            channel: 'master',
            points: {
                master: [[0, 0], [255, 255]],
                r: [[0, 0], [255, 255]],
                g: [[0, 0], [255, 255]],
                b: [[0, 0], [255, 255]],
            },
            dragging: -1,
        };
    }
    return curvesState[deviceId];
}

function renderCurvesEditor(deviceId, device) {
    const state = getCurvesKey(deviceId);
    // Initialize from device params if they exist
    if (device.params.points && device.params.points.length >= 2) {
        const ch = device.params.channel || 'master';
        state.points[ch] = JSON.parse(JSON.stringify(device.params.points));
    }

    return `
        <div class="curves-editor" data-curves-device="${deviceId}">
            <div class="curves-channel-tabs">
                <button class="curves-channel-tab ${state.channel === 'master' ? 'active' : ''}" data-ch="master" data-device="${deviceId}" onclick="curvesSetChannel(${deviceId},'master')">M</button>
                <button class="curves-channel-tab ${state.channel === 'r' ? 'active' : ''}" data-ch="r" data-device="${deviceId}" onclick="curvesSetChannel(${deviceId},'r')">R</button>
                <button class="curves-channel-tab ${state.channel === 'g' ? 'active' : ''}" data-ch="g" data-device="${deviceId}" onclick="curvesSetChannel(${deviceId},'g')">G</button>
                <button class="curves-channel-tab ${state.channel === 'b' ? 'active' : ''}" data-ch="b" data-device="${deviceId}" onclick="curvesSetChannel(${deviceId},'b')">B</button>
            </div>
            <canvas class="curves-canvas" width="200" height="200" data-device="${deviceId}"></canvas>
            <div class="curves-hint">click = add point | drag = move | right-click = delete</div>
        </div>`;
}

function curvesSetChannel(deviceId, ch) {
    const state = getCurvesKey(deviceId);
    // Save current points to device params before switching
    const device = chain.find(d => d.id === deviceId);
    if (device) {
        device.params.channel = ch;
        device.params.points = state.points[ch];
    }
    state.channel = ch;
    renderChain();
}

function setupCurvesCanvas(canvas) {
    const deviceId = parseInt(canvas.dataset.device);
    const state = getCurvesKey(deviceId);

    drawCurves(canvas, state);

    canvas.addEventListener('mousedown', e => {
        e.preventDefault();
        const rect = canvas.getBoundingClientRect();
        const x = Math.round((e.offsetX / rect.width) * 255);
        const y = Math.round(255 - (e.offsetY / rect.height) * 255);

        const pts = state.points[state.channel];

        // Right-click: delete nearest point (but not endpoints)
        if (e.button === 2) {
            e.preventDefault();
            const idx = findNearestPoint(pts, x, y);
            if (idx > 0 && idx < pts.length - 1) {
                pts.splice(idx, 1);
                curvesSync(deviceId, state);
                drawCurves(canvas, state);
            }
            return;
        }

        // Left-click: check if near existing point to drag, or add new point
        const idx = findNearestPoint(pts, x, y);
        const dist = Math.sqrt((pts[idx][0] - x) ** 2 + (pts[idx][1] - y) ** 2);
        if (dist < 15) {
            // Drag existing point (but not fixed endpoints if they're at 0 or 255)
            state.dragging = idx;
        } else {
            // Add new point
            pts.push([x, y]);
            pts.sort((a, b) => a[0] - b[0]);
            state.dragging = pts.findIndex(p => p[0] === x && p[1] === y);
            curvesSync(deviceId, state);
            drawCurves(canvas, state);
        }
    });

    canvas.addEventListener('mousemove', e => {
        if (state.dragging < 0) return;
        const rect = canvas.getBoundingClientRect();
        const x = Math.round(Math.max(0, Math.min(255, (e.offsetX / rect.width) * 255)));
        const y = Math.round(Math.max(0, Math.min(255, 255 - (e.offsetY / rect.height) * 255)));

        const pts = state.points[state.channel];
        const idx = state.dragging;

        // Endpoints are locked to x=0 and x=255
        if (idx === 0) {
            pts[idx] = [0, y];
        } else if (idx === pts.length - 1) {
            pts[idx] = [255, y];
        } else {
            // Constrain between neighbors
            const minX = pts[idx - 1][0] + 1;
            const maxX = pts[idx + 1][0] - 1;
            pts[idx] = [Math.max(minX, Math.min(maxX, x)), y];
        }
        drawCurves(canvas, state);
    });

    const endDrag = () => {
        if (state.dragging >= 0) {
            state.dragging = -1;
            curvesSync(deviceId, state);
        }
    };
    canvas.addEventListener('mouseup', endDrag);
    canvas.addEventListener('mouseleave', endDrag);

    canvas.addEventListener('contextmenu', e => e.preventDefault());
}

function findNearestPoint(pts, x, y) {
    let best = 0, bestDist = Infinity;
    for (let i = 0; i < pts.length; i++) {
        const d = Math.sqrt((pts[i][0] - x) ** 2 + (pts[i][1] - y) ** 2);
        if (d < bestDist) { bestDist = d; best = i; }
    }
    return best;
}

function curvesSync(deviceId, state) {
    const device = chain.find(d => d.id === deviceId);
    if (device) {
        device.params.points = state.points[state.channel];
        device.params.channel = state.channel;
        schedulePreview();
    }
}

function drawCurves(canvas, state) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const pts = state.points[state.channel];

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0a0a0c';
    ctx.fillRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = '#1a1a1e';
    ctx.lineWidth = 1;
    for (let i = 1; i < 4; i++) {
        const p = (i / 4) * w;
        ctx.beginPath();
        ctx.moveTo(p, 0); ctx.lineTo(p, h);
        ctx.moveTo(0, p); ctx.lineTo(w, p);
        ctx.stroke();
    }

    // Diagonal baseline (identity)
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h);
    ctx.lineTo(w, 0);
    ctx.stroke();

    // Draw the curve
    const chColors = { master: '#fff', r: '#ff6666', g: '#66ff66', b: '#6688ff' };
    ctx.strokeStyle = chColors[state.channel] || '#fff';
    ctx.lineWidth = 2;
    ctx.beginPath();

    // Generate smooth curve using monotone interpolation (linear between points for simplicity)
    for (let px = 0; px < w; px++) {
        const inVal = (px / w) * 255;
        const outVal = interpolateCurve(pts, inVal);
        const sy = h - (outVal / 255) * h;
        if (px === 0) ctx.moveTo(px, sy);
        else ctx.lineTo(px, sy);
    }
    ctx.stroke();

    // Draw control points
    for (let i = 0; i < pts.length; i++) {
        const sx = (pts[i][0] / 255) * w;
        const sy = h - (pts[i][1] / 255) * h;
        ctx.beginPath();
        ctx.arc(sx, sy, i === state.dragging ? 6 : 4, 0, Math.PI * 2);
        ctx.fillStyle = i === state.dragging ? '#fff' : (chColors[state.channel] || '#fff');
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.stroke();
    }
}

function interpolateCurve(pts, x) {
    if (pts.length < 2) return x;
    // Find surrounding points
    if (x <= pts[0][0]) return pts[0][1];
    if (x >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
    for (let i = 0; i < pts.length - 1; i++) {
        if (x >= pts[i][0] && x <= pts[i + 1][0]) {
            const t = (x - pts[i][0]) / (pts[i + 1][0] - pts[i][0]);
            return pts[i][1] + t * (pts[i + 1][1] - pts[i][1]);
        }
    }
    return x;
}

// --- HSL Color Strip ---
function renderHslStrip(deviceId, targetHue) {
    const hueRanges = {
        all: null,
        reds: [350, 30],
        oranges: [15, 45],
        yellows: [45, 75],
        greens: [75, 165],
        cyans: [165, 195],
        blues: [195, 255],
        magentas: [255, 350],
    };

    if (targetHue === 'all') {
        // Full rainbow gradient
        return `<div class="hsl-color-strip" style="background:linear-gradient(to right,
            hsl(0,100%,50%), hsl(60,100%,50%), hsl(120,100%,50%),
            hsl(180,100%,50%), hsl(240,100%,50%), hsl(300,100%,50%),
            hsl(360,100%,50%));opacity:0.6"></div>`;
    }

    const range = hueRanges[targetHue];
    if (!range) return '';

    // Build gradient showing affected hue range
    const start = range[0];
    const end = range[1];
    return `<div class="hsl-color-strip" style="background:linear-gradient(to right,
        hsl(${start},100%,50%), hsl(${(start + end) / 2},100%,50%), hsl(${end},100%,50%));
        opacity:0.6"></div>`;
}

// --- Color Balance Grouped Rendering ---
function renderColorBalanceGrouped(deviceId, device, def) {
    const groups = [
        { label: 'Shadows', params: ['shadows_r', 'shadows_g', 'shadows_b'] },
        { label: 'Midtones', params: ['midtones_r', 'midtones_g', 'midtones_b'] },
        { label: 'Highlights', params: ['highlights_r', 'highlights_g', 'highlights_b'] },
    ];

    let html = '';
    for (const group of groups) {
        html += `<div class="cb-section"><div class="cb-section-label">${group.label}</div><div class="cb-sliders">`;
        for (const pName of group.params) {
            const spec = def.params[pName];
            if (!spec) continue;
            const value = device.params[pName] ?? spec.default;
            const ctrlSpec = controlMap?.effects?.[device.name]?.params?.[pName];
            html += createControl(deviceId, pName, spec, value, 'knob', ctrlSpec);
        }
        html += `</div></div>`;
    }

    // Add preserve_luminosity toggle
    const plSpec = def.params['preserve_luminosity'];
    if (plSpec) {
        const plVal = device.params['preserve_luminosity'] ?? plSpec.default;
        html += createControl(deviceId, 'preserve_luminosity', plSpec, plVal, 'toggle');
    }

    return html;
}

// --- Override renderChain to inject custom color controls ---
const _origRenderChain = renderChain;
renderChain = function() {
    const rack = document.getElementById('chain-rack');
    document.getElementById('chain-count').textContent = `${chain.length} device${chain.length !== 1 ? 's' : ''}`;

    rack.innerHTML = chain.map(device => {
        const def = effectDefs.find(e => e.name === device.name);
        const bypassClass = device.bypassed ? 'bypassed' : '';
        const powerClass = device.bypassed ? 'off' : 'on';

        let paramsHtml = '';
        if (def) {
            if (device.name === 'curves') {
                // Replace standard controls with curves canvas editor
                paramsHtml = renderCurvesEditor(device.id, device);
                // Still render interpolation dropdown
                const interpSpec = def.params['interpolation'];
                if (interpSpec) {
                    const val = device.params['interpolation'] ?? interpSpec.default;
                    const ctrlSpec = controlMap?.effects?.[device.name]?.params?.['interpolation'];
                    paramsHtml += createControl(device.id, 'interpolation', interpSpec, val, 'dropdown', ctrlSpec);
                }
            } else if (device.name === 'colorbalance') {
                // Grouped color balance rendering
                paramsHtml = renderColorBalanceGrouped(device.id, device, def);
            } else if (device.name === 'hsladjust') {
                // Standard params + color strip
                for (const [key, spec] of Object.entries(def.params)) {
                    const value = device.params[key] ?? spec.default;
                    const ctrlSpec = controlMap?.effects?.[device.name]?.params?.[key];
                    const ctrlType = ctrlSpec?.control_type || (spec.type === 'string' ? 'dropdown' : spec.type === 'bool' ? 'toggle' : 'knob');
                    paramsHtml += createControl(device.id, key, spec, value, ctrlType, ctrlSpec);
                }
                // Add hue color strip
                const targetHue = device.params['target_hue'] || 'all';
                paramsHtml += renderHslStrip(device.id, targetHue);
            } else {
                // Default rendering for all other effects
                for (const [key, spec] of Object.entries(def.params)) {
                    const value = device.params[key] ?? spec.default;
                    const ctrlSpec = controlMap?.effects?.[device.name]?.params?.[key];
                    const ctrlType = ctrlSpec?.control_type || (spec.type === 'string' ? 'dropdown' : spec.type === 'bool' ? 'toggle' : 'knob');
                    paramsHtml += createControl(device.id, key, spec, value, ctrlType, ctrlSpec);
                }
            }
        }

        const mixPct = Math.round((device.mix ?? 1.0) * 100);

        return `
            <div class="device ${bypassClass}" data-device-id="${device.id}" draggable="true"
                 oncontextmenu="deviceContextMenu(event, ${device.id})">
                <div class="device-header">
                    ${gripHTML()}
                    <button class="device-power ${powerClass}" onclick="toggleBypass(${device.id})" title="${device.bypassed ? 'Turn On' : 'Turn Off'}">${device.bypassed ? 'OFF' : 'ON'}</button>
                    <span class="device-name">${esc(device.name)}</span>
                    <span class="device-mix" title="Mix: ${mixPct}% — 0% = original frame, 100% = full effect">
                        <label>Mix</label>
                        <input type="range" class="mix-slider" min="0" max="100" value="${mixPct}"
                               data-device="${device.id}"
                               oninput="updateDeviceMix(${device.id}, this.value)"
                               onclick="event.stopPropagation()">
                        <span class="mix-value">${mixPct}%</span>
                    </span>
                    <button class="more-btn" onclick="event.stopPropagation(); deviceContextMenu(event, ${device.id})" title="More options">&#8943;</button>
                </div>
                <div class="device-params">
                    ${paramsHtml}
                </div>
            </div>`;
    }).join('');

    // Re-attach control event listeners
    document.querySelectorAll('.knob').forEach(setupKnobInteraction);
    document.querySelectorAll('.param-dropdown').forEach(setupDropdownInteraction);
    document.querySelectorAll('.param-toggle').forEach(setupToggleInteraction);

    // Setup curves canvases
    document.querySelectorAll('.curves-canvas').forEach(setupCurvesCanvas);

    // Setup device reordering
    setupDeviceReorder();

    // Re-apply LFO-mapped state to knob containers
    cleanLfoMappings();
    for (const mapping of lfoState.mappings) {
        const knobEl = document.querySelector(`.knob[data-device="${mapping.deviceId}"][data-param="${mapping.paramName}"]`);
        if (knobEl) {
            const container = knobEl.closest('.knob-container');
            if (container) container.classList.add('lfo-mapped');
        }
    }
    renderLfoPanel();

    // Re-apply automation-mapped state to knob containers
    applyAutomationMappedState();

    // Mark overflowing param panels
    document.querySelectorAll('.device-params').forEach(panel => {
        if (panel.scrollHeight > panel.clientHeight) {
            const total = panel.querySelectorAll('.param-control, .dropdown-container, .toggle-container, .curves-editor, .cb-section').length;
            const visible = Array.from(panel.children).filter(c => {
                const rect = c.getBoundingClientRect();
                const parentRect = panel.getBoundingClientRect();
                return rect.bottom <= parentRect.bottom;
            }).length;
            const hidden = total - visible;
            if (hidden > 0) {
                panel.classList.add('has-overflow');
                panel.dataset.overflowHint = `+${hidden} more`;
            }
        } else {
            panel.classList.remove('has-overflow');
        }
    });
};

// --- HSL dropdown change → update color strip ---
const _origSetupDropdownInteraction = setupDropdownInteraction;
setupDropdownInteraction = function(selectEl) {
    _origSetupDropdownInteraction(selectEl);
    // After the standard handler, also update HSL color strips
    selectEl.addEventListener('change', () => {
        const deviceId = parseInt(selectEl.dataset.device);
        const paramName = selectEl.dataset.param;
        if (paramName === 'target_hue') {
            // Re-render just to update the color strip
            renderChain();
        }
    });
};

// ============ BOOT ============
init();

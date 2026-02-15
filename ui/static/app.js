// Entropic — DAW-Style UI Controller
// Handles: effect browser, drag-to-chain, Moog knobs, real-time preview
// Layers panel (Photoshop), History panel (Photoshop), Ableton on/off toggles

const API = '';

// ============ TOAST / MODAL SYSTEM (replaces alert/prompt) ============

function showToast(message, type = 'info', action = null, duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    let html = `<span>${esc(message)}</span>`;
    if (action) {
        html += `<button class="toast-action" onclick="(${action.fn})()">${esc(action.label)}</button>`;
    }
    toast.innerHTML = html;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function showErrorToast(message) {
    showToast(message, 'error', null, 6000);
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
let controlMap = null;    // UI control type mapping (loaded from control-map.json)
let chain = [];           // Current effect chain: [{name, params, bypassed, id}, ...]
let videoLoaded = false;
let currentFrame = 0;
let totalFrames = 100;
let deviceIdCounter = 0;
let previewDebounce = null;
let selectedLayerId = null;
let mixLevel = 1.0;              // Wet/dry mix: 0.0 = original, 1.0 = full effect
let appMode = 'quick';           // 'quick' | 'timeline' | 'perform'

// Spatial mask drawing state
let maskDrawing = false;
let maskStartX = 0;
let maskStartY = 0;
let maskRect = null;             // {x, y, w, h} in canvas pixels during draw

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
    schedulePreview();
}

function jumpToHistory(index) {
    if (index < 0 || index >= history.length) return;
    historyIndex = index;
    restoreFromHistory(index);
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
    effectDefs = await effectsRes.json();
    if (controlsRes && controlsRes.ok) {
        controlMap = await controlsRes.json();
    }
    renderBrowser();
    setupDragDrop();
    setupFileInput();
    setupPanelTabs();
    setupKeyboard();
    setupMaskDrawing();
    pushHistory('Open');
    renderLayers();
    renderHistory();
    startHeartbeat();

    // Initialize timeline editor
    window.timelineEditor = new TimelineEditor('timeline-canvas');

    // Start in quick mode (hides timeline)
    setMode('quick');

    // Dismiss boot screen
    const boot = document.getElementById('boot-screen');
    if (boot) {
        boot.classList.add('fade-out');
        setTimeout(() => boot.remove(), 500);
    }
}

// ============ EFFECT BROWSER ============

let browserView = 'category';  // 'category' or 'package'
let packageDefs = null;        // Loaded on first package view

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
    } else {
        renderBrowserCategories();
    }
}

function renderBrowserCategories() {
    const list = document.getElementById('effect-list');

    // Build categories dynamically from effectDefs
    const groups = {};
    for (const def of effectDefs) {
        const cat = (def.category || 'other').toUpperCase();
        if (!groups[cat]) groups[cat] = [];
        groups[cat].push(def.name);
    }

    // Sort category names, but put common ones first
    const order = ['GLITCH', 'DISTORTION', 'TEXTURE', 'COLOR', 'TEMPORAL', 'MODULATION', 'ENHANCE', 'DESTRUCTION'];
    const sorted = order.filter(c => groups[c]);
    for (const c of Object.keys(groups)) {
        if (!sorted.includes(c)) sorted.push(c);
    }

    let html = '';
    for (const cat of sorted) {
        const names = groups[cat];
        if (!names || names.length === 0) continue;
        html += `<h3>${esc(cat)} <span class="count">${names.length}</span></h3>`;
        for (const name of names.sort()) {
            html += `
                <div class="effect-item" draggable="true" data-effect="${esc(name)}"
                     ondragstart="onBrowserDragStart(event, '${esc(name)}')"
                     title="${esc(effectDefs.find(e => e.name === name)?.description || '')}">
                    ${gripHTML()}
                    <span class="name">${esc(name)}</span>
                </div>`;
        }
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
            } catch (err) { console.error('Bad recipe data:', err); }
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

    document.getElementById('file-name').textContent = file.name;
    document.getElementById('empty-state').style.display = 'none';

    const form = new FormData();
    form.append('file', file);

    try {
        const res = await fetch(`${API}/api/upload`, { method: 'POST', body: form });
        const data = await res.json();

        videoLoaded = true;
        totalFrames = data.info.total_frames || 100;
        currentFrame = 0;

        const slider = document.getElementById('frame-slider');
        slider.max = totalFrames - 1;
        slider.value = 0;
        document.getElementById('frame-scrubber').style.display = appMode === 'quick' ? 'block' : 'none';

        showPreview(data.preview);
        updateFrameInfo(data.info);

        // Suggest perform mode (toast with action)
        if (appMode === 'quick') {
            showToast('Video loaded. Try Perform mode?', 'info', {
                label: 'Switch to Perform',
                fn: "function(){setMode('perform')}",
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
        console.error('Upload failed:', err);
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
            || document.getElementById('shortcut-overlay')?.style.display === 'flex';
    };

    document.addEventListener('keydown', e => {
        // --- Escape: close any open modal ---
        if (e.key === 'Escape') {
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
            if (appMode === 'perform') {
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

        // --- Perform mode shortcuts (keys 1-4, R, Shift+P) ---
        if (appMode === 'perform' && videoLoaded) {
            // Keys 1-4: trigger layers (blocked during review)
            if (e.key >= '1' && e.key <= '4') {
                e.preventDefault();
                if (!perfReviewing) {
                    const layerId = parseInt(e.key) - 1;
                    perfTriggerLayer(layerId, 'keydown');
                }
                return;
            }
            // R: toggle recording (blocked during review)
            if (e.key === 'r') {
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

        // P = Refresh preview
        if (e.key === 'p') {
            e.preventDefault(); previewChain(); return;
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
        // Perform mode: key release for gate mode (blocked during review)
        if (appMode === 'perform' && !perfReviewing && e.key >= '1' && e.key <= '4') {
            const layerId = parseInt(e.key) - 1;
            perfTriggerLayer(layerId, 'keyup');
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
    const device = chain.find(d => d.id === deviceId);
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

function duplicateSelected() {
    if (selectedLayerId === null) return;
    const device = chain.find(d => d.id === selectedLayerId);
    if (!device) return;
    const clone = {
        id: deviceIdCounter++,
        name: device.name,
        params: JSON.parse(JSON.stringify(device.params)),
        bypassed: device.bypassed,
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

function renderChain() {
    const rack = document.getElementById('chain-rack');
    document.getElementById('chain-count').textContent = `${chain.length} device${chain.length !== 1 ? 's' : ''}`;

    rack.innerHTML = chain.map(device => {
        const def = effectDefs.find(e => e.name === device.name);
        const bypassClass = device.bypassed ? 'bypassed' : '';
        const powerClass = device.bypassed ? 'off' : 'on';

        let paramsHtml = '';
        if (def) {
            for (const [key, spec] of Object.entries(def.params)) {
                const value = device.params[key] ?? spec.default;
                const ctrlSpec = controlMap?.effects?.[device.name]?.params?.[key];
                const ctrlType = ctrlSpec?.control_type || (spec.type === 'string' ? 'dropdown' : spec.type === 'bool' ? 'toggle' : 'knob');
                paramsHtml += createControl(device.id, key, spec, value, ctrlType, ctrlSpec);
            }
        }

        return `
            <div class="device ${bypassClass}" data-device-id="${device.id}" draggable="true"
                 oncontextmenu="deviceContextMenu(event, ${device.id})">
                <div class="device-header">
                    ${gripHTML()}
                    <button class="device-power ${powerClass}" onclick="toggleBypass(${device.id})" title="${device.bypassed ? 'Turn On' : 'Turn Off'}">${device.bypassed ? 'OFF' : 'ON'}</button>
                    <span class="device-name">${esc(device.name)}</span>
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

    // Setup device reordering
    setupDeviceReorder();
}

// ============ LAYERS PANEL (Photoshop-style) ============

function renderLayers() {
    const list = document.getElementById('layers-list');

    // PERFORM MODE: show perform layers instead of chain
    if (appMode === 'perform' && perfLayers.length > 0) {
        list.innerHTML = perfLayers.map((l, i) => {
            const state = perfLayerStates[l.layer_id] || {};
            const isActive = state.active || l.trigger_mode === 'always_on';
            const opacity = Math.round((state.opacity ?? l.opacity) * 100);
            const color = PERF_LAYER_COLORS[i] || '#888';
            const modeTag = l.trigger_mode.replace('_', ' ');
            const eyeIcon = state.muted ? '&#9675;' : '&#9679;';
            const eyeClass = state.muted ? 'hidden' : '';
            const activeClass = isActive ? 'selected' : '';
            const mutedClass = state.muted ? 'bypassed-layer' : '';

            return `
                <div class="layer-item ${activeClass} ${mutedClass}"
                     onclick="perfSelectLayerForEdit(${l.layer_id})">
                    <span class="layer-eye ${eyeClass}"
                          onclick="event.stopPropagation(); perfToggleMute(${l.layer_id})"
                          title="${state.muted ? 'Unmute' : 'Mute'}">${eyeIcon}</span>
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
        const eyeClass = device.bypassed ? 'hidden' : '';
        const eyeIcon = device.bypassed ? '&#9675;' : '&#9679;'; // hollow vs filled circle

        return `
            <div class="layer-item ${selectedClass} ${bypassedClass}"
                 data-layer-id="${device.id}"
                 onclick="selectLayer(${device.id})"
                 oncontextmenu="layerContextMenu(event, ${device.id})"
                 draggable="true">
                <span class="layer-eye ${eyeClass}" onclick="event.stopPropagation(); toggleBypass(${device.id})" title="${device.bypassed ? 'Show' : 'Hide'}">${eyeIcon}</span>
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

    list.innerHTML = history.map((entry, i) => {
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
    return `
        <div class="param-control dropdown-container">
            <label>${label}</label>
            <select class="param-dropdown" data-device="${deviceId}" data-param="${paramName}">
                ${optionsHtml}
            </select>
        </div>`;
}

function createToggle(deviceId, paramName, spec, value, label) {
    const checked = value ? 'checked' : '';
    return `
        <div class="param-control toggle-container">
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
    } else {
        normalized = (value - spec.min) / (spec.max - spec.min);
    }

    const angle = -135 + normalized * 270; // -135 to +135
    const arcLen = 48 * Math.PI;
    const dashLen = normalized * arcLen * 0.75;

    const displayVal = typeof value === 'number'
        ? (Number.isInteger(value) ? value : value.toFixed(2))
        : value;

    return `
        <div class="knob-container">
            <label>${label}</label>
            <div class="knob" data-device="${deviceId}" data-param="${paramName}"
                 data-min="${spec.min}" data-max="${spec.max}" data-type="${spec.type}"
                 data-value="${typeof value === 'object' ? value[0] : value}">
                <svg viewBox="0 0 48 48">
                    <circle class="arc-track" cx="24" cy="24" r="20"
                        stroke-dasharray="${arcLen * 0.75} ${arcLen}"
                        stroke-dashoffset="${-arcLen * 0.125}"
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
        const min = parseFloat(knobEl.dataset.min);
        const max = parseFloat(knobEl.dataset.max);
        const range = max - min;
        const type = knobEl.dataset.type;

        let newValue = startValue + dy * sensitivity * range;
        newValue = Math.max(min, Math.min(max, newValue));

        if (type === 'int') newValue = Math.round(newValue);

        knobEl.dataset.value = newValue;
        updateKnobVisual(knobEl, newValue, min, max, type);

        // Update chain data
        const deviceId = parseInt(knobEl.dataset.device);
        const paramName = knobEl.dataset.param;
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
        }

        schedulePreview();
    };

    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        document.removeEventListener('touchmove', onMove);
        document.removeEventListener('touchend', onUp);

        // Push history after knob adjustment is done
        const deviceId = parseInt(knobEl.dataset.device);
        const paramName = knobEl.dataset.param;
        const device = chain.find(d => d.id === deviceId);
        if (device) {
            pushHistory(`${device.name}: ${paramName}`);
            syncChainToRegion();
        }
    };

    const onDown = (e) => {
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
    const normalized = (value - min) / (max - min);
    const angle = -135 + normalized * 270;
    const arcLen = 48 * Math.PI;
    const dashLen = normalized * arcLen * 0.75;

    const indicator = knobEl.querySelector('.indicator');
    const arcFill = knobEl.querySelector('.arc-fill');
    const valueSpan = knobEl.parentElement.querySelector('.knob-value');

    if (indicator) indicator.style.transform = `translateX(-50%) rotate(${angle}deg)`;
    if (arcFill) arcFill.setAttribute('stroke-dasharray', `${dashLen} ${arcLen}`);
    if (valueSpan) {
        valueSpan.textContent = type === 'int' ? Math.round(value) : value.toFixed(2);
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

function schedulePreview() {
    if (!videoLoaded) return;
    clearTimeout(previewDebounce);
    previewDebounce = setTimeout(previewChain, 150);
}

async function previewChain() {
    if (!videoLoaded) return;
    // Perform mode uses its own preview loop — skip
    if (appMode === 'perform' && perfPlaying) return;

    try {
        let res;
        if (appMode === 'perform' && perfLayers.length > 0) {
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
            // Quick mode: existing flat chain behavior
            const activeEffects = chain
                .filter(d => !d.bypassed)
                .map(d => ({ name: d.name, params: d.params }));
            res = await fetch(`${API}/api/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ effects: activeEffects, frame_number: currentFrame, mix: mixLevel }),
            });
        }
        const data = await res.json();
        showPreview(data.preview);
        updateMaskOverlay();
        // Sync perform mode UI with server envelope states
        if (data.layer_states && appMode === 'perform') {
            perfSyncWithServer(data.layer_states);
        }
    } catch (err) {
        console.error('Preview failed:', err);
    }
}

function showPreview(dataUrl) {
    const img = document.getElementById('preview-img');
    img.src = dataUrl;
    img.style.display = 'block';
    document.getElementById('empty-state').style.display = 'none';
}

// ============ CONTEXT MENU ============

let ctxTarget = null; // {type: 'device'|'layer'|'canvas', id: ...}

function showContextMenu(e, items) {
    e.preventDefault();
    e.stopPropagation();
    const menu = document.getElementById('ctx-menu');

    menu.innerHTML = items.map(item => {
        if (item === '---') return '<div class="ctx-sep"></div>';
        const cls = item.danger ? 'ctx-item danger' : 'ctx-item';
        const shortcut = item.shortcut ? `<span class="ctx-shortcut">${item.shortcut}</span>` : '';
        return `<div class="${cls}" onclick="ctxAction('${item.action}'); hideContextMenu()">${item.label}${shortcut}</div>`;
    }).join('');

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

function ctxAction(action) {
    if (!ctxTarget) return;
    const id = ctxTarget.id;
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
    }
}

function deviceContextMenu(e, deviceId) {
    ctxTarget = { type: 'device', id: deviceId };
    const device = chain.find(d => d.id === deviceId);
    const idx = chain.findIndex(d => d.id === deviceId);
    showContextMenu(e, [
        { label: device?.bypassed ? 'Turn On' : 'Turn Off', action: 'bypass', shortcut: 'Click power' },
        { label: 'Isolate (hide others)', action: 'solo' },
        '---',
        { label: 'Duplicate', action: 'duplicate', shortcut: 'Cmd+D' },
        { label: 'Reset Parameters', action: 'resetParams' },
        '---',
        { label: 'Move Up', action: 'moveUp', shortcut: idx > 0 ? '' : '(first)' },
        { label: 'Move Down', action: 'moveDown', shortcut: idx < chain.length - 1 ? '' : '(last)' },
        '---',
        { label: 'Remove', action: 'remove', danger: true, shortcut: 'Del' },
    ]);
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
    } catch (err) {
        console.error('Randomize failed:', err);
    }
}

// ============ WET/DRY MIX ============

function onMixChange(value) {
    mixLevel = parseInt(value) / 100;
    document.getElementById('mix-value').textContent = `${parseInt(value)}%`;
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

    // In timeline mode, include regions data
    if (appMode === 'timeline' && window.timelineEditor) {
        settings.timeline_regions = timelineEditor.getActiveRegions().map(r => ({
            start: r.startFrame,
            end: r.endFrame,
            effects: (r.effects || []).filter(e => !e.bypassed),
            mask: r.mask || null,
        }));
    }

    try {
        const endpoint = (appMode === 'timeline' && settings.timeline_regions)
            ? `${API}/api/export/timeline`
            : `${API}/api/export`;
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            closeExportDialog();
            const info = data.size_mb
                ? `${data.size_mb}MB | ${data.format}`
                : `${data.format} | ${data.frames} frames`;
            showToast(`Exported: ${info}`, 'success', {
                label: 'Reveal in Finder',
                fn: `function(){revealInFinder('${(data.path || '').replace(/'/g, "\\'")}')}`
            }, 8000);
        } else {
            showErrorToast(`Export failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        showErrorToast(`Export error: ${err.message}`);
    } finally {
        btn.textContent = origText;
        btn.disabled = false;
    }
}

// ============ A/B COMPARE (Space Bar) ============

let originalPreviewSrc = null;
let isShowingOriginal = false;

// ============ MODE SWITCHING (Quick / Timeline) ============

function setMode(mode) {
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
            appMode = 'quick';
            appEl.classList.remove('perform-mode');
            appEl.classList.add('quick-mode');
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === 'quick');
            });
            if (badge) badge.textContent = 'QUICK';
            return;
        }
        perfInitLayers();
    }

    schedulePreview();
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
    schedulePreview();
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
        chain: chain.map(d => ({ name: d.name, params: d.params, bypassed: d.bypassed })),
        mixLevel,
        currentFrame,
        totalFrames,
    };
    // Include perform mode data
    if (appMode === 'perform' && perfLayers.length > 0) {
        state.perfLayers = perfLayers;
        state.perfLayerStates = perfLayerStates;
        state.perfSession = perfSession;
        state.perfFrameIndex = perfFrameIndex;
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
                }));
                selectedLayerId = chain.length > 0 ? chain[chain.length - 1].id : null;
                renderChain();
                renderLayers();
            }

            // Restore mix
            if (p.mixLevel !== undefined) {
                mixLevel = p.mixLevel;
                document.getElementById('mix-slider').value = mixLevel * 100;
                document.getElementById('mix-value').textContent = Math.round(mixLevel * 100) + '%';
            }

            // Restore perform mode state
            if (p.perfLayers) {
                perfLayers = p.perfLayers;
                perfLayerStates = p.perfLayerStates || {};
                perfSession = p.perfSession || {type:'performance', lanes:[]};
                perfFrameIndex = p.perfFrameIndex || 0;
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
        console.error('Failed to load presets:', err);
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
                <div class="preset-item" onclick="loadPreset(${JSON.stringify(JSON.stringify(p.effects))})" title="${esc(p.description || '')}">
                    <div class="preset-name">${esc(p.name)}</div>
                    <div class="preset-desc">${esc(p.description || '')}</div>
                    ${tags ? `<div class="preset-tags">${tags}</div>` : ''}
                </div>`;
        }
    }
    list.innerHTML = html;
}

function loadPreset(effectsJson) {
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
            body: JSON.stringify({ name, effects, description: desc, tags: [] }),
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
    // If Quick mode had effects, migrate them to L1 (handoff)
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

            // Handoff: Quick mode chain -> L1 effects
            if (quickChain && quickChain.length > 0 && perfLayers.length > 1) {
                perfLayers[1].effects = quickChain;
                perfLayers[1].name = 'Quick Chain';
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
            <div class="strip-bottom">
                <button class="${isMuted ? 'muted' : ''}" onclick="perfToggleMute(${l.layer_id})">M</button>
                <button class="${isSoloed ? 'soloed' : ''}" onclick="perfToggleSolo(${l.layer_id})">S</button>
            </div>
        </div>`;
    }

    // Master strip
    html += `
    <div class="channel-strip master-strip">
        <div class="channel-strip-header">
            <span class="strip-color" style="background:var(--text-dim)"></span>
            <span class="strip-name">MASTER</span>
        </div>
        <div style="padding:8px 0;font-size:10px;color:var(--text-dim);">Preview: ${PERF_FPS}fps</div>
        <div class="strip-fader-wrap">
            <input type="range" class="strip-fader" min="0" max="100" value="100"
                   oninput="mixLevel = this.value / 100; document.getElementById('mix-slider').value = this.value; document.getElementById('mix-value').textContent = this.value + '%';">
            <span class="strip-fader-val">100%</span>
        </div>
        <div class="strip-bottom">
            <button onclick="perfPanic()">PANIC</button>
        </div>
    </div>`;

    mixer.innerHTML = html;
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
        // Queue trigger event for server ADSR processing
        perfTriggerQueue.push({ layer_id: layerId, event: 'on' });
        // Record event for automation
        perfRecordEvent(layerId, 'active', state.active ? 1.0 : 0.0);
    } else if (eventType === 'keyup') {
        if (mode === 'gate') {
            state.active = false;
            perfRecordEvent(layerId, 'active', 0.0);
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
        }).catch(() => {});
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
        }).catch(() => {});
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
        }).catch(() => {});
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
        }).catch(() => {});
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
            }).catch(() => {});
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
                }).catch(() => {})
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
    if (hudRec) hudRec.textContent = perfReviewing ? '[REVIEW]' : (perfRecording ? '[REC]' : '[BUF]');
    if (hudTime) hudTime.textContent = formatTime(perfFrameIndex / 30);
    if (hudEvents) hudEvents.textContent = `${perfEventCount} ev`;
}

function perfScrub(value) {
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

    if (perfRecording) {
        // Clear buffer for fresh take
        perfSession = { type: 'performance', lanes: [] };
        perfEventCount = 0;
        if (btn) btn.classList.add('recording');
        showToast('Recording armed — buffer cleared', 'info', null, 2000);
    } else {
        if (btn) btn.classList.remove('recording');
        if (perfEventCount > 0) {
            showToast(`Recording stopped: ${perfEventCount} events`, 'success', {
                label: 'Save',
                fn: 'perfSaveSession',
            }, 10000);
            showToast('Review your performance', 'info', {
                label: 'Review',
                fn: 'perfReviewStart',
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
    }
    renderMixer();
    showToast('ALL LAYERS RESET', 'info', null, 1000);
    if (!perfPlaying) schedulePreview();
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
            showToast(`Rendered: ${data.size_mb}MB @ ${data.fps}fps`, 'success', {
                label: 'Reveal in Finder',
                fn: `function(){revealInFinder('${(data.path || '').replace(/'/g, "\\'")}')}`,
            }, 8000);
        } else {
            showErrorToast(`Render failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        showErrorToast(`Render error: ${err.message}`);
    } finally {
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

    // Reset to start
    perfFrameIndex = 0;
    perfReviewing = true;
    perfPlaying = true;

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
    if (appMode === 'perform' && perfEventCount > 0) {
        e.preventDefault();
        e.returnValue = 'You have unsaved performance data. Leave?';
    }
});

// ============ BOOT ============
init();

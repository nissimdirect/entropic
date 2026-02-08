// Entropic — DAW-Style UI Controller
// Handles: effect browser, drag-to-chain, Moog knobs, real-time preview
// Layers panel (Photoshop), History panel (Photoshop), Ableton on/off toggles

const API = '';

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
    pushHistory('Open');
    renderLayers();
    renderHistory();
}

// ============ EFFECT BROWSER ============

function renderBrowser() {
    const list = document.getElementById('effect-list');

    const categories = {
        'Glitch': ['pixelsort', 'channelshift', 'displacement', 'bitcrush'],
        'Distortion': ['wave', 'mirror', 'chromatic'],
        'Texture': ['scanlines', 'vhs', 'noise', 'blur', 'sharpen', 'edges', 'posterize'],
        'Color': ['hueshift', 'contrast', 'saturation', 'exposure', 'invert', 'temperature'],
    };

    let html = '';
    for (const [cat, names] of Object.entries(categories)) {
        html += `<h3>${cat}</h3>`;
        for (const name of names) {
            const def = effectDefs.find(e => e.name === name);
            if (!def) continue;
            html += `
                <div class="effect-item" draggable="true" data-effect="${name}"
                     ondragstart="onBrowserDragStart(event, '${name}')">
                    ${gripHTML()}
                    <span class="name">${name}</span>
                </div>`;
        }
    }
    list.innerHTML = html;
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
        const name = e.dataTransfer.getData('effect-name');
        if (name) addToChain(name);
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

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

async function uploadVideo(file) {
    // Client-side validation
    if (file.size > MAX_FILE_SIZE) {
        alert(`File too large (${(file.size / 1024 / 1024).toFixed(0)}MB). Maximum: ${MAX_FILE_SIZE / 1024 / 1024}MB`);
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
        alert(`Unsupported file type: .${ext}\nAllowed: ${allowed.join(', ')}`);
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

        const slider = document.getElementById('frame-slider');
        slider.max = totalFrames - 1;
        slider.value = 0;
        document.getElementById('frame-scrubber').style.display = 'block';

        showPreview(data.preview);
        updateFrameInfo(data.info);
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
    document.addEventListener('keydown', e => {
        // Cmd/Ctrl+Z = Undo
        if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
            e.preventDefault();
            undo();
        }
        // Cmd/Ctrl+Shift+Z = Redo
        if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) {
            e.preventDefault();
            redo();
        }
        // Space = A/B compare
        if (e.code === 'Space' && videoLoaded && !isShowingOriginal) {
            e.preventDefault();
            isShowingOriginal = true;
            const img = document.getElementById('preview-img');
            originalPreviewSrc = img.src;
            fetch(`${API}/api/frame/${currentFrame}`)
                .then(r => r.json())
                .then(data => {
                    if (isShowingOriginal) img.src = data.preview;
                });
        }
        // Cmd/Ctrl+D = Duplicate selected
        if ((e.metaKey || e.ctrlKey) && e.key === 'd') {
            e.preventDefault();
            duplicateSelected();
        }
        // Delete/Backspace = remove selected layer
        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedLayerId !== null) {
            // Don't delete if focused on an input
            if (document.activeElement.tagName === 'INPUT') return;
            e.preventDefault();
            removeFromChain(selectedLayerId);
        }
    });

    document.addEventListener('keyup', e => {
        if (e.code === 'Space' && isShowingOriginal) {
            e.preventDefault();
            isShowingOriginal = false;
            const img = document.getElementById('preview-img');
            if (originalPreviewSrc) img.src = originalPreviewSrc;
        }
    });
}

// ============ EFFECT CHAIN ============

function addToChain(effectName) {
    const def = effectDefs.find(e => e.name === effectName);
    if (!def) return;

    const device = {
        id: deviceIdCounter++,
        name: effectName,
        params: {},
        bypassed: false,
    };

    // Copy defaults
    for (const [k, v] of Object.entries(def.params)) {
        if (v.type === 'xy') {
            device.params[k] = [...v.default];
        } else {
            device.params[k] = v.default;
        }
    }

    chain.push(device);
    selectedLayerId = device.id;
    pushHistory(`Add ${effectName}`);
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

    const activeEffects = chain
        .filter(d => !d.bypassed)
        .map(d => ({ name: d.name, params: d.params }));

    try {
        const res = await fetch(`${API}/api/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ effects: activeEffects, frame_number: currentFrame, mix: mixLevel }),
        });
        const data = await res.json();
        showPreview(data.preview);
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
    if (!videoLoaded) { alert('Load a file first.'); return; }
    if (chain.length === 0) { alert('Add at least one effect.'); return; }
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

    try {
        const res = await fetch(`${API}/api/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        const data = await res.json();
        if (data.status === 'ok') {
            closeExportDialog();
            const info = data.size_mb
                ? `Size: ${data.size_mb}MB | ${data.dimensions} | ${data.format}`
                : `Format: ${data.format} | ${data.dimensions} | ${data.frames} frames`;
            alert(`Export complete!\nFile: ${data.path}\n${info}`);
        } else {
            alert(`Export failed: ${data.detail || 'Unknown error'}`);
        }
    } catch (err) {
        alert(`Export error: ${err.message}`);
    } finally {
        btn.textContent = origText;
        btn.disabled = false;
    }
}

// ============ A/B COMPARE (Space Bar) ============

let originalPreviewSrc = null;
let isShowingOriginal = false;

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
    if (chain.length === 0) { alert('Add effects to the chain first.'); return; }
    const name = prompt('Preset name:');
    if (!name) return;
    const desc = prompt('Description (optional):') || '';

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
            alert(`Preset "${name}" saved.`);
        }
    } catch (err) {
        alert(`Failed to save preset: ${err.message}`);
    }
}

// ============ BOOT ============
init();

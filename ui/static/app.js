// Entropic — DAW-Style UI Controller
// Handles: effect browser, drag-to-chain, Moog knobs, real-time preview
// Layers panel (Photoshop), History panel (Photoshop), Ableton on/off toggles

const API = '';
let effectDefs = [];      // Effect definitions from server
let chain = [];           // Current effect chain: [{name, params, bypassed, id}, ...]
let videoLoaded = false;
let currentFrame = 0;
let totalFrames = 100;
let deviceIdCounter = 0;
let previewDebounce = null;
let selectedLayerId = null;

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
    const res = await fetch(`${API}/api/effects`);
    effectDefs = await res.json();
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
        'Glitch': ['pixelsort', 'channelshift', 'scanlines', 'bitcrush'],
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
        if (files.length > 0 && files[0].type.startsWith('video/')) {
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

async function uploadVideo(file) {
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
    el.textContent = `${w}x${h} | ${fps}fps | Frame ${currentFrame}/${totalFrames}`;
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
                if (spec.type === 'string') continue;
                const value = device.params[key] ?? spec.default;
                paramsHtml += createKnob(device.id, key, spec, value);
            }
        }

        return `
            <div class="device ${bypassClass}" data-device-id="${device.id}" draggable="true">
                <div class="device-header">
                    ${gripHTML()}
                    <button class="device-power ${powerClass}" onclick="toggleBypass(${device.id})" title="${device.bypassed ? 'Turn On' : 'Turn Off'}">${device.bypassed ? 'OFF' : 'ON'}</button>
                    <span class="device-name">${device.name}</span>
                    <button class="remove-btn" onclick="removeFromChain(${device.id})" title="Remove">&times;</button>
                </div>
                <div class="device-params">
                    ${paramsHtml}
                </div>
            </div>`;
    }).join('');

    // Re-attach knob event listeners
    document.querySelectorAll('.knob').forEach(setupKnobInteraction);

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
                 draggable="true">
                <span class="layer-eye ${eyeClass}" onclick="event.stopPropagation(); toggleBypass(${device.id})" title="${device.bypassed ? 'Show' : 'Hide'}">${eyeIcon}</span>
                ${gripHTML()}
                <span class="layer-name">${device.name}</span>
                <span class="layer-index">${layerNum}</span>
                <span class="layer-delete" onclick="event.stopPropagation(); removeFromChain(${device.id})" title="Delete">&times;</span>
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

function createKnob(deviceId, paramName, spec, value) {
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
            <label>${paramName}</label>
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
            body: JSON.stringify({ effects: activeEffects, frame_number: currentFrame }),
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

// ============ A/B COMPARE (Space Bar) ============

let originalPreviewSrc = null;
let isShowingOriginal = false;

// ============ BOOT ============
init();

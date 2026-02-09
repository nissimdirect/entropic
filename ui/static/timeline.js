// Entropic — Timeline Editor
// Canvas-based timeline with tracks, regions, playhead, I/O markers, zoom/scroll
// Inspired by Ableton, Logic, Premiere

// ============ DATA MODEL ============

class Track {
    constructor(id, name, type = 'video') {
        this.id = id;
        this.name = name;
        this.type = type;         // 'video' | 'effects'
        this.muted = false;
        this.soloed = false;
        this.regions = [];
        this.height = 60;
    }
}

class Region {
    constructor(id, trackId, startFrame, endFrame) {
        this.id = id;
        this.trackId = trackId;
        this.startFrame = startFrame;
        this.endFrame = endFrame;
        this.effects = [];        // [{name, params, bypassed}, ...]
        this.label = '';
        this.color = null;        // null = use track default
        this.mask = null;         // null = full frame, or {x, y, w, h} as 0-1 ratios
    }
}

// ============ TIMELINE EDITOR ============

class TimelineEditor {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        // State
        this.tracks = [new Track(0, 'Video 1', 'video')];
        this.playhead = 0;
        this.inPoint = null;
        this.outPoint = null;
        this.zoom = 2.0;           // pixels per frame
        this.scrollX = 0;
        this.selectedRegionId = null;
        this.selectedTrackId = 0;
        this.isPlaying = false;
        this.playInterval = null;
        this.fps = 30;
        this.totalFrames = 100;
        this.trackHeaderWidth = 120;
        this.rulerHeight = 24;
        this.nextTrackId = 1;
        this.nextRegionId = 0;

        // Interaction state
        this.isDragging = false;
        this.dragType = null;       // 'playhead', 'region-move', 'region-resize-l', 'region-resize-r', 'scroll', 'select-region'
        this.dragTarget = null;
        this.dragStartX = 0;
        this.dragStartFrame = 0;
        this.dragOrigStart = 0;
        this.dragOrigEnd = 0;
        this.hoveredRegion = null;
        this.hoverEdge = null;      // 'left', 'right', null

        // Colors
        this.colors = {
            bg: '#0a0a0b',
            trackBg: '#111114',
            trackAlt: '#141418',
            trackHeader: '#1a1a1e',
            trackHeaderBorder: '#2a2a30',
            ruler: '#1a1a1e',
            rulerText: '#555',
            rulerMajor: '#444',
            rulerMinor: '#2a2a30',
            playhead: '#ff3d3d',
            inPoint: '#4caf50',
            outPoint: '#ff5252',
            regionDefault: '#3a5a8a',
            regionSelected: '#5a8abb',
            regionBorder: '#6a9acc',
            regionMuted: '#333',
            text: '#ccc',
            textDim: '#666',
            textMuted: '#444',
            soloBtn: '#f5a623',
            muteBtn: '#ff5252',
        };

        // Track default colors for regions
        this.trackColors = [
            '#3a5a8a', '#5a3a8a', '#3a8a5a', '#8a5a3a',
            '#8a3a5a', '#3a8a8a', '#8a8a3a', '#5a8a3a',
        ];

        this.setupEvents();
        this.resize();
    }

    // ============ RESIZE ============

    resize() {
        if (!this.canvas) return;
        const wrapper = this.canvas.parentElement;
        if (!wrapper) return;
        const rect = wrapper.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.ctx.scale(dpr, dpr);
        this.canvasW = rect.width;
        this.canvasH = rect.height;
        this.draw();
    }

    // ============ COORDINATE HELPERS ============

    frameToX(frame) {
        return this.trackHeaderWidth + (frame * this.zoom) - this.scrollX;
    }

    xToFrame(x) {
        return Math.round((x - this.trackHeaderWidth + this.scrollX) / this.zoom);
    }

    getTimelineWidth() {
        return this.canvasW - this.trackHeaderWidth;
    }

    // ============ DRAWING ============

    draw() {
        if (!this.ctx) return;
        const ctx = this.ctx;
        const w = this.canvasW;
        const h = this.canvasH;

        // Clear
        ctx.fillStyle = this.colors.bg;
        ctx.fillRect(0, 0, w, h);

        // Draw ruler
        this.drawRuler();

        // Draw tracks
        let y = this.rulerHeight;
        for (let i = 0; i < this.tracks.length; i++) {
            const track = this.tracks[i];
            this.drawTrack(track, y, i);
            y += track.height;
        }

        // Draw I/O markers (behind playhead)
        this.drawIOMarkers();

        // Draw playhead (always on top)
        this.drawPlayhead();
    }

    drawRuler() {
        const ctx = this.ctx;
        const w = this.canvasW;
        const rh = this.rulerHeight;

        // Background
        ctx.fillStyle = this.colors.ruler;
        ctx.fillRect(0, 0, w, rh);

        // Header corner
        ctx.fillStyle = this.colors.trackHeader;
        ctx.fillRect(0, 0, this.trackHeaderWidth, rh);

        // Border
        ctx.strokeStyle = this.colors.trackHeaderBorder;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(this.trackHeaderWidth, 0);
        ctx.lineTo(this.trackHeaderWidth, rh);
        ctx.stroke();

        // Time markers
        ctx.font = '9px Menlo, Monaco, monospace';
        ctx.textBaseline = 'middle';

        // Calculate tick interval based on zoom
        let tickInterval = 1;
        const minPixelsPerTick = 60;
        const candidates = [1, 5, 10, 15, 30, 60, 150, 300, 600, 1800];
        for (const c of candidates) {
            if (c * this.zoom >= minPixelsPerTick) {
                tickInterval = c;
                break;
            }
        }

        const startFrame = Math.max(0, Math.floor(this.scrollX / this.zoom));
        const endFrame = Math.min(this.totalFrames, Math.ceil((this.scrollX + this.getTimelineWidth()) / this.zoom));

        const firstTick = Math.ceil(startFrame / tickInterval) * tickInterval;

        for (let f = firstTick; f <= endFrame; f += tickInterval) {
            const x = this.frameToX(f);
            if (x < this.trackHeaderWidth || x > w) continue;

            // Major tick
            ctx.fillStyle = this.colors.rulerText;
            const secs = f / this.fps;
            let label;
            if (secs >= 60) {
                const m = Math.floor(secs / 60);
                const s = Math.floor(secs % 60);
                label = `${m}:${String(s).padStart(2, '0')}`;
            } else {
                label = secs.toFixed(1) + 's';
            }
            ctx.fillText(label, x + 3, rh / 2);

            ctx.strokeStyle = this.colors.rulerMajor;
            ctx.beginPath();
            ctx.moveTo(x, rh - 8);
            ctx.lineTo(x, rh);
            ctx.stroke();

            // Minor ticks (half-intervals)
            if (tickInterval > 1) {
                const halfX = this.frameToX(f + tickInterval / 2);
                if (halfX > this.trackHeaderWidth && halfX < w) {
                    ctx.strokeStyle = this.colors.rulerMinor;
                    ctx.beginPath();
                    ctx.moveTo(halfX, rh - 4);
                    ctx.lineTo(halfX, rh);
                    ctx.stroke();
                }
            }
        }

        // Bottom border
        ctx.strokeStyle = this.colors.trackHeaderBorder;
        ctx.beginPath();
        ctx.moveTo(0, rh);
        ctx.lineTo(w, rh);
        ctx.stroke();
    }

    drawTrack(track, y, index) {
        const ctx = this.ctx;
        const w = this.canvasW;
        const h = track.height;

        // Track background (alternating)
        ctx.fillStyle = index % 2 === 0 ? this.colors.trackBg : this.colors.trackAlt;
        if (track.muted) ctx.globalAlpha = 0.5;
        ctx.fillRect(this.trackHeaderWidth, y, w - this.trackHeaderWidth, h);
        ctx.globalAlpha = 1.0;

        // Track header
        ctx.fillStyle = this.colors.trackHeader;
        ctx.fillRect(0, y, this.trackHeaderWidth, h);

        // Selected track highlight
        if (track.id === this.selectedTrackId) {
            ctx.fillStyle = 'rgba(255,61,61,0.05)';
            ctx.fillRect(this.trackHeaderWidth, y, w - this.trackHeaderWidth, h);
            ctx.strokeStyle = 'rgba(255,61,61,0.3)';
            ctx.lineWidth = 1;
            ctx.strokeRect(0.5, y + 0.5, this.trackHeaderWidth - 1, h - 1);
        }

        // Track name
        ctx.fillStyle = track.muted ? this.colors.textMuted : this.colors.text;
        ctx.font = '10px Menlo, Monaco, monospace';
        ctx.textBaseline = 'middle';
        ctx.fillText(track.name, 8, y + h / 2 - 8);

        // S (solo) and M (mute) buttons
        const btnY = y + h / 2 + 4;
        const btnW = 16;
        const btnH = 14;

        // Solo button
        ctx.fillStyle = track.soloed ? this.colors.soloBtn : this.colors.trackHeaderBorder;
        ctx.fillRect(8, btnY, btnW, btnH);
        ctx.fillStyle = track.soloed ? '#000' : this.colors.textDim;
        ctx.font = '8px Menlo, Monaco, monospace';
        ctx.fillText('S', 12, btnY + btnH / 2 + 1);

        // Mute button
        ctx.fillStyle = track.muted ? this.colors.muteBtn : this.colors.trackHeaderBorder;
        ctx.fillRect(28, btnY, btnW, btnH);
        ctx.fillStyle = track.muted ? '#fff' : this.colors.textDim;
        ctx.fillText('M', 32, btnY + btnH / 2 + 1);

        // Header right border
        ctx.strokeStyle = this.colors.trackHeaderBorder;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(this.trackHeaderWidth, y);
        ctx.lineTo(this.trackHeaderWidth, y + h);
        ctx.stroke();

        // Bottom border
        ctx.beginPath();
        ctx.moveTo(0, y + h);
        ctx.lineTo(w, y + h);
        ctx.stroke();

        // Draw regions on this track
        for (const region of track.regions) {
            this.drawRegion(region, track, y);
        }
    }

    drawRegion(region, track, trackY) {
        const ctx = this.ctx;
        const x1 = this.frameToX(region.startFrame);
        const x2 = this.frameToX(region.endFrame);
        const rw = x2 - x1;
        const padding = 3;
        const ry = trackY + padding;
        const rh = track.height - padding * 2;

        // Clip to timeline area
        if (x2 < this.trackHeaderWidth || x1 > this.canvasW) return;

        const isSelected = region.id === this.selectedRegionId;
        const isMuted = track.muted;

        // Region background
        const baseColor = region.color || this.trackColors[track.id % this.trackColors.length];
        ctx.fillStyle = isMuted ? this.colors.regionMuted : (isSelected ? this.colors.regionSelected : baseColor);
        ctx.globalAlpha = isMuted ? 0.4 : 0.8;

        const clampX = Math.max(this.trackHeaderWidth, x1);
        const clampW = Math.min(this.canvasW, x2) - clampX;
        ctx.fillRect(clampX, ry, clampW, rh);

        // Region border
        ctx.globalAlpha = 1.0;
        ctx.strokeStyle = isSelected ? '#fff' : this.colors.regionBorder;
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.strokeRect(clampX + 0.5, ry + 0.5, clampW - 1, rh - 1);

        // Region label
        if (rw > 40) {
            ctx.fillStyle = isSelected ? '#fff' : this.colors.text;
            ctx.font = '9px Menlo, Monaco, monospace';
            ctx.textBaseline = 'middle';
            const label = region.label || (region.effects.length > 0
                ? region.effects.map(e => e.name).join(' > ')
                : 'Empty');
            // Clip text to region width
            ctx.save();
            ctx.beginPath();
            ctx.rect(clampX + 4, ry, clampW - 8, rh);
            ctx.clip();
            ctx.fillText(label, clampX + 6, ry + rh / 2);
            ctx.restore();
        }

        // Resize handles (small triangles at edges)
        if (isSelected && rw > 20) {
            ctx.fillStyle = '#fff';
            // Left handle
            ctx.beginPath();
            ctx.moveTo(clampX, ry);
            ctx.lineTo(clampX + 6, ry);
            ctx.lineTo(clampX, ry + 6);
            ctx.fill();
            // Right handle
            const rx2 = Math.min(this.canvasW, x2);
            ctx.beginPath();
            ctx.moveTo(rx2, ry);
            ctx.lineTo(rx2 - 6, ry);
            ctx.lineTo(rx2, ry + 6);
            ctx.fill();
        }
    }

    drawPlayhead() {
        const ctx = this.ctx;
        const x = this.frameToX(this.playhead);

        if (x < this.trackHeaderWidth || x > this.canvasW) return;

        // Line
        ctx.strokeStyle = this.colors.playhead;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, this.canvasH);
        ctx.stroke();

        // Triangle handle at top
        ctx.fillStyle = this.colors.playhead;
        ctx.beginPath();
        ctx.moveTo(x - 6, 0);
        ctx.lineTo(x + 6, 0);
        ctx.lineTo(x, 10);
        ctx.closePath();
        ctx.fill();

        // Frame number label
        ctx.font = '9px Menlo, Monaco, monospace';
        ctx.textBaseline = 'top';
        ctx.fillStyle = this.colors.playhead;
        const label = String(this.playhead);
        const textW = ctx.measureText(label).width;
        // Position label to the right of playhead, unless near right edge
        const labelX = x + 8 + textW > this.canvasW ? x - textW - 4 : x + 4;
        ctx.fillText(label, labelX, 12);
    }

    drawIOMarkers() {
        const ctx = this.ctx;

        if (this.inPoint !== null) {
            const x = this.frameToX(this.inPoint);
            if (x >= this.trackHeaderWidth && x <= this.canvasW) {
                ctx.strokeStyle = this.colors.inPoint;
                ctx.lineWidth = 1;
                ctx.setLineDash([4, 3]);
                ctx.beginPath();
                ctx.moveTo(x, this.rulerHeight);
                ctx.lineTo(x, this.canvasH);
                ctx.stroke();
                ctx.setLineDash([]);

                // "I" label
                ctx.fillStyle = this.colors.inPoint;
                ctx.font = 'bold 9px Menlo, Monaco, monospace';
                ctx.fillText('I', x + 2, this.rulerHeight + 10);
            }
        }

        if (this.outPoint !== null) {
            const x = this.frameToX(this.outPoint);
            if (x >= this.trackHeaderWidth && x <= this.canvasW) {
                ctx.strokeStyle = this.colors.outPoint;
                ctx.lineWidth = 1;
                ctx.setLineDash([4, 3]);
                ctx.beginPath();
                ctx.moveTo(x, this.rulerHeight);
                ctx.lineTo(x, this.canvasH);
                ctx.stroke();
                ctx.setLineDash([]);

                // "O" label
                ctx.fillStyle = this.colors.outPoint;
                ctx.font = 'bold 9px Menlo, Monaco, monospace';
                ctx.fillText('O', x + 2, this.rulerHeight + 10);
            }
        }

        // Shade I/O range
        if (this.inPoint !== null && this.outPoint !== null) {
            const x1 = this.frameToX(this.inPoint);
            const x2 = this.frameToX(this.outPoint);
            const clampX1 = Math.max(this.trackHeaderWidth, x1);
            const clampX2 = Math.min(this.canvasW, x2);
            if (clampX2 > clampX1) {
                ctx.fillStyle = 'rgba(76, 175, 80, 0.06)';
                ctx.fillRect(clampX1, this.rulerHeight, clampX2 - clampX1, this.canvasH - this.rulerHeight);
            }
        }
    }

    // ============ ZOOM / SCROLL ============

    zoomIn() {
        const center = this.scrollX + this.getTimelineWidth() / 2;
        this.zoom = Math.min(20, this.zoom * 1.3);
        this.scrollX = center - this.getTimelineWidth() / 2;
        this.clampScroll();
        this.draw();
    }

    zoomOut() {
        const center = this.scrollX + this.getTimelineWidth() / 2;
        this.zoom = Math.max(0.05, this.zoom / 1.3);
        this.scrollX = center - this.getTimelineWidth() / 2;
        this.clampScroll();
        this.draw();
    }

    fitToWindow() {
        const timelineW = this.getTimelineWidth();
        if (this.totalFrames > 0 && timelineW > 0) {
            this.zoom = timelineW / this.totalFrames;
            this.scrollX = 0;
        }
        this.draw();
    }

    scrollTo(frame) {
        this.scrollX = frame * this.zoom - this.getTimelineWidth() / 2;
        this.clampScroll();
        this.draw();
    }

    clampScroll() {
        const maxScroll = Math.max(0, this.totalFrames * this.zoom - this.getTimelineWidth());
        this.scrollX = Math.max(0, Math.min(this.scrollX, maxScroll));
    }

    // ============ PLAYHEAD ============

    setPlayhead(frame) {
        this.playhead = Math.max(0, Math.min(frame, this.totalFrames - 1));
        this.draw();
        // Notify app.js
        if (typeof onTimelinePlayheadChange === 'function') {
            onTimelinePlayheadChange(this.playhead);
        }
    }

    setInPoint() {
        this.inPoint = this.playhead;
        if (this.outPoint !== null && this.inPoint > this.outPoint) {
            this.outPoint = null;
        }
        this.draw();
        if (typeof showToast === 'function') {
            showToast(`In point: frame ${this.inPoint}`, 'info');
        }
    }

    setOutPoint() {
        this.outPoint = this.playhead;
        if (this.inPoint !== null && this.outPoint < this.inPoint) {
            this.inPoint = null;
        }
        this.draw();
        if (typeof showToast === 'function') {
            showToast(`Out point: frame ${this.outPoint}`, 'info');
        }
    }

    // ============ PLAYBACK ============

    togglePlayback() {
        if (this.isPlaying) {
            this.stopPlayback();
        } else {
            this.startPlayback();
        }
    }

    startPlayback() {
        if (this.isPlaying) return;
        this.isPlaying = true;
        const interval = 1000 / this.fps;
        this.playInterval = setInterval(() => {
            if (this.playhead >= this.totalFrames - 1) {
                this.stopPlayback();
                return;
            }
            this.setPlayhead(this.playhead + 1);

            // Auto-scroll to follow playhead
            const px = this.frameToX(this.playhead);
            if (px > this.canvasW - 50 || px < this.trackHeaderWidth + 50) {
                this.scrollTo(this.playhead);
            }
        }, interval);
    }

    stopPlayback() {
        this.isPlaying = false;
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }

    // ============ REGIONS ============

    createRegionFromIO() {
        if (this.inPoint === null || this.outPoint === null) {
            if (typeof showToast === 'function') {
                showToast('Set in-point (I) and out-point (O) first', 'info');
            }
            return null;
        }

        const track = this.tracks.find(t => t.id === this.selectedTrackId) || this.tracks[0];
        if (!track) return null;

        const start = Math.min(this.inPoint, this.outPoint);
        const end = Math.max(this.inPoint, this.outPoint);

        const region = new Region(this.nextRegionId++, track.id, start, end);
        track.regions.push(region);

        this.selectedRegionId = region.id;
        this.draw();

        if (typeof showToast === 'function') {
            showToast(`Region created: frames ${start}-${end}`, 'success');
        }
        if (typeof onRegionSelect === 'function') {
            onRegionSelect(region);
        }

        return region;
    }

    addTrack(name, type) {
        name = name || `Track ${this.tracks.length + 1}`;
        type = type || 'effects';
        const track = new Track(this.nextTrackId++, name, type);
        this.tracks.push(track);
        this.draw();
        return track;
    }

    findRegion(regionId) {
        for (const track of this.tracks) {
            const region = track.regions.find(r => r.id === regionId);
            if (region) return region;
        }
        return null;
    }

    findTrackForRegion(regionId) {
        for (const track of this.tracks) {
            if (track.regions.find(r => r.id === regionId)) return track;
        }
        return null;
    }

    deleteSelectedRegion() {
        if (this.selectedRegionId === null) return;
        for (const track of this.tracks) {
            const idx = track.regions.findIndex(r => r.id === this.selectedRegionId);
            if (idx !== -1) {
                track.regions.splice(idx, 1);
                this.selectedRegionId = null;
                this.draw();
                if (typeof showToast === 'function') {
                    showToast('Region deleted', 'info');
                }
                return;
            }
        }
    }

    getActiveRegions() {
        // Return all regions across all non-muted tracks
        const regions = [];
        const anySoloed = this.tracks.some(t => t.soloed);
        for (const track of this.tracks) {
            if (anySoloed && !track.soloed) continue;
            if (track.muted) continue;
            for (const region of track.regions) {
                regions.push(region);
            }
        }
        return regions;
    }

    getRegionsAtFrame(frame) {
        return this.getActiveRegions().filter(r => frame >= r.startFrame && frame <= r.endFrame);
    }

    isTrackMuted(trackId) {
        const track = this.tracks.find(t => t.id === trackId);
        if (!track) return true;
        const anySoloed = this.tracks.some(t => t.soloed);
        if (anySoloed && !track.soloed) return true;
        return track.muted;
    }

    // ============ TRACK SOLO/MUTE ============

    toggleTrackMute(trackId) {
        const track = this.tracks.find(t => t.id === trackId);
        if (!track) return;
        track.muted = !track.muted;
        this.draw();
    }

    toggleTrackSolo(trackId) {
        const track = this.tracks.find(t => t.id === trackId);
        if (!track) return;
        track.soloed = !track.soloed;
        this.draw();
    }

    unmuteAll() {
        for (const track of this.tracks) {
            track.muted = false;
            track.soloed = false;
        }
        this.draw();
    }

    // ============ HIT TESTING ============

    hitTest(canvasX, canvasY) {
        // Returns: { type: 'ruler'|'track-header'|'region'|'empty', track?, region?, edge? }

        // Ruler area
        if (canvasY < this.rulerHeight) {
            return { type: 'ruler' };
        }

        // Track header area
        if (canvasX < this.trackHeaderWidth) {
            let y = this.rulerHeight;
            for (const track of this.tracks) {
                if (canvasY >= y && canvasY < y + track.height) {
                    // Check if S or M button was clicked
                    const btnY = y + track.height / 2 + 4;
                    const btnH = 14;
                    if (canvasY >= btnY && canvasY <= btnY + btnH) {
                        if (canvasX >= 8 && canvasX < 24) {
                            return { type: 'solo-btn', track };
                        }
                        if (canvasX >= 28 && canvasX < 44) {
                            return { type: 'mute-btn', track };
                        }
                    }
                    return { type: 'track-header', track };
                }
                y += track.height;
            }
            return { type: 'empty' };
        }

        // Timeline area — check regions
        let y = this.rulerHeight;
        for (const track of this.tracks) {
            if (canvasY >= y && canvasY < y + track.height) {
                // Check regions on this track
                for (const region of track.regions) {
                    const x1 = this.frameToX(region.startFrame);
                    const x2 = this.frameToX(region.endFrame);
                    if (canvasX >= x1 && canvasX <= x2) {
                        // Check for edge resize handle (within 6px of edge)
                        let edge = null;
                        if (canvasX - x1 < 8) edge = 'left';
                        else if (x2 - canvasX < 8) edge = 'right';
                        return { type: 'region', track, region, edge };
                    }
                }
                return { type: 'track-body', track };
            }
            y += track.height;
        }

        return { type: 'empty' };
    }

    // ============ EVENTS ============

    setupEvents() {
        if (!this.canvas) return;

        this.canvas.addEventListener('mousedown', e => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', e => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', e => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', e => this.onWheel(e), { passive: false });
        this.canvas.addEventListener('dblclick', e => this.onDblClick(e));

        // Resize observer
        if (this.canvas.parentElement) {
            const ro = new ResizeObserver(() => this.resize());
            ro.observe(this.canvas.parentElement);
        }

        // Global mouseup (in case mouse leaves canvas during drag)
        document.addEventListener('mouseup', e => {
            if (this.isDragging) this.onMouseUp(e);
        });

        document.addEventListener('mousemove', e => {
            if (this.isDragging) this.onMouseMove(e);
        });
    }

    getCanvasPos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    onMouseDown(e) {
        const pos = this.getCanvasPos(e);
        const hit = this.hitTest(pos.x, pos.y);

        if (hit.type === 'ruler') {
            // Click ruler → set playhead
            const frame = this.xToFrame(pos.x);
            this.setPlayhead(Math.max(0, Math.min(frame, this.totalFrames - 1)));
            this.isDragging = true;
            this.dragType = 'playhead';
            return;
        }

        if (hit.type === 'solo-btn') {
            this.toggleTrackSolo(hit.track.id);
            return;
        }

        if (hit.type === 'mute-btn') {
            this.toggleTrackMute(hit.track.id);
            return;
        }

        if (hit.type === 'track-header') {
            this.selectedTrackId = hit.track.id;
            this.draw();
            return;
        }

        if (hit.type === 'region') {
            this.selectedRegionId = hit.region.id;
            this.selectedTrackId = hit.track.id;

            if (hit.edge === 'left') {
                this.isDragging = true;
                this.dragType = 'region-resize-l';
                this.dragTarget = hit.region;
                this.dragOrigStart = hit.region.startFrame;
                this.dragOrigEnd = hit.region.endFrame;
            } else if (hit.edge === 'right') {
                this.isDragging = true;
                this.dragType = 'region-resize-r';
                this.dragTarget = hit.region;
                this.dragOrigStart = hit.region.startFrame;
                this.dragOrigEnd = hit.region.endFrame;
            } else {
                this.isDragging = true;
                this.dragType = 'region-move';
                this.dragTarget = hit.region;
                this.dragStartX = pos.x;
                this.dragStartFrame = this.xToFrame(pos.x);
                this.dragOrigStart = hit.region.startFrame;
                this.dragOrigEnd = hit.region.endFrame;
            }

            this.draw();
            if (typeof onRegionSelect === 'function') {
                onRegionSelect(hit.region);
            }
            return;
        }

        if (hit.type === 'track-body') {
            // Click empty area → move playhead and select track
            this.selectedTrackId = hit.track.id;
            this.selectedRegionId = null;
            const frame = this.xToFrame(pos.x);
            this.setPlayhead(Math.max(0, Math.min(frame, this.totalFrames - 1)));
            this.isDragging = true;
            this.dragType = 'playhead';
            if (typeof onRegionDeselect === 'function') {
                onRegionDeselect();
            }
            return;
        }
    }

    onMouseMove(e) {
        const pos = this.getCanvasPos(e);

        if (this.isDragging) {
            if (this.dragType === 'playhead') {
                const frame = this.xToFrame(pos.x);
                this.setPlayhead(Math.max(0, Math.min(frame, this.totalFrames - 1)));
            } else if (this.dragType === 'region-move') {
                const frameDelta = this.xToFrame(pos.x) - this.dragStartFrame;
                const newStart = Math.max(0, this.dragOrigStart + frameDelta);
                const duration = this.dragOrigEnd - this.dragOrigStart;
                const newEnd = Math.min(this.totalFrames - 1, newStart + duration);
                this.dragTarget.startFrame = newEnd - duration < 0 ? 0 : newEnd - duration;
                this.dragTarget.endFrame = newEnd;
                this.draw();
            } else if (this.dragType === 'region-resize-l') {
                const frame = Math.max(0, this.xToFrame(pos.x));
                this.dragTarget.startFrame = Math.min(frame, this.dragTarget.endFrame - 1);
                this.draw();
            } else if (this.dragType === 'region-resize-r') {
                const frame = Math.min(this.totalFrames - 1, this.xToFrame(pos.x));
                this.dragTarget.endFrame = Math.max(frame, this.dragTarget.startFrame + 1);
                this.draw();
            }
            return;
        }

        // Hover: update cursor based on hit
        const hit = this.hitTest(pos.x, pos.y);
        if (hit.type === 'region' && hit.edge) {
            this.canvas.style.cursor = 'col-resize';
        } else if (hit.type === 'region') {
            this.canvas.style.cursor = 'grab';
        } else if (hit.type === 'ruler') {
            this.canvas.style.cursor = 'pointer';
        } else {
            this.canvas.style.cursor = 'crosshair';
        }
    }

    onMouseUp(e) {
        if (this.isDragging && this.dragType === 'region-move') {
            this.canvas.style.cursor = 'grab';
        }
        this.isDragging = false;
        this.dragType = null;
        this.dragTarget = null;
    }

    onWheel(e) {
        e.preventDefault();

        if (e.ctrlKey || e.metaKey) {
            // Zoom at cursor position
            const pos = this.getCanvasPos(e);
            const frameAtCursor = this.xToFrame(pos.x);
            const oldZoom = this.zoom;

            if (e.deltaY < 0) {
                this.zoom = Math.min(20, this.zoom * 1.15);
            } else {
                this.zoom = Math.max(0.05, this.zoom / 1.15);
            }

            // Keep frame under cursor at same screen position
            this.scrollX += frameAtCursor * (this.zoom - oldZoom);
            this.clampScroll();
        } else {
            // Horizontal scroll
            this.scrollX += e.deltaY * 2;
            this.clampScroll();
        }

        this.draw();
    }

    onDblClick(e) {
        const pos = this.getCanvasPos(e);
        const hit = this.hitTest(pos.x, pos.y);

        if (hit.type === 'track-body') {
            // Double-click empty track → create a small region at click point
            const frame = this.xToFrame(pos.x);
            const halfLen = Math.round(this.fps); // 1 second region
            const start = Math.max(0, frame - halfLen);
            const end = Math.min(this.totalFrames - 1, frame + halfLen);
            const region = new Region(this.nextRegionId++, hit.track.id, start, end);
            hit.track.regions.push(region);
            this.selectedRegionId = region.id;
            this.draw();
            if (typeof onRegionSelect === 'function') {
                onRegionSelect(region);
            }
            if (typeof showToast === 'function') {
                showToast(`Region created: frames ${start}-${end}`, 'success');
            }
        }
    }

    // ============ SERIALIZATION ============

    serialize() {
        return {
            tracks: this.tracks.map(t => ({
                id: t.id,
                name: t.name,
                type: t.type,
                muted: t.muted,
                soloed: t.soloed,
                regions: t.regions.map(r => ({
                    id: r.id,
                    startFrame: r.startFrame,
                    endFrame: r.endFrame,
                    effects: r.effects,
                    label: r.label,
                    color: r.color,
                    mask: r.mask,
                })),
            })),
            playhead: this.playhead,
            inPoint: this.inPoint,
            outPoint: this.outPoint,
            zoom: this.zoom,
            scrollX: this.scrollX,
            selectedRegionId: this.selectedRegionId,
        };
    }

    deserialize(data) {
        if (!data) return;
        this.tracks = (data.tracks || []).map(t => {
            const track = new Track(t.id, t.name, t.type);
            track.muted = t.muted || false;
            track.soloed = t.soloed || false;
            track.regions = (t.regions || []).map(r => {
                const region = new Region(r.id, t.id, r.startFrame, r.endFrame);
                region.effects = r.effects || [];
                region.label = r.label || '';
                region.color = r.color || null;
                region.mask = r.mask || null;
                return region;
            });
            return track;
        });

        // Update ID counters
        this.nextTrackId = Math.max(0, ...this.tracks.map(t => t.id)) + 1;
        let maxRegionId = -1;
        for (const t of this.tracks) {
            for (const r of t.regions) {
                maxRegionId = Math.max(maxRegionId, r.id);
            }
        }
        this.nextRegionId = maxRegionId + 1;

        this.playhead = data.playhead || 0;
        this.inPoint = data.inPoint ?? null;
        this.outPoint = data.outPoint ?? null;
        this.zoom = data.zoom || 2.0;
        this.scrollX = data.scrollX || 0;
        this.selectedRegionId = data.selectedRegionId ?? null;
        this.draw();
    }
}

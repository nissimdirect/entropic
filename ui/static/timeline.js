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

class AutomationLaneUI {
    constructor(id, regionId, effectIndex, paramName, color) {
        this.id = id;
        this.regionId = regionId;
        this.effectIndex = effectIndex;
        this.paramName = paramName;
        this.color = color;
        this.keyframes = [];  // [{frame, value, curve}] — value is 0-1 normalized
        this.height = 60;
        this.visible = true;
        this.selected = false;
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

        // Automation state
        this.automationLanes = [];  // AutomationLaneUI[]
        this.nextLaneId = 0;
        this.automationVisible = true;  // Toggle with 'A' key
        this.selectedLaneId = null;
        this.selectedBreakpoints = [];  // [{laneId, index}]
        this.isDraggingBreakpoint = false;
        this.dragBreakpointLane = null;
        this.dragBreakpointIndex = -1;
        this.drawMode = false;  // pencil mode (for Phase 2c)

        // Automation lane colors (Ableton-inspired)
        this.laneColors = [
            '#ff5555', '#55aaff', '#55ff55', '#ffaa55',
            '#ff55ff', '#55ffff', '#ffff55', '#aa55ff',
            '#ff8888', '#88aaff', '#88ff88', '#ffcc88',
        ];

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

        // Draw automation lanes
        this.drawAutomationLanes();

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

        // Frozen region overlay
        if (region._frozen) {
            ctx.fillStyle = 'rgba(100, 180, 255, 0.15)';
            ctx.fillRect(clampX, ry, clampW, rh);
            // Snowflake icon
            ctx.fillStyle = '#88ccff';
            ctx.font = '12px sans-serif';
            ctx.textBaseline = 'middle';
            ctx.fillText('\u2744', clampX + clampW - 16, ry + rh / 2); // ❄
        }

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

    // ============ AUTOMATION LANES ============

    drawAutomationLanes() {
        if (!this.automationVisible) return;

        for (const lane of this.automationLanes) {
            if (!lane.visible) continue;

            // Find the track that contains the region this lane belongs to
            const track = this.findTrackForRegion(lane.regionId);
            if (!track) continue;

            // Calculate Y position: after the track + any previous lanes
            let laneY = this.getTrackY(track.id) + track.height;
            const lanesForTrack = this.automationLanes.filter(l => {
                const t = this.findTrackForRegion(l.regionId);
                return t && t.id === track.id && l.visible;
            });
            const laneIndex = lanesForTrack.indexOf(lane);
            laneY += laneIndex * lane.height;

            this.drawLane(lane, laneY);
        }
    }

    getTrackY(trackId) {
        let y = this.rulerHeight;
        for (const track of this.tracks) {
            if (track.id === trackId) return y;
            y += track.height;
            // Add automation lane heights
            const trackLanes = this.automationLanes.filter(l => {
                const t = this.findTrackForRegion(l.regionId);
                return t && t.id === track.id && l.visible;
            });
            if (this.automationVisible) {
                y += trackLanes.length * 60;
            }
        }
        return y;
    }

    getTotalHeight() {
        let h = this.rulerHeight;
        for (const track of this.tracks) {
            h += track.height;
            if (this.automationVisible) {
                const trackLanes = this.automationLanes.filter(l => {
                    const t = this.findTrackForRegion(l.regionId);
                    return t && t.id === track.id && l.visible;
                });
                h += trackLanes.length * 60;
            }
        }
        return h;
    }

    drawLane(lane, y) {
        const ctx = this.ctx;
        const w = this.canvasW;
        const h = lane.height;

        // Lane background
        ctx.fillStyle = 'rgba(20, 20, 24, 0.9)';
        ctx.fillRect(this.trackHeaderWidth, y, w - this.trackHeaderWidth, h);

        // Lane header (in track header area)
        ctx.fillStyle = '#1a1a20';
        ctx.fillRect(0, y, this.trackHeaderWidth, h);

        // Lane label
        ctx.fillStyle = lane.color;
        ctx.font = '9px Menlo, Monaco, monospace';
        ctx.textBaseline = 'middle';
        ctx.fillText(lane.paramName, 8, y + h / 2);

        // Color indicator bar
        ctx.fillStyle = lane.color;
        ctx.fillRect(this.trackHeaderWidth - 3, y, 3, h);

        // Value grid lines (0.25, 0.5, 0.75)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        for (const val of [0.25, 0.5, 0.75]) {
            const gy = y + h - val * h;
            ctx.beginPath();
            ctx.moveTo(this.trackHeaderWidth, gy);
            ctx.lineTo(w, gy);
            ctx.stroke();
        }

        // Draw interpolated line between keyframes
        if (lane.keyframes.length > 0) {
            ctx.strokeStyle = lane.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();

            // Draw from left edge to right edge
            const region = this.findRegion(lane.regionId);
            const startFrame = region ? region.startFrame : 0;
            const endFrame = region ? region.endFrame : this.totalFrames;

            // Sample at pixel intervals for efficiency
            const startX = this.frameToX(startFrame);
            const endX = this.frameToX(endFrame);
            let first = true;
            for (let x = Math.max(this.trackHeaderWidth, startX); x <= Math.min(w, endX); x += 2) {
                const f = this.xToFrame(x);
                const val = this.getLaneValue(lane, f);
                if (val === null) continue;
                const py = y + h - val * h;
                if (first) { ctx.moveTo(x, py); first = false; }
                else ctx.lineTo(x, py);
            }
            ctx.stroke();

            // Draw breakpoint dots
            for (let i = 0; i < lane.keyframes.length; i++) {
                const kf = lane.keyframes[i];
                const x = this.frameToX(kf.frame);
                const py = y + h - kf.value * h;

                if (x < this.trackHeaderWidth || x > w) continue;

                const isSelected = this.selectedBreakpoints.some(
                    s => s.laneId === lane.id && s.index === i
                );

                // Dot
                ctx.fillStyle = isSelected ? '#fff' : lane.color;
                ctx.beginPath();
                ctx.arc(x, py, isSelected ? 5 : 4, 0, Math.PI * 2);
                ctx.fill();

                // Border
                ctx.strokeStyle = isSelected ? lane.color : 'rgba(0,0,0,0.5)';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }
        }

        // Bottom border
        ctx.strokeStyle = '#2a2a30';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, y + h);
        ctx.lineTo(w, y + h);
        ctx.stroke();

        // Selected lane highlight
        if (lane.id === this.selectedLaneId) {
            ctx.strokeStyle = lane.color + '44';
            ctx.lineWidth = 2;
            ctx.strokeRect(this.trackHeaderWidth, y, w - this.trackHeaderWidth, h);
        }
    }

    getLaneValue(lane, frame) {
        const kfs = lane.keyframes;
        if (kfs.length === 0) return null;
        if (frame <= kfs[0].frame) return kfs[0].value;
        if (frame >= kfs[kfs.length - 1].frame) return kfs[kfs.length - 1].value;

        for (let i = 0; i < kfs.length - 1; i++) {
            if (kfs[i].frame <= frame && frame <= kfs[i + 1].frame) {
                const t = (frame - kfs[i].frame) / (kfs[i + 1].frame - kfs[i].frame);
                const curve = kfs[i].curve || 'linear';
                return this.interpolate(kfs[i].value, kfs[i + 1].value, t, curve, kfs[i].cp1, kfs[i].cp2);
            }
        }
        return kfs[kfs.length - 1].value;
    }

    interpolate(a, b, t, curve, cp1, cp2) {
        switch (curve) {
            case 'ease_in': return a + (b - a) * t * t;
            case 'ease_out': return a + (b - a) * (1 - (1 - t) ** 2);
            case 'ease_in_out':
                return t < 0.5
                    ? a + (b - a) * 2 * t * t
                    : a + (b - a) * (1 - (-2 * t + 2) ** 2 / 2);
            case 'step': return a;
            case 'sine': return a + (b - a) * (1 - Math.cos(t * Math.PI)) / 2;
            case 'bezier': return this.bezierInterpolate(a, b, t, cp1, cp2);
            default: return a + (b - a) * t; // linear
        }
    }

    bezierInterpolate(a, b, t, cp1, cp2) {
        // Cubic bezier with control points in normalized 0-1 space
        cp1 = cp1 || [0.42, 0.0];
        cp2 = cp2 || [0.58, 1.0];
        // Newton's method to solve for u where B_x(u) = t
        let u = t;
        for (let iter = 0; iter < 8; iter++) {
            const xU = 3 * (1 - u) ** 2 * u * cp1[0] +
                        3 * (1 - u) * u ** 2 * cp2[0] +
                        u ** 3;
            const dx = 3 * (1 - u) ** 2 * cp1[0] +
                       6 * (1 - u) * u * (cp2[0] - cp1[0]) +
                       3 * u ** 2 * (1 - cp2[0]);
            if (Math.abs(dx) < 1e-10) break;
            u = Math.max(0, Math.min(1, u - (xU - t) / dx));
        }
        const y = 3 * (1 - u) ** 2 * u * cp1[1] +
                  3 * (1 - u) * u ** 2 * cp2[1] +
                  u ** 3;
        return a + (b - a) * y;
    }

    // ============ MARQUEE SELECTION ============

    startMarquee(x, y) {
        this.marqueeStart = { x, y };
        this.marqueeEnd = { x, y };
        this.isMarqueeSelecting = true;
    }

    updateMarquee(x, y) {
        this.marqueeEnd = { x, y };
        this.draw();
        // Draw marquee rectangle
        const ctx = this.ctx;
        const mx = Math.min(this.marqueeStart.x, x);
        const my = Math.min(this.marqueeStart.y, y);
        const mw = Math.abs(x - this.marqueeStart.x);
        const mh = Math.abs(y - this.marqueeStart.y);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(mx, my, mw, mh);
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.fillRect(mx, my, mw, mh);
    }

    endMarquee() {
        if (!this.isMarqueeSelecting) return;
        this.isMarqueeSelecting = false;

        const x1 = Math.min(this.marqueeStart.x, this.marqueeEnd.x);
        const x2 = Math.max(this.marqueeStart.x, this.marqueeEnd.x);
        const y1 = Math.min(this.marqueeStart.y, this.marqueeEnd.y);
        const y2 = Math.max(this.marqueeStart.y, this.marqueeEnd.y);

        // Find all breakpoints within the marquee
        this.selectedBreakpoints = [];
        for (const lane of this.automationLanes) {
            if (!lane.visible) continue;
            const track = this.findTrackForRegion(lane.regionId);
            if (!track) continue;

            let laneY = this.getTrackY(track.id) + track.height;
            const trackLanes = this.automationLanes.filter(l => {
                const t = this.findTrackForRegion(l.regionId);
                return t && t.id === track.id && l.visible;
            });
            const laneIdx = trackLanes.indexOf(lane);
            laneY += laneIdx * lane.height;

            for (let i = 0; i < lane.keyframes.length; i++) {
                const kf = lane.keyframes[i];
                const kfX = this.frameToX(kf.frame);
                const kfY = laneY + lane.height - kf.value * lane.height;
                if (kfX >= x1 && kfX <= x2 && kfY >= y1 && kfY <= y2) {
                    this.selectedBreakpoints.push({ laneId: lane.id, index: i });
                }
            }
        }
        this.draw();
    }

    // ============ SHAPES LIBRARY ============

    insertShape(lane, shapeName, startFrame, endFrame, numPoints) {
        numPoints = numPoints || 16;
        const duration = endFrame - startFrame;
        if (duration <= 0) return;

        const newKeyframes = [];
        for (let i = 0; i <= numPoints; i++) {
            const t = i / numPoints;
            const frame = Math.round(startFrame + t * duration);
            let value;

            switch (shapeName) {
                case 'ramp_up':
                    value = t;
                    break;
                case 'ramp_down':
                    value = 1 - t;
                    break;
                case 'sine':
                    value = (Math.sin(t * Math.PI * 2 - Math.PI / 2) + 1) / 2;
                    break;
                case 'triangle':
                    value = t < 0.5 ? t * 2 : 2 - t * 2;
                    break;
                case 'saw':
                    value = t;
                    break;
                case 'square':
                    value = t < 0.5 ? 1 : 0;
                    break;
                case 's_curve':
                    value = t < 0.5 ? 2 * t * t : 1 - 2 * (1 - t) ** 2;
                    break;
                default:
                    value = t;
            }

            newKeyframes.push({ frame, value: Math.max(0, Math.min(1, value)), curve: 'linear' });
        }

        // Replace keyframes in the range, preserve outside
        lane.keyframes = lane.keyframes.filter(kf => kf.frame < startFrame || kf.frame > endFrame);
        lane.keyframes.push(...newKeyframes);
        lane.keyframes.sort((a, b) => a.frame - b.frame);
        this.draw();
    }

    // ============ COPY / PASTE ============

    copySelectedBreakpoints() {
        if (this.selectedBreakpoints.length === 0) return;
        // Find the earliest frame to use as offset reference
        let minFrame = Infinity;
        const copied = [];
        for (const sel of this.selectedBreakpoints) {
            const lane = this.automationLanes.find(l => l.id === sel.laneId);
            if (!lane) continue;
            const kf = lane.keyframes[sel.index];
            if (!kf) continue;
            if (kf.frame < minFrame) minFrame = kf.frame;
            copied.push({ laneId: sel.laneId, frame: kf.frame, value: kf.value, curve: kf.curve || 'linear' });
        }
        // Normalize to relative offsets
        this.clipboard = copied.map(c => ({
            frameOffset: c.frame - minFrame,
            value: c.value,
            curve: c.curve,
            laneId: c.laneId,
        }));
        if (typeof showToast === 'function') {
            showToast(`Copied ${this.clipboard.length} breakpoints`, 'info');
        }
    }

    pasteBreakpoints() {
        if (!this.clipboard || this.clipboard.length === 0) return;
        const pasteFrame = this.playhead;
        // If pasting to the same lane or the selected lane
        const targetLaneId = this.selectedLaneId;
        const targetLane = this.automationLanes.find(l => l.id === targetLaneId);

        for (const item of this.clipboard) {
            const frame = pasteFrame + item.frameOffset;
            // Paste to original lane or target lane (cross-lane paste)
            const lane = targetLane || this.automationLanes.find(l => l.id === item.laneId);
            if (!lane) continue;
            lane.keyframes.push({
                frame,
                value: item.value,
                curve: item.curve,
            });
            lane.keyframes.sort((a, b) => a.frame - b.frame);
        }
        this.draw();
        if (typeof showToast === 'function') {
            showToast(`Pasted ${this.clipboard.length} breakpoints at frame ${pasteFrame}`, 'info');
        }
    }

    // ============ DRAW MODE (PENCIL) ============

    toggleDrawMode() {
        this.drawMode = !this.drawMode;
        this.canvas.style.cursor = this.drawMode ? 'cell' : 'crosshair';
        if (typeof showToast === 'function') {
            showToast(this.drawMode ? 'Draw mode ON' : 'Draw mode OFF', 'info');
        }
    }

    drawModeStroke(lane, laneY, startX, endX, y) {
        // Grid-quantized step automation
        const gridSize = this.getDrawGridSize();
        const startFrame = this.xToFrame(Math.min(startX, endX));
        const endFrame = this.xToFrame(Math.max(startX, endX));

        for (let f = startFrame; f <= endFrame; f += gridSize) {
            const value = Math.max(0, Math.min(1, (laneY + lane.height - y) / lane.height));
            const existing = lane.keyframes.findIndex(kf => kf.frame === f);
            if (existing >= 0) {
                lane.keyframes[existing].value = value;
            } else {
                lane.keyframes.push({ frame: f, value, curve: 'step' });
            }
        }
        lane.keyframes.sort((a, b) => a.frame - b.frame);
        this.draw();
    }

    getDrawGridSize() {
        // Adaptive grid: fewer points when zoomed out, more when zoomed in
        if (this.zoom > 8) return 1;
        if (this.zoom > 4) return 5;
        if (this.zoom > 1) return 10;
        return 30;
    }

    // ============ SIMPLIFY (RDP) ============

    simplifyLane(laneId, tolerance) {
        tolerance = tolerance || 0.02;
        const lane = this.automationLanes.find(l => l.id === laneId);
        if (!lane || lane.keyframes.length <= 2) return;

        const simplified = this._rdpSimplify(lane.keyframes, tolerance);
        const removed = lane.keyframes.length - simplified.length;
        lane.keyframes = simplified;
        this.draw();
        if (typeof showToast === 'function' && removed > 0) {
            showToast(`Simplified: removed ${removed} points`, 'info');
        }
    }

    _rdpSimplify(keyframes, tolerance) {
        if (keyframes.length <= 2) return keyframes;

        const first = keyframes[0];
        const last = keyframes[keyframes.length - 1];
        let maxDist = 0;
        let maxIdx = 0;

        for (let i = 1; i < keyframes.length - 1; i++) {
            const kf = keyframes[i];
            const t = last.frame === first.frame ? 0 : (kf.frame - first.frame) / (last.frame - first.frame);
            const expected = first.value + t * (last.value - first.value);
            const dist = Math.abs(kf.value - expected);
            if (dist > maxDist) {
                maxDist = dist;
                maxIdx = i;
            }
        }

        if (maxDist > tolerance) {
            const left = this._rdpSimplify(keyframes.slice(0, maxIdx + 1), tolerance);
            const right = this._rdpSimplify(keyframes.slice(maxIdx), tolerance);
            return left.slice(0, -1).concat(right);
        }
        return [first, last];
    }

    // ============ LANE CONTEXT MENU ============

    showLaneContextMenu(e, lane) {
        e.preventDefault();
        const region = this.findRegion(lane.regionId);
        const startFrame = region ? region.startFrame : 0;
        const endFrame = region ? region.endFrame : this.totalFrames;

        // Determine selection range for shape insertion
        const selFrames = this.selectedBreakpoints
            .filter(s => s.laneId === lane.id)
            .map(s => lane.keyframes[s.index]?.frame)
            .filter(f => f !== undefined);
        const shapeStart = selFrames.length > 0 ? Math.min(...selFrames) : startFrame;
        const shapeEnd = selFrames.length > 0 ? Math.max(...selFrames) : endFrame;

        if (typeof showContextMenu === 'function') {
            window._laneCtxData = { lane, shapeStart, shapeEnd };
            showContextMenu(e, [
                { label: 'Insert: Ramp Up', action: 'shape_ramp_up' },
                { label: 'Insert: Ramp Down', action: 'shape_ramp_down' },
                { label: 'Insert: Sine', action: 'shape_sine' },
                { label: 'Insert: Triangle', action: 'shape_triangle' },
                { label: 'Insert: Saw', action: 'shape_saw' },
                { label: 'Insert: Square', action: 'shape_square' },
                { label: 'Insert: S-Curve', action: 'shape_s_curve' },
                '---',
                { label: 'Simplify', action: 'simplifyLane' },
                { label: 'Flatten to Static', action: 'flattenLaneToStatic' },
                '---',
                { label: 'Delete Lane', action: 'deleteLane', danger: true },
            ]);
        }
    }

    addAutomationLane(regionId, effectIndex, paramName) {
        const color = this.laneColors[this.automationLanes.length % this.laneColors.length];
        const lane = new AutomationLaneUI(this.nextLaneId++, regionId, effectIndex, paramName, color);
        this.automationLanes.push(lane);
        this.draw();
        return lane;
    }

    removeAutomationLane(laneId) {
        this.automationLanes = this.automationLanes.filter(l => l.id !== laneId);
        if (this.selectedLaneId === laneId) this.selectedLaneId = null;
        this.draw();
    }

    toggleAutomationVisibility() {
        this.automationVisible = !this.automationVisible;
        this.draw();
    }

    getAutomationSessionData() {
        // Convert UI lanes to {lanes: [{effect_idx, param, keyframes: [[frame, value]], curve}, ...]}
        return {
            lanes: this.automationLanes.filter(l => l.keyframes.length > 0).map(l => ({
                effect_idx: l.effectIndex,
                param: l.paramName,
                keyframes: l.keyframes.map(kf => [kf.frame, kf.value]),
                curve: l.keyframes[0]?.curve || 'linear',
            }))
        };
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
        // Kick off pre-cache for upcoming frames
        if (typeof prefetchFrames === 'function') {
            prefetchFrames(this.playhead);
        }
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
        // Free cached frames
        if (typeof clearFrameCache === 'function') {
            clearFrameCache();
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
        // Returns: { type: 'ruler'|'track-header'|'region'|'lane-header'|'lane-body'|'breakpoint'|'lane-line'|'empty', ...}

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

                // Check automation lane headers
                if (this.automationVisible) {
                    const trackLanes = this.automationLanes.filter(l => {
                        const t = this.findTrackForRegion(l.regionId);
                        return t && t.id === track.id && l.visible;
                    });
                    for (const lane of trackLanes) {
                        if (canvasY >= y && canvasY < y + lane.height) {
                            return { type: 'lane-header', lane };
                        }
                        y += lane.height;
                    }
                }
            }
            return { type: 'empty' };
        }

        // Timeline area — check automation lanes first (they overlay tracks)
        if (this.automationVisible) {
            let y = this.rulerHeight;
            for (const track of this.tracks) {
                y += track.height;

                const trackLanes = this.automationLanes.filter(l => {
                    const t = this.findTrackForRegion(l.regionId);
                    return t && t.id === track.id && l.visible;
                });

                for (const lane of trackLanes) {
                    if (canvasY >= y && canvasY < y + lane.height) {
                        // Check for breakpoint click (within 6px)
                        for (let i = 0; i < lane.keyframes.length; i++) {
                            const kf = lane.keyframes[i];
                            const kfX = this.frameToX(kf.frame);
                            const kfY = y + lane.height - kf.value * lane.height;
                            const dist = Math.sqrt((canvasX - kfX) ** 2 + (canvasY - kfY) ** 2);
                            if (dist <= 6) {
                                return { type: 'breakpoint', lane, index: i, laneY: y };
                            }
                        }

                        // Check if clicking on the interpolated line (within 4px)
                        if (lane.keyframes.length > 0) {
                            const frame = this.xToFrame(canvasX);
                            const val = this.getLaneValue(lane, frame);
                            if (val !== null) {
                                const lineY = y + lane.height - val * lane.height;
                                if (Math.abs(canvasY - lineY) <= 4) {
                                    return { type: 'lane-line', lane, frame, value: val, laneY: y };
                                }
                            }
                        }

                        return { type: 'lane-body', lane, laneY: y };
                    }
                    y += lane.height;
                }
            }
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

            // Skip automation lanes in Y calculation
            if (this.automationVisible) {
                const trackLanes = this.automationLanes.filter(l => {
                    const t = this.findTrackForRegion(l.regionId);
                    return t && t.id === track.id && l.visible;
                });
                y += trackLanes.length * 60;
            }
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

        // Keyboard shortcuts
        document.addEventListener('keydown', e => {
            const isTyping = document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'SELECT';
            if (isTyping) return;

            if ((e.key === 'a' || e.key === 'A') && !e.ctrlKey && !e.metaKey && !e.altKey) {
                this.toggleAutomationVisibility();
            }
            // Cmd/Ctrl+C = copy breakpoints
            if ((e.metaKey || e.ctrlKey) && e.key === 'c' && this.selectedBreakpoints.length > 0) {
                e.preventDefault();
                this.copySelectedBreakpoints();
            }
            // Cmd/Ctrl+V = paste breakpoints
            if ((e.metaKey || e.ctrlKey) && e.key === 'v' && this.clipboard?.length > 0) {
                e.preventDefault();
                this.pasteBreakpoints();
            }
            // B = toggle draw mode
            if (e.key === 'b' || e.key === 'B') {
                this.toggleDrawMode();
            }
            // Delete/Backspace = delete selected breakpoints
            if ((e.key === 'Delete' || e.key === 'Backspace') && this.selectedBreakpoints.length > 0) {
                e.preventDefault();
                // Delete in reverse order to preserve indices
                const sorted = [...this.selectedBreakpoints].sort((a, b) => b.index - a.index);
                for (const sel of sorted) {
                    const lane = this.automationLanes.find(l => l.id === sel.laneId);
                    if (lane) lane.keyframes.splice(sel.index, 1);
                }
                this.selectedBreakpoints = [];
                this.draw();
            }
        });
    }

    getCanvasPos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    onMouseDown(e) {
        const pos = this.getCanvasPos(e);
        const hit = this.hitTest(pos.x, pos.y);

        // Right-click on region → show context menu (handled in app.js)
        if (e.button === 2 && hit.type === 'region') {
            this.selectedRegionId = hit.region.id;
            this.selectedTrackId = hit.track.id;
            this.draw();
            if (typeof onRegionRightClick === 'function') {
                onRegionRightClick(e, hit.region);
            }
            return;
        }

        // Right-click on breakpoint → delete it
        if (e.button === 2 && hit.type === 'breakpoint') {
            hit.lane.keyframes.splice(hit.index, 1);
            this.draw();
            return;
        }

        // Right-click on lane → show shapes/simplify context menu
        if (e.button === 2 && (hit.type === 'lane-body' || hit.type === 'lane-header' || hit.type === 'lane-line')) {
            this.showLaneContextMenu(e, hit.lane);
            return;
        }

        // Draw mode: click-drag in lane creates step automation
        if (this.drawMode && hit.type === 'lane-body') {
            this.isDragging = true;
            this.dragType = 'draw';
            this.dragBreakpointLane = hit.lane;
            this.dragLaneY = hit.laneY;
            this.dragStartX = pos.x;
            // Add first point
            const frame = this.xToFrame(pos.x);
            const value = Math.max(0, Math.min(1, (hit.laneY + hit.lane.height - pos.y) / hit.lane.height));
            hit.lane.keyframes.push({ frame, value, curve: 'step' });
            hit.lane.keyframes.sort((a, b) => a.frame - b.frame);
            this.draw();
            return;
        }

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

        if (hit.type === 'lane-header') {
            this.selectedLaneId = hit.lane.id;
            this.draw();
            return;
        }

        if (hit.type === 'breakpoint') {
            // Start dragging breakpoint
            this.selectedLaneId = hit.lane.id;
            if (!e.shiftKey) {
                this.selectedBreakpoints = [{ laneId: hit.lane.id, index: hit.index }];
            } else {
                // Shift+click to add to selection
                const exists = this.selectedBreakpoints.some(
                    s => s.laneId === hit.lane.id && s.index === hit.index
                );
                if (!exists) {
                    this.selectedBreakpoints.push({ laneId: hit.lane.id, index: hit.index });
                }
            }
            this.isDragging = true;
            this.dragType = 'breakpoint';
            this.dragBreakpointLane = hit.lane;
            this.dragBreakpointIndex = hit.index;
            this.dragStartX = pos.x;
            this.dragStartY = pos.y;
            this.dragOrigBreakpoint = { ...hit.lane.keyframes[hit.index] };
            this.dragLaneY = hit.laneY;
            this.draw();
            return;
        }

        if (hit.type === 'lane-line') {
            // Click on interpolated line → insert new breakpoint
            const newKf = { frame: hit.frame, value: hit.value, curve: 'linear' };
            hit.lane.keyframes.push(newKf);
            hit.lane.keyframes.sort((a, b) => a.frame - b.frame);
            const newIndex = hit.lane.keyframes.indexOf(newKf);
            this.selectedLaneId = hit.lane.id;
            this.selectedBreakpoints = [{ laneId: hit.lane.id, index: newIndex }];
            this.isDragging = true;
            this.dragType = 'breakpoint';
            this.dragBreakpointLane = hit.lane;
            this.dragBreakpointIndex = newIndex;
            this.dragStartX = pos.x;
            this.dragStartY = pos.y;
            this.dragOrigBreakpoint = { ...newKf };
            this.dragLaneY = hit.laneY;
            this.draw();
            return;
        }

        if (hit.type === 'lane-body') {
            // Double-click handled separately; single click selects lane
            this.selectedLaneId = hit.lane.id;
            this.selectedBreakpoints = [];
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
            } else if (this.dragType === 'breakpoint') {
                // Drag breakpoint: X maps to frame, Y maps to 0-1 value
                const lane = this.dragBreakpointLane;
                const kf = lane.keyframes[this.dragBreakpointIndex];
                if (!kf) return;

                // Frame (with snap to playhead if close)
                let newFrame = this.xToFrame(pos.x);
                const playheadDist = Math.abs(pos.x - this.frameToX(this.playhead));
                if (playheadDist < 8) {
                    newFrame = this.playhead; // Snap to playhead
                }
                newFrame = Math.max(0, Math.min(this.totalFrames - 1, newFrame));
                kf.frame = newFrame;

                // Value (inverted Y, with shift for fine control)
                const deltaY = pos.y - this.dragStartY;
                const precision = e.shiftKey ? 4 : 1; // Shift = 4x finer
                const valueDelta = (-deltaY / (lane.height * precision));
                let newValue = this.dragOrigBreakpoint.value + valueDelta;
                newValue = Math.max(0, Math.min(1, newValue));
                kf.value = newValue;

                // Re-sort keyframes by frame
                lane.keyframes.sort((a, b) => a.frame - b.frame);
                // Update index in selection
                this.dragBreakpointIndex = lane.keyframes.indexOf(kf);
                this.selectedBreakpoints = [{ laneId: lane.id, index: this.dragBreakpointIndex }];

                this.draw();
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
            } else if (this.dragType === 'draw') {
                // Draw mode: add points as mouse moves
                this.drawModeStroke(
                    this.dragBreakpointLane,
                    this.dragLaneY,
                    this.dragStartX, pos.x, pos.y
                );
                this.dragStartX = pos.x;
            } else if (this.dragType === 'region-resize-r') {
                const frame = Math.min(this.totalFrames - 1, this.xToFrame(pos.x));
                this.dragTarget.endFrame = Math.max(frame, this.dragTarget.startFrame + 1);
                this.draw();
            }
            return;
        }

        // Hover: update cursor based on hit
        const hit = this.hitTest(pos.x, pos.y);
        if (hit.type === 'breakpoint') {
            this.canvas.style.cursor = 'pointer';
        } else if (hit.type === 'lane-line') {
            this.canvas.style.cursor = 'cell';
        } else if (hit.type === 'lane-body' || hit.type === 'lane-header') {
            this.canvas.style.cursor = 'default';
        } else if (hit.type === 'region' && hit.edge) {
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

        if (hit.type === 'lane-body') {
            // Double-click empty lane area → insert breakpoint
            const frame = this.xToFrame(pos.x);
            const valueY = (hit.laneY + hit.lane.height - pos.y) / hit.lane.height;
            const value = Math.max(0, Math.min(1, valueY));
            const newKf = { frame, value, curve: 'linear' };
            hit.lane.keyframes.push(newKf);
            hit.lane.keyframes.sort((a, b) => a.frame - b.frame);
            const newIndex = hit.lane.keyframes.indexOf(newKf);
            this.selectedLaneId = hit.lane.id;
            this.selectedBreakpoints = [{ laneId: hit.lane.id, index: newIndex }];
            this.draw();
            return;
        }

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
            automationLanes: this.automationLanes.map(l => ({
                id: l.id,
                regionId: l.regionId,
                effectIndex: l.effectIndex,
                paramName: l.paramName,
                color: l.color,
                keyframes: l.keyframes,
                visible: l.visible,
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

        // Restore automation lanes
        this.automationLanes = (data.automationLanes || []).map(l => {
            const lane = new AutomationLaneUI(l.id, l.regionId, l.effectIndex, l.paramName, l.color);
            lane.keyframes = l.keyframes || [];
            lane.visible = l.visible ?? true;
            return lane;
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
        this.nextLaneId = this.automationLanes.length > 0
            ? Math.max(...this.automationLanes.map(l => l.id)) + 1
            : 0;

        this.playhead = data.playhead || 0;
        this.inPoint = data.inPoint ?? null;
        this.outPoint = data.outPoint ?? null;
        this.zoom = data.zoom || 2.0;
        this.scrollX = data.scrollX || 0;
        this.selectedRegionId = data.selectedRegionId ?? null;
        this.draw();
    }
}

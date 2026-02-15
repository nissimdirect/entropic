// TOOLTIP PATCH for app.js
// Add these lines to the three parameter creation functions:

// ===== IN createKnob() function (around line 1254) =====
// AFTER: const displayVal = typeof value === 'number'...
// ADD:
const tooltip = `${label}: ${displayVal} (range: ${spec.min}–${spec.max})`;

// CHANGE: <div class="knob-container">
// TO: <div class="knob-container" title="${tooltip}">


// ===== IN createDropdown() function (around line 1182) =====
// BEFORE: return `
// ADD:
const tooltip = `${label}: ${value} (${options.length} options)`;

// CHANGE: <div class="param-control dropdown-container">
// TO: <div class="param-control dropdown-container" title="${tooltip}">


// ===== IN createToggle() function (around line 1193) =====
// AFTER: const checked = value ? 'checked' : '';
// ADD:
const tooltip = `${label}: ${value ? 'ON' : 'OFF'} (click to toggle)`;

// CHANGE: <div class="param-control toggle-container">
// TO: <div class="param-control toggle-container" title="${tooltip}">

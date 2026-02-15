# Review Mode Test Plan

## Overview
Review Mode allows users to play back their recorded performance with visual feedback showing when layers were triggered. This is task #9 from the perform mode plan.

## What Was Built

### 1. Review Mode State
- Added `perfReviewing` flag to track review playback mode
- Added `perfReviewFrameMap` to store frame->events mapping for playback

### 2. Review Button in Toast
When recording stops (press R a second time), three toasts appear:
1. "Recording stopped: X events" with Save button
2. "Review your performance" with **Review button** (NEW)
3. "Or discard this take" with Discard button

### 3. Review Playback Logic
**`perfReviewStart()`**
- Builds frame->events map from recorded perfSession data
- Resets playback to frame 0
- Sets perfReviewing flag
- Renders event density timeline
- Starts playback loop

**Modified `perfLoop()`**
- When perfReviewing is true, reads events from perfReviewFrameMap instead of perfTriggerQueue
- Converts recorded events (active/opacity parameters) to trigger events (on/off/opacity)
- Sends to server for identical ADSR processing as live performance
- Updates event density timeline position each frame

### 4. Event Density Timeline
**Visual representation below the transport scrubber:**
- Canvas element (20px height)
- Horizontal bar showing event density across time
- Color intensity = number of events in that time slice
- White vertical line shows current playback position
- Fades in during review (opacity transition)

### 5. UI Feedback
- HUD shows `[REVIEW]` instead of `[REC]` or `[BUF]`
- Keyboard input (keys 1-4, R) blocked during review
- Channel strips show layer activity as events play back
- Visual sync matches original performance

## Test Cases

### TC-1: Start Review
**Setup:** Record a performance with at least 10 events using keys 1-4
**Steps:**
1. Press R to start recording
2. Trigger layers 1-4 in various patterns (toggle, gate, etc.)
3. Press R to stop recording
4. Click "Review" button in toast

**Expected:**
- Playback starts from frame 0
- Event density timeline appears below scrubber
- HUD shows `[REVIEW]`
- Layers trigger automatically as recorded
- Channel strips light up in sync with triggers

### TC-2: Event Density Visualization
**Setup:** Review mode active
**Steps:**
1. Observe the event density timeline

**Expected:**
- Timeline shows orange bars where events occurred
- Bar height/intensity represents event density
- White vertical line moves with playback
- Timeline width matches scrubber width

### TC-3: Keyboard Blocked During Review
**Setup:** Review mode active
**Steps:**
1. Press keys 1-4 during review playback
2. Press R during review playback

**Expected:**
- Layer triggers do NOT respond to keyboard
- Recording does NOT start
- Playback continues uninterrupted

### TC-4: Review Looping
**Setup:** Loop mode ON, review active
**Steps:**
1. Let review playback reach end of video

**Expected:**
- Playback loops back to frame 0
- Review continues (does not stop)
- Event density timeline updates

### TC-5: Stop Review
**Setup:** Review mode active
**Steps:**
1. Press Space to stop playback (or let it finish with loop OFF)

**Expected:**
- perfReviewing flag clears
- Event density timeline fades out (data-active="false")
- HUD returns to `[BUF]`
- Keyboard input enabled again

### TC-6: Review with No Events
**Setup:** Empty performance buffer
**Steps:**
1. Don't record anything
2. Try to start review (if UI allows)

**Expected:**
- Toast: "No performance to review"
- Review mode does not start

### TC-7: Multiple Reviews
**Setup:** Recorded performance
**Steps:**
1. Click Review button
2. Let playback complete (or stop it)
3. Click Review button again

**Expected:**
- Event density timeline rebuilds correctly
- Frame map is accurate on second playback
- No memory leaks or stale data

### TC-8: Review Then Discard
**Setup:** Review mode active
**Steps:**
1. Stop review playback
2. Click Discard button

**Expected:**
- Performance buffer clears
- Event count goes to 0
- Review button no longer appears (no events to review)

### TC-9: Save After Review
**Setup:** Review mode completed
**Steps:**
1. Review performance
2. Stop playback
3. Click Save button

**Expected:**
- Performance saves to JSON correctly
- Saved file contains original perfSession data (not modified by review)

## Files Modified

### `/Users/nissimagent/Development/entropic/ui/static/app.js`
- Line 158: Added `perfReviewing` state flag
- Line 165: Added `perfReviewFrameMap` for event mapping
- Lines 636-656: Block keyboard input during review
- Line 796: Block keyup events during review
- Lines 2657-2668: Clear review state in perfStop()
- Lines 2698-2732: Modified perfLoop() to handle review playback
- Line 2824: Update HUD to show `[REVIEW]`
- Line 2862: Added Review button to toast
- Lines 3022-3054: `perfReviewStart()` function
- Lines 3055-3063: `perfReviewStop()` function
- Lines 3065-3115: `perfRenderEventDensity()` function
- Lines 3117-3139: `perfUpdateEventDensityPosition()` function

### `/Users/nissimagent/Development/entropic/ui/static/style.css`
- Lines 1481-1484: Updated #perf-scrubber to flex column layout
- Lines 1505-1519: Event density timeline styles

## Edge Cases

1. **Large event count (10K+ events):** Frame map generation should be fast enough
2. **Long video (1000+ frames):** Event density buckets scale correctly
3. **Review during server disconnect:** Should pause like normal playback
4. **Canvas resize:** Timeline width should adapt to scrubber width

## Performance Notes

- Frame map is built once at review start (not per-frame)
- Event density canvas redraws each frame during review (acceptable at 15 FPS)
- No memory leaks: review state clears on stop

## Future Enhancements

- Click timeline to jump to that frame
- Zoom into timeline for detailed event view
- Color-code events by layer
- Export review visualization as image

## Completion Checklist

- [x] Review mode state variables added
- [x] Review button in toast when recording stops
- [x] perfReviewStart() builds frame map and starts playback
- [x] perfLoop() modified to handle review mode events
- [x] Event density timeline renders and updates
- [x] Keyboard input blocked during review
- [x] HUD shows [REVIEW] indicator
- [x] JavaScript syntax verified (node -c)
- [x] CSS styles for timeline added
- [x] perfStop() clears review state

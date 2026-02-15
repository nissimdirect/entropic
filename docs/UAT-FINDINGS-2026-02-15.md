# Entropic UAT Findings — 2026-02-15

> **Tester:** nissimdirect
> **Session:** Live UAT walkthrough of web UI (Quick mode, all effects)
> **Video:** Uploaded via drag-and-drop to localhost:7860

---

## CRITICAL BUGS (Blocking)

| # | Bug | Severity | Details |
|---|-----|----------|---------|
| B1 | **File upload not populating** | CRITICAL | Dropped file onto UI, nothing happened. Video didn't load into canvas, timeline, or perform mode. |
| B2 | **Datamosh not rendering** | CRITICAL | Primary feature. Does nothing in web UI. Real datamosh also fails. |
| B3 | **Pixel gravity not working** | HIGH | No visible effect when applied. |
| B4 | **Pixel haunt not working** | HIGH | No visible effect. |
| B5 | **Pixel ink drop not working** | HIGH | No visible effect. |
| B6 | **Pixel liquify not working** | HIGH | No visible effect. |
| B7 | **Pixel melt not working** | HIGH | No visible effect. |
| B8 | **Pixel time warp not working** | HIGH | No visible effect. |
| B9 | **Pixel vortex not working** | HIGH | No visible effect. |
| B10 | **Byte corrupt not doing anything** | HIGH | No visible change on any param setting. |
| B11 | **Flow distort not doing anything** | HIGH | No visible change. |
| B12 | **Auto levels no effect** | MEDIUM | No visible change when applied. |
| B13 | **Histogram EQ no effect** | MEDIUM | No visualizer, no visible change. |
| B14 | **Sidechain crossfeed not mapped** | HIGH | Not connected to any output parameter. Major design flaw — effect does nothing. |

---

## PARAMETER BUGS

| # | Bug | Effect | Details |
|---|-----|--------|---------|
| P1 | **Seed does nothing** | Many effects | Seed parameter exposed but changing it produces no visual diff. Affects: pixel magnetic, channel destroy, data bend, and others. Need systematic audit. |
| P2 | **Pixel magnetic — poles don't work** | pixelmagnetic | Adding more poles doesn't increase complexity. Only moves toward center. Damping, Rotation, Seed all non-functional. Only one field type works. |
| P3 | **Pixel quantum — params dead** | pixelquantum | Uncertainty, superposition, decoherence sliders don't affect output. |
| P4 | **Pixel elastic — high mass breaks it** | pixelelastic | Works at low mass, does nothing at high mass. Parameter range needs recalibration. |
| P5 | **Duotone doesn't revert** | duotone | Move params → colors change. Move params back → colors STICK. Must delete and re-add to reset. |
| P6 | **Scanlines flickr crashes render** | scanlines | Moving flickr param past a threshold stops rendering. Can't recover — must delete effect and re-add. |
| P7 | **Brailleart shows question marks** | brailleart | Output is just a block of `?` characters. Likely font/encoding issue. |

---

## UX / DESIGN BUGS

| # | Bug | Details |
|---|-----|---------|
| U1 | **Scrollable parameter panels — HIDDEN PARAMS** | Parameter panels scroll vertically. User had NO IDEA you could scroll down. Missed parameters for many effects. **Major human error.** Horizontal strip expectation — nobody will scroll. Needs complete redesign. |
| U2 | **History order inverted** | Most recent should be at TOP (scroll down for older). Currently oldest at top. |
| U3 | **Mix slider purpose unclear** | "What is this mix slider on top? I don't know what that means." Needs label/tooltip explaining dry/wet. |

---

## PARAMETER SENSITIVITY PROBLEM (Systemic)

> **Pattern observed across MANY effects:** There's a narrow "sweet spot" where parameters do something useful. Below it = nothing visible. Above it = completely blown out (white/black). Most of the parameter range is wasted.
>
> **Affected effects:** edges, smear, decay parameters broadly, pixel elastic (mass), contrast, and others.
>
> **Proposed solutions:**
> 1. **Parameter histogram/diagnostic** — Show a visual indicator of where the "active zone" is for each parameter
> 2. **Non-linear parameter scaling** — Zoom into the resonance peak. Make the slider more sensitive in the useful range
> 3. **Frame diff tool** — Change a parameter, see what pixels actually changed. If seed changes and nothing changes on screen → bug
> 4. **Parameter range recalibration** — For each effect, find the useful range and make that the full slider width

---

## ARCHITECTURE FEEDBACK (Major)

### A1. Performance Mode Should Be a Timeline Layer, Not a Separate Mode

> "Performance mode should be an automation layer on top of the timeline, with just additional tools being shown at the bottom, like we're combining Premiere and Ableton. It's not like a completely different mode."

**Current:** Quick | Timeline | Perform are three separate modes.
**Desired:** Timeline is the main view. Performance tools (mixer, triggers, transport) appear as an additional panel BELOW the timeline when activated. Automation lanes sit ON the timeline tracks.

### A2. Quick Mode Purpose Unclear

> "I also don't know what the purpose of Quick mode is."

**Decision needed:** Is Quick mode necessary? Could it be replaced by Timeline mode with a single full-length region? Or is it a simplified "one-shot preview" mode for beginners?

### A3. Effects vs Tools vs Operators — Need Taxonomy

> "Those shouldn't be effects. Those should be part of the toolbar."

**Proposed categories:**

| Category | What goes here | UI treatment |
|----------|---------------|-------------|
| **Effects** | Glitch, destruction, physics, pixel art, ASCII | Effect rack / chain |
| **Tools** | Color correction, grading, brightness, contrast, hue, saturation | Photoshop-style toolbar with histogram, pop-out panels |
| **Operators** | LFO, flanger, phaser, gate, envelope, sidechain | Mappable modulators (like Ableton Max for Live). Connect to any parameter on any effect. |
| **Image Editing** | Crop, transform, mask, selection | Photoshop-style direct manipulation |

**Effects that should become Tools:**
- hueshift → color tool
- contrast → color tool (needs histogram like Photoshop)
- saturation → color tool
- exposure → color tool
- temperature → color tool
- cyanotype → color filter preset
- infrared → color filter preset
- tapesaturation → color tool (currently "just makes it more white")

**Effects that should become Operators:**
- LFO → mappable to any parameter on any effect
- Flanger/Phaser → operator with source selection
- Gate → operator (currently cool but should be mappable)
- Ring mod → operator (currently "just black stripes")
- Sidechain → modular operator, not per-use-case presets

### A4. Sidechain Must Be Modular

> "We should make it modular. The sidechain crossfeed doesn't do anything because it's not mapped to any output parameter."

**Current:** 6 separate sidechain effects, each hardcoded to specific behavior.
**Desired:** One sidechain operator that you connect to any parameter. The current 6 become presets.

### A5. LFO Must Be Mappable

> "I see there is an LFO, but I can't map it to anything else. I want to be able to hook it up to other effects."

**Desired:** LFO as a modulation source. Click LFO → click any parameter knob on any effect → LFO modulates that parameter. Set min/max range. Like Ableton's macro mapping.

### A6. Pixel Physics Effects Are Redundant — Consider Consolidation

> "Maybe we should group together some of these pixel ones into bigger plugins that have different modes, because it seems like they're all kind of doing similar things."

**Current:** 16 separate pixel physics effects.
**Proposed:** Consolidate into fewer, more powerful effects with mode selectors:
- **Pixel Dynamics** (liquify, gravity, vortex, explode, elastic, melt) → one effect, 6 modes
- **Pixel Cosmos** (black hole, antigravity, magnetic, dimension fold, wormhole, quantum, dark energy, superfluid) → one effect, 8 modes
- **Pixel Organic** (ink drop, haunt, bubbles) → one effect, 3 modes

Each consolidated effect gets:
- Mode selector dropdown
- Force type / vector controls
- Concentration / position controls
- Physics model selector (physical vs non-physical)

### A7. Color Tools Must Match Photoshop/Premiere

> "Truly, it needs to be as good as Photoshop or Premiere, or any of the free image editing software. We need to copy what competitors do."

**Action:** Research and spec out what Photoshop, Premiere, DaVinci Resolve, and GIMP offer for:
- Levels (black/gray/white histogram)
- Curves
- Hue/Saturation
- Color Balance
- Brightness/Contrast (with histogram)
- Selective Color
- Channel Mixer

---

## FEATURE REQUESTS

### Effects — Enhancements

| # | Effect | Request |
|---|--------|---------|
| F1 | **Smear** | Add more directions. Add motion (watch things smear in real-time, shift vectors). |
| F2 | **Wave** | More directions. Modulate amplitude AND frequency (bouncing wave). Min/max parameter controls. |
| F3 | **ASCII art** | Expand character set to ALL ASCII modes. Expand color modes. "ASCII art is INSANE!" |
| F4 | **Blur** | Add more types: Gaussian, radial, motion, lens, etc. Great utility — interference patterns when before pixel sort. |
| F5 | **Contours** | Option to contour outlines ONLY without affecting interior color. Currently dims palette to earth tones. Isolate topography overlay. |
| F6 | **Edges** | Control color palette. Fix threshold sensitivity (blown out → nothing). |
| F7 | **Noise** | Motion in the seed (animated noise). Before pixel sort = animated texture behind sorting. |
| F8 | **TV static** | Concentrations in certain areas. Physics model/gravity. Motion/displacement for active TV feel. |
| F9 | **Contrast** | Needs histogram like Photoshop. Currently oversimplified. |
| F10 | **Pixel elastic** | More force types, concentrations, vectors. Less atmospheric, more punchy. Currently tiles/fluidizes everything. |
| F11 | **Pixel wormhole** | Position should MOVE AROUND the screen. Currently stuck in one region. Needs more motion. |
| F12 | **Block corrupt** | More non-random modes in dropdown. |
| F13 | **Channel destroy** | More modes. |
| F14 | **Data bend** | More modes, more variability. |
| F15 | **Film grain** | Automated seed = grain with motion. |
| F16 | **Framesmash** | Color control / color affect options. |
| F17 | **Glitch repeat** | Motion, flicker, switch between different states. |
| F18 | **Invert bands** | Direction control, rotation, vectors, distortion of shapes (not just lines). Downward motion like CRT. |
| F19 | **Pixel annihilate** | More params to differentiate from noisy plugins, OR cut it. |
| F20 | **Pixel risograph** | Changeable colors. |
| F21 | **Xerox** | Individuate more. Allow patching effect order inside xerox. Reconsider physical model. Maybe chopping block. |
| F22 | **Row shift** | Rotation capability. Gravity concentrations. |
| F23 | **XOR glitch** | More modes. "Very cool, makes me want to explore more." |
| F24 | **Emboss** | Make gray areas transparent → layerable outlines on top of other effects. |
| F25 | **Parallel compress** | Compress on dimensions beyond black-white. |
| F26 | **Solarize** | Needs own brightness/black-gray-white control. |
| F27 | **Wavefold** | Needs brightness control. Histogram for luminosity levels. |
| F28 | **Tapesaturation** | Reconceptualize. "Just makes it more white." |

### System-Wide Features

| # | Request | Details |
|---|---------|---------|
| S1 | **Dry/wet knobs on all effects** | Transparency/opacity per effect. Mix slider exists but purpose unclear. |
| S2 | **Parameter metering / diagnostics** | Histogram showing parameter sensitivity zones. Where is the sweet spot? Where is it blown out? |
| S3 | **Non-linear parameter scaling** | Zoom into useful range. More resolution in the sweet spot. |
| S4 | **Frame diff tool** | Change param → see pixel diff. If nothing changes → flag as bug. |
| S5 | **Seed audit** | Systematic check: does seed actually work for every effect that exposes it? |
| S6 | **Gravity concentrations** | Place attraction points on frame that intensify all parameters in that region. Theoretical/future. |
| S7 | **Transparency rendering** | Render effects to transparent layers. Overlay pixel distortion on transparent regions. |
| S8 | **LFO min/max controls** | When LFO modulates a parameter, set the min and max bounds of modulation. |
| S9 | **Temporal effect preview** | Can't test temporal effects in web UI without play button. Need playback to see stutter/feedback/delay. |

---

## POSITIVE FEEDBACK (What Works Well)

| Effect | Feedback |
|--------|----------|
| **Smear** | "Very cool" |
| **ASCII art** | "INSANE! Really crazy." |
| **Blur** | "Great utility. Adds so much character in front of pixel sort." |
| **Contours** | "Very cool. Ability to have topography of everything." |
| **Edges** | "Very cool. Low threshold = old video game like Return of the Obra Dinn." |
| **Noise** | "Great utility." |
| **Sharpen** | "Great. Great utility." |
| **TV static** | "Good utility." |
| **Scanlines** | "Works." |
| **Gate** | "Very cool. I want to maintain that." |
| **Block corrupt** | "Dope." |
| **Film grain** | "Useful." |
| **Framesmash** | "Cool." |
| **Glitch repeat** | "Cool." |
| **Invert bands** | "Very cool." |
| **JPEG damage** | "Awesome." |
| **Pixel fax** | "Insane. So cool." |
| **Pixel risograph** | "Very cool." |
| **XOR glitch** | "Very cool. Makes me want to explore more." |
| **Pixel elastic** | "Cool when mass is low." |
| **Median** | "Pretty cool." |
| **Wave** | "Works." |
| **Wavefold** | "Kind of cool." |

---

## EFFECTS VERDICT SUMMARY

| Status | Effects |
|--------|---------|
| **BROKEN** | datamosh, pixel gravity, pixel haunt, pixel ink drop, pixel liquify, pixel melt, pixel time warp, pixel vortex, byte corrupt, flow distort, auto levels, histogram eq, sidechain crossfeed, real datamosh |
| **BUGGY** | duotone (doesn't revert), scanlines (flickr crashes), brailleart (question marks), pixel magnetic (most params dead), pixel quantum (params dead) |
| **WORKS BUT NEEDS IMPROVEMENT** | smear, wave, edges, contrast, pixel elastic, pixel wormhole, tapesaturation, ring mod, AM radio, emboss, parallel compress, solarize, wavefold, noise, TV static, contours, block corrupt, channel destroy, data bend, glitch repeat, invert bands, pixel annihilate, xerox, row shift, framesmash |
| **WORKS WELL** | ASCII art, blur, sharpen, film grain, JPEG damage, pixel fax, pixel risograph, XOR glitch, gate, posterize, median, VHS, pixel sort |
| **RECLASSIFY (not effects)** | hueshift, contrast, saturation, exposure, temperature, cyanotype, infrared, tapesaturation → should be color TOOLS |
| **RECLASSIFY (operators)** | LFO, flanger, phaser, gate, ring mod, sidechain → should be mappable OPERATORS |
| **CONSIDER CUTTING** | AM radio ("kind of useless"), pixel annihilate (redundant), xerox (maybe chopping block) |
| **CONSOLIDATE** | All 16 pixel physics → 3 mega-effects with mode selectors |

---

## PRIORITY TRIAGE

### P0 — Fix Before Next Session
1. File upload not working (B1) — can't test anything without this
2. Datamosh not rendering (B2) — primary feature
3. Scrollable param panels redesign (U1) — user missed half the params
4. History order fix (U2)

### P1 — Fix This Week
5. All broken pixel physics (B3-B9) — 7 effects dead
6. Byte corrupt, flow distort, auto levels, histogram eq (B10-B13)
7. Sidechain crossfeed mapping (B14)
8. Duotone revert bug (P5)
9. Scanlines flickr crash (P6)
10. Seed audit across all effects (P1)
11. Parameter range recalibration (systemic)

### P2 — Architecture (Spec + Plan)
12. Performance mode as timeline layer (A1)
13. Effects/Tools/Operators taxonomy (A3)
14. Modular sidechain (A4)
15. Mappable LFO (A5)
16. Pixel physics consolidation (A6)
17. Photoshop-level color tools (A7)

### P3 — Feature Enhancements
18. All feature requests (F1-F28)
19. System-wide features (S1-S9)

---

## EXHAUSTIVE QUOTE-TO-ITEM MAPPING

> Every phrase from the user's UAT session, mapped to a specific bug, request, or learning. No stone unturned.

### Upload & Mode Issues

| Quote | Maps To |
|-------|---------|
| "I dropped the file onto it, but it's not populating" | B1: File upload not populating |
| "it's not showing up on the timeline under the track" | B1-ext: Even if upload succeeds, timeline track doesn't populate |
| "or in performance mode" | B1-ext: Perform mode also doesn't show uploaded video |

### Architecture — Performance Mode

| Quote | Maps To |
|-------|---------|
| "performance mode should be an automation layer on top of the timeline" | A1: Perform as timeline layer |
| "with just additional tools being shown at the bottom" | A1-detail: Mixer/transport as bottom panel, not mode switch |
| "like we're combining Premiere and Ableton" | A1-ref: Premiere (timeline) + Ableton (automation/triggers) hybrid |
| "It's not like a completely different mode" | A1-detail: Modes should NOT be separate views |

### Architecture — Quick Mode

| Quote | Maps To |
|-------|---------|
| "I also don't know what the purpose of quick mode is" | A2: Quick mode purpose unclear — consider removing |

### Smear

| Quote | Maps To |
|-------|---------|
| "Smear is very cool" | POSITIVE: smear |
| "We should add more directions" | F1: Smear — more directions |
| "it had motion; you could watch things smear" | F1-ext: Smear — animated motion |
| "watch the direction kind of shift vectors; that would be very cool" | F1-ext: Smear — shifting direction vectors |

### Parameter Sensitivity (SYSTEMIC)

| Quote | Maps To |
|-------|---------|
| "there's like a threshold for some of the parameters where things get really blown out" | S2: Parameter sensitivity — blown-out threshold |
| "and then underneath kind of nothing happens" | S2-ext: Dead zone below threshold |
| "would it be effective to show a histogram or something diagnostic" | S2-detail: Parameter histogram/diagnostic visualization |
| "so we know, at what level of the decay, for example, everything is going to turn white" | S2-detail: Visual indicator of blow-out point |
| "Could we potentially zoom in on the resonance spike of that parameter set" | S3: Non-linear parameter scaling — zoom into useful range |
| "have the decay be much more sensitive" | S3-detail: More resolution in the sweet spot |
| "the full width of the parameters, most of it doesn't do anything" | S3-detail: Wasted slider range |
| "Once it's already blown out, it's just blown out" | S2-ext: Redundant range above blow-out |
| "underneath that it's very subtle" | S2-ext: Insufficient resolution in subtle range |
| "There's this one kind of peak range where things seem to work well" | S3: The "resonance peak" concept |
| "I would like to be more sensitive within that range" | S3: Non-linear scaling imperative |
| "I think I would also want to visualize...for how the user understands what is the visual reason for that" | S2-ext: User-facing explanation of parameter behavior |
| "if they can preempt it and hone in on the proper parameter tolerancing" | S2: Proactive parameter guidance |

### Pixel Elastic

| Quote | Maps To |
|-------|---------|
| "Pixel elastic is cool when the mass is low" | POSITIVE: pixel elastic (conditional) |
| "when the mass is high, it doesn't do anything" | P4: Pixel elastic high mass breaks it |
| "We should also add different force types and concentrations and vectors" | F10: Pixel elastic — force types, concentrations, vectors |
| "a little bit less atmospheric and a little bit more punchy" | F10-ext: Pixel elastic — needs punch, not ambient |
| "right now it just kind of tiles everything or fluidizes everything" | F10-ext: Current behavior too uniform |
| "these parameters are off, hanging off the bottom" | U1-ext: Scrollable params caused missed controls |

### Pixel Explode

| Quote | Maps To |
|-------|---------|
| "Pixel explode just kind of pinches things at the center. Is that the intent?" | Q1: Pixel explode — behavior unclear, possibly working but expectations mismatched |

### Mix Slider

| Quote | Maps To |
|-------|---------|
| "what is this mix slider on the top? I don't know what that means" | U3: Mix slider purpose unclear |
| "Maybe we should consider adding dry/wet knobs to all these effects?" | S1: Dry/wet per-effect |
| "I guess perhaps that would be transparency?" | S1-ext: Mix = transparency/opacity? Needs clearer labeling |
| "That's a medium idea" | PRIORITY: Medium |

### Pixel Gravity, Haunt, Ink Drop, Liquify

| Quote | Maps To |
|-------|---------|
| "Pixel gravity doesn't seem to be working either" | B3: Pixel gravity broken |
| "Pixel Haunt doesn't seem to be working" | B4: Pixel haunt broken |
| "Pixel Ink Drop doesn't seem to be working either" | B5: Pixel ink drop broken |
| "Pixel liquify doesn't seem to be working" | B6: Pixel liquify broken |

### Pixel Magnetic

| Quote | Maps To |
|-------|---------|
| "Pixel Magnetic works, but it only moves it toward the center" | P2: Only one behavior works |
| "If I add more poles, it doesn't seem to be making it more complex" | P2-ext: Poles param non-functional |
| "There's also only one field type" | P2-ext: Field type selector non-functional |
| "Damping doesn't seem to do anything" | P2-ext: Damping param dead |
| "neither does Rotation" | P2-ext: Rotation param dead |
| "neither does Seed" | P1/P2: Seed param dead |
| "It seems like all these pixel ones are not working as well as they did when we were just generating random stuff" | ROOT-CAUSE: Effects worked in batch/CLI render but broken in web UI preview (stateful frame issue) |

### Pixel Physics Consolidation

| Quote | Maps To |
|-------|---------|
| "Pixel melt doesn't work" | B7: Pixel melt broken |
| "Pixel quantum works, but uncertainty, superposition, and decoherence seem to not affect anything" | P3: Pixel quantum params dead |
| "Maybe we should group together some of these pixel ones into bigger plugins that have different modes" | A6: Pixel physics consolidation |
| "it seems like they're all kind of doing similar things and they seem a little bit redundant" | A6-reason: Redundancy across pixel effects |
| "Maybe we can combine them and troubleshoot and offer different physical or non-physical physics models" | A6-detail: Multiple physics models per consolidated effect |
| "for how it can distort stuff" | A6-detail: Distortion as the unifying concept |
| "it just seems like a lot of these are kind of doing the same things" | A6-reason: Repeated |
| "Let me know what you think there" | ACTION: CTO should analyze consolidation strategy |

### More Pixel Effects

| Quote | Maps To |
|-------|---------|
| "Pixel time warp doesn't seem to do anything" | B8: Pixel time warp broken |
| "Pixel Vortex doesn't seem to do anything" | B9: Pixel vortex broken |
| "pixel wormhole would be way cooler if the position of the distortion was moving around" | F11: Pixel wormhole — animated position |
| "It feels like it's localized to one region of the screen" | F11-ext: Currently static, should be dynamic |
| "it's supposed to have more motion than it's showing" | F11-ext: Expected motion, got static |
| "I think it could also be more effective" | F11-ext: Impact too subtle |

### Wave

| Quote | Maps To |
|-------|---------|
| "Wave works" | POSITIVE: wave |
| "We should have more directions" | F2: Wave — more directions |
| "being able to modulate the amplitude or modulate the frequency would be really sick" | F2-ext: Wave — amplitude/frequency modulation |
| "because then it would bounce around" | F2-ext: Dynamic bouncing wave |
| "For these modulations, I wanna be able to set max and min parameters too" | S8: LFO min/max controls |
| "Add that to notes for the LFO operator, perhaps" | ARCH: LFO operator needs min/max bounds |

### ASCII Art

| Quote | Maps To |
|-------|---------|
| "ASCII art is insane! Insane!" | POSITIVE: ASCII art (strongest positive reaction) |
| "Let's expand the character set to all of the different ASCII modes" | F3: ASCII art — all character modes |
| "Let's expand the color mode" | F3-ext: ASCII art — more color modes |
| "I think we should also audit what seed does across the board" | S5: Systematic seed audit |
| "it seems to not do things a lot of the time" | P1: Seed non-functional broadly |
| "Not sure what that actually provides as a value" | P1-ext: Seed value unclear to user |
| "but that's insane. Really crazy." | POSITIVE: ASCII art (repeated) |

### History

| Quote | Maps To |
|-------|---------|
| "the order is inverted" | U2: History order inverted |
| "the top most should be the most recent" | U2-detail: Most recent at top |
| "you should be able to scroll all the way down to the least recent" | U2-detail: Oldest at bottom |
| "right now, it's the opposite" | U2-confirm: Bug confirmed |

### Blur

| Quote | Maps To |
|-------|---------|
| "Blur is a great utility" | POSITIVE: blur |
| "This adds so much character in front of things like Pixel Sort" | RECIPE-INSIGHT: blur → pixelsort = interference patterns + texture |
| "for presets, having things blurred before a layer that affects pixels creates interference patterns and so much texture" | RECIPE: Create blur→pixelsort preset |
| "This is so cool" | POSITIVE: blur+pixelsort combo |
| "I think for blur we should add more options like Gaussian Blur" | F4: Blur — more types (Gaussian, etc.) |
| "I think there's a bunch of different types of blur that we should consider" | F4-ext: Radial, motion, lens, etc. |

### Brailleart

| Quote | Maps To |
|-------|---------|
| "I'm not sure what brailleart is supposed to do" | UX: Effect purpose unclear |
| "the result wasn't very effective" | P7: Brailleart not working |
| "It was just like a block of question marks that showed up" | P7-detail: Unicode encoding issue — `?` instead of braille chars |

### Contours

| Quote | Maps To |
|-------|---------|
| "Contours is very cool" | POSITIVE: contours |
| "Is there a way for there to be a setting on Contours where it only contours the outlines of shapes but doesn't affect the color of the shape inside it?" | F5: Contours — outline-only mode |
| "I feel like it dimmed a lot of the color palette and made it more like earth tones" | F5-detail: Color dimming is unwanted side effect |
| "I would like to have that be intentional" | F5-ext: Make color change optional/separate |
| "this ability to have topography of everything is very cool" | POSITIVE: contours topography |
| "I would like to have that isolated" | F5: Isolate contour lines from color changes |

### Edges

| Quote | Maps To |
|-------|---------|
| "Edges is very cool too" | POSITIVE: edges |
| "If we could control the color palette as well, that'd be great" | F6: Edges — color palette control |
| "the threshold can be kind of arbitrary" | S2/F6: Parameter sensitivity issue on edges |
| "after a certain point nothing is affected, but before that it gets really blown out" | S2: Same sensitivity pattern |
| "That's another point toward our metering quandary" | S2: Systemic — affects many effects |
| "Edges only and a low threshold? Makes it look like some old video game" | POSITIVE: edges at low threshold |
| "kind of thing like Return of the Obra Dinn" | REFERENCE: Visual aesthetic target |
| "That's very cool" | POSITIVE: edges (repeated) |

### Noise

| Quote | Maps To |
|-------|---------|
| "Noise is another great utility" | POSITIVE: noise |
| "The noise in the texture section would be really great to be able to have motion in the seed" | F7: Noise — animated seed = motion noise |
| "If I'm putting that before, like, pixel sort or something, it's going to add motion behind what's being sorted" | F7-reasoning: Animated noise before pixelsort = animated texture |
| "That's going to look really, really cool" | POSITIVE: animated noise concept |

### Posterize, Scanlines, Sharpen, TV Static, VHS

| Quote | Maps To |
|-------|---------|
| "Posterize works. It's cool. Not my favorite, but I could find utility for it" | POSITIVE: posterize (lukewarm) |
| "It's like medium effective" | PRIORITY: Medium/low |
| "I think maybe it's good where it's at" | NO-ACTION: posterize is fine as-is |
| "Scanlines works, but check on the flickr function" | P6: Scanlines flickr bug |
| "When I moved some of the functions past a certain point, it stopped rendering" | P6-detail: Threshold causes render halt |
| "then I couldn't get it to render again until I deleted the plugin and added it back" | P6-detail: State corruption — must remove and re-add |
| "We need to add that to the bug list and figure that out" | P6: Confirmed bug |
| "Sharpen is great. That will be a great utility" | POSITIVE: sharpen |
| "TV static is a good utility" | POSITIVE: TV static |
| "It would be cool if we can make concentrations of it in certain points" | F8: TV static — spatial concentration |
| "add some kind of physics model or gravity to it so it was a little bit more surreal" | F8-ext: TV static — gravity/physics model |
| "If you figure out a way to have motion or displacement of the static so it feels more like an actual active TV" | F8-ext: TV static — animated displacement |
| "VHS works, not my fave, but perhaps a good tool" | POSITIVE: VHS (lukewarm) |

### Contrast & Color Tools

| Quote | Maps To |
|-------|---------|
| "Contrast works, but it's a bit oversimplified considering I'm used to the contrast tool from Photoshop with a histogram and stuff" | F9/A7: Contrast needs Photoshop-level histogram |
| "We should make that better" | F9: Contrast improvement |
| "Cyanotype just makes it blue. Is that the intent?" | Q2: Cyanotype behavior questionable |
| "I'm not going to go through the entire color section" | USER-DECISION: Color section deprioritized for now |
| "those shouldn't be effects. Those should be part of the toolbar" | A3: Effects/Tools taxonomy — color = tools |
| "There should be a difference between effects and color correction and grading and stuff" | A3: Taxonomy confirmation |
| "We should be able to have them as an effect layer, I think, but it shouldn't be an effect; it should be like a tool" | A3-detail: Can be in chain but UI is "tool" not "effect" |
| "We're competing with Photoshop with these" | A7: Competitive standard = Photoshop |
| "maybe for those the interface could be a bit different" | A7-detail: Pop-out/expanded UI for color tools |
| "It could expand out; we could have a pop out" | A7-detail: Pop-out panels |
| "Truly, it needs to be as good as Photoshop or Premiere, or any of the free image editing software" | A7: Match competitor quality |
| "Maybe do some research and make it as competitive" | A7-action: Competitive research needed |
| "you'd have to spec out for each of these what the competitors are doing" | A7-action: Per-feature competitor spec |
| "for us to copy it" | A7-action: Copy, don't innovate on color tools |
| "we don't need to innovate there, but it has to be as good as what I want to see in Photoshop" | A7-principle: Copy > innovate for utilities |
| "Infrared is cool, but maybe there should just be a color filter section or toolset" | A3-ext: Infrared = color filter preset, not standalone effect |
| "and infrared is one of the settings" | A3-ext: Filter presets within color tool |
| "I don't think it should be its own thing" | A3-ext: Cut as standalone, merge into color tools |

### Hue Shift / Hue Flanger Redundancy

| Quote | Maps To |
|-------|---------|
| "Hue shift, Hue flanger — I feel like a little bit redundant" | A3/CUT: Hue shift + hue flanger overlap |
| "Maybe a flanger and a phaser is like an operator" | A3-ext: Flanger/phaser = operator category |
| "but we'd have to identify how it's different than an LFO" | ARCH-Q: LFO vs flanger vs phaser — define differences |
| "we could pick a color value or luminosity or opacity or light-dark histogram or RGB" | ARCH: Operator target = any spectrum value |
| "one of these different spectrum values" | ARCH: Operator target selection |
| "We could have resonant peaks kind of moving across as if it was a phaser or flanger" | ARCH: Phaser/flanger = resonant peak sweeping across spectrum |
| "Conceptually, is that how it's implemented?" | Q3: User asking about backend implementation |
| "I'm not sure what you did on the backend there" | Q3-ext: Backend unclear to user |
| "I think we should reconsider where we've put that" | A3: Reclassification needed |
| "perhaps that's enough to make it an effect rather than a tool" | A3: Classification decision deferred to CTO |
| "but I'll leave that up to you to decide" | ACTION: CTO decides effect vs tool vs operator |

### Sidechain Crossfeed

| Quote | Maps To |
|-------|---------|
| "the sidechain crossfeed doesn't do anything because it's not mapped to any output parameter" | B14: Sidechain crossfeed unmapped |
| "which is a major design flaw" | B14-severity: DESIGN FLAW not just bug |
| "We should fix that" | B14-action: Fix |
| "We should make it modular" | A4: Modular sidechain |
| "We should have an operators section" | A3: Operators category |
| "so we should have effects, tools, operators, and then image editing" | A3-full: 4 categories: Effects, Tools, Operators, Image Editing |

### Tape Saturation

| Quote | Maps To |
|-------|---------|
| "I think we could conceptualize tapesaturation a bit more creatively" | F28: Tapesaturation reconceptualize |
| "It just makes it more white" | F28-detail: Current behavior = just whitening |
| "I don't know about that" | PRIORITY: User uncertain about value |

### Temporal Effects

| Quote | Maps To |
|-------|---------|
| "I can't test any of the temporal effects because I don't have the ability to hit play and watch it happen" | S9: Temporal effect preview needs playback |
| "issue with the test plan there" | UAT-FIX: Test plan needs note about temporal effects requiring playback |

### LFO / Operators

| Quote | Maps To |
|-------|---------|
| "I see there is an LFO, but I can't map it to anything else" | A5: LFO not mappable |
| "I want to be able to hook it up to other effects" | A5: LFO → any parameter on any effect |
| "we need to take major inspiration from Ableton's Max for Live Operators" | A5-ref: Ableton Max for Live = reference implementation |

### AM Radio

| Quote | Maps To |
|-------|---------|
| "AM radio is kind of useless" | CUT-CANDIDATE: AM radio |
| "Either reconceptualize it or get rid of it" | CUT/REWORK: AM radio |

### Modulation Section

| Quote | Maps To |
|-------|---------|
| "I see the modulation section now. My points still stand" | A3: Modulation taxonomy issues persist |
| "I think these are kind of split up arbitrarily" | A3-detail: Arbitrary effect categorization |
| "I'd rather have things that map to other things" | A5: Modular mapping is the goal |
| "These are good, too. We should keep them" | KEEP: Current modulation effects as presets |
| "maybe like presets when we have the flanger" | A3-ext: Current effects become presets for operator |
| "all of these are valid filters and flanger-type shit" | A3-ext: Presets within operator |
| "It should be a flanger operator" | A3/ARCH: Flanger as operator, not effect |
| "It should be a flanger phaser" | ARCH-Q: Flanger vs phaser naming |
| "Maybe we should differentiate between them" | ARCH: Clear naming between operator types |
| "like flanger operator and, like, channel flanger or something" | ARCH-detail: Named variants within operator type |
| "Yeah, these all work, I think. I'll have to check them out a bit more later" | STATUS: Modulation effects functional but need more testing |

### Sidechain Feedback

| Quote | Maps To |
|-------|---------|
| "Your side chains, too, are split up by use case" | A4: Sidechain per-use-case = wrong approach |
| "I want it to be more broad" | A4: Modular sidechain |
| "but these are good presets for if we want to have it separate" | A4-detail: Current sidechains become presets |
| "I do like how these are" | POSITIVE: Sidechain concepts good |
| "Let's figure out a way to maintain these effects but also listen to me here" | A4: Keep as presets, add modular operator |

### Gate

| Quote | Maps To |
|-------|---------|
| "gate is very cool" | POSITIVE: gate |
| "I want to maintain that" | KEEP: Gate effect |
| "but I also want to make it an actual gate operator that I can map to different things" | A5/ARCH: Gate = mappable operator + keep preset |

### Ring Mod

| Quote | Maps To |
|-------|---------|
| "I think you could reinterpret ring mod" | REWORK: Ring mod |
| "I think there's some interesting ring mod where you can modulate it by another source" | ARCH: Ring mod with external modulation source |
| "Ring mod doesn't seem very effective" | STATUS: Ring mod underperforming |
| "It's just black stripes on the screen" | STATUS-detail: Output = black stripes only |

### Wavefold

| Quote | Maps To |
|-------|---------|
| "Wavefold is kind of cool" | POSITIVE: wavefold (tepid) |
| "but I have no idea what it does" | UX: Effect purpose unclear to user |
| "It would be nice to be able to have a brightness control on Wavefold" | F27: Wavefold — brightness control |
| "specifically because it seems to deal with brightness a ton, or like luminosity levels" | F27-reasoning: Wavefold operates on luminosity |
| "Like in Photoshop, when there's like a black, gray, white continuum in a histogram" | A7: Histogram reference (Photoshop levels) |
| "That should be a thing that's also in the color brightness settings" | A7-ext: Levels/histogram should be in color tools |
| "we can enumerate all the things that are in the Photoshop color brightness, hue, saturation, contrast, all that stuff" | A7-action: Enumerate all Photoshop color tools |
| "Those are things that we need to add" | A7: Confirmed requirement |

### Scrollable Params (CRITICAL UX)

| Quote | Maps To |
|-------|---------|
| "I just realized you could scroll down, that there's another access to these plugins" | U1: Hidden scrollable params discovered |
| "That's a major human error design flaw" | U1-severity: MAJOR |
| "because these are just supposed to be a horizontal strip" | U1-expectation: Horizontal layout expected |
| "I didn't expect you to be able to scroll down" | U1-detail: No affordance/signifier for scrolling |
| "I could be missing parameters. I have been missing parameters." | U1-impact: FALSE BUG REPORTS from missed params |
| "Some of this shit that I've been saying might not even be useful, because I just didn't realize that you could scroll down" | U1-impact: User self-correcting — some "bugs" may be params they didn't see |
| "If I didn't realize that and I built this, no one's gonna realize that" | U1-principle: If the builder misses it, users will too |
| "We have to figure out a different design for some of these plugin modules that doesn't have to scroll downward" | U1-action: Redesign param panels |
| "That's fucked" | U1-severity: Emphatic |

### Individual Effect Feedback (Quick-Fire)

| Quote | Maps To |
|-------|---------|
| "Auto levels doesn't seem to do anything" | B12: Auto levels broken |
| "Duotone, once I move the parameters, it doesn't, and then move it back; it doesn't revert" | P5: Duotone revert bug |
| "It just kind of sticks where the colors were until I delete it" | P5-detail: State persists after param change |
| "That's a glitch there" | P5: Confirmed bug |
| "Emboss would be much more interesting if we could use that as a layer on top of something and make all of the gray transparent" | F24: Emboss — transparent gray for layering |
| "Then we could just have these weird little outlines on top of shit" | F24-ext: Emboss outlines as overlay |
| "Once something is transparent, too, I think it'd be really cool to be able to render it" | S7: Transparent layer rendering |
| "then be able to have these other effects on top of it" | S7-ext: Effect on transparent layer |
| "pixel distortion effects, distorting and liquefying the pixels over a transparent region" | S7-ext: Pixel physics on transparency |
| "I think that would be really sick" | S7: Confirmed desire |
| "False Color is very punchy, but I'm not really sure what it does" | UX: False color purpose unclear |
| "It also doesn't seem very flexible" | STATUS: False color lacks param range |
| "Histogram eq has no visualizer; it has no effect. That's kind of a dud" | B13: Histogram eq broken + no visualizer |
| "Median is cool. That seems pretty cool" | POSITIVE: median |
| "Parallel compress is kind of cool" | POSITIVE: parallel compress |
| "it looks like it's just doing it across the black-white continuum" | F25: Parallel compress — limited to luminosity |
| "Maybe if there's other things we could compress, it would have more utility" | F25: Expand compression targets |
| "Solarize is cool, but needs its own black/gray/white/brightness control" | F26: Solarize — brightness control |
| "to counteract the darkening effect" | F26-reasoning: Solarize darkens, needs compensation |

### Destruction Effects

| Quote | Maps To |
|-------|---------|
| "Block corrupt is dope" | POSITIVE: block corrupt |
| "I think we should add more versions so it's not just random" | F12: Block corrupt — more non-random modes |
| "Are there other ones we could add there in that dropdown?" | F12: Expand mode dropdown |
| "Byte corrupt doesn't seem to do anything" | B10: Byte corrupt broken |
| "Guess we need to fix that" | B10-action: Fix |
| "I don't know what it's supposed to do" | UX: Byte corrupt purpose unclear |
| "Channel destroy should have more modes" | F13: Channel destroy — more modes |
| "the seed function doesn't really do anything when I move it" | P1: Seed non-functional |
| "when we're testing these, we should figure out a way to have a frame and move a parameter and check the diff on the frame" | S4: Frame diff tool for testing |
| "If we have a thing and we change the seed and the seed is surfaced as a parameter and nothing changes on the screen, that's an issue" | S5: Dead params must be fixed or hidden |
| "Either we're not using the right parameters or we're just gonna confuse the user" | S5-principle: Don't surface params that do nothing |
| "It's confusing me, and it makes me want to do more with the tool, and then you're offering me something that's not doing anything" | S5-impact: Dead params erode trust |
| "That's a consistent issue I'm noticing" | S5: Systemic across many effects |
| "Data Bend suffers from the same thing" | P1/F14: Data bend — dead params + needs more modes |
| "Could be cool. Not nearly enough variability" | F14: Data bend needs variability |
| "It needs more modes as well" | F14: More modes |
| "Datamosh doesn't seem to be working either" | B2: Datamosh broken |
| "which is really disappointing because that was one of the primary ones I was looking forward to" | B2-impact: PRIMARY FEATURE, user most wanted |
| "Film Grain is useful" | POSITIVE: film grain |
| "If the seed could be automated, that would be really cool to watch it all move" | F15: Film grain — automated seed = grain motion |
| "Flow distort doesn't seem to do anything" | B11: Flow distort broken |
| "Framesmash is cool" | POSITIVE: framesmash |
| "but if we have the ability to affect the colors, that would be better" | F16: Framesmash — color control |
| "Glitch repeat is cool" | POSITIVE: glitch repeat |
| "It would be cooler if there was motion, if there was flicker" | F17: Glitch repeat — motion/flicker |
| "If I can have different states of them and switch between them" | F17-ext: Switchable states |
| "I don't know, common feedback, I guess" | META: Motion/animation is a recurring theme |
| "Invert bands is very cool" | POSITIVE: invert bands |
| "if we could control the direction of the bands" | F18: Invert bands — direction control |
| "if there was rotation" | F18-ext: Rotation |
| "if there were vectors and distortion of the shapes, so it wasn't just lines" | F18-ext: Non-linear band shapes |
| "Or if somehow they moved downward like a CRT" | F18-ext: Animated downward motion like CRT |
| "JPEG damage is awesome" | POSITIVE: JPEG damage |
| "Pixel Annihilate seems redundant with some of the noisier plug-ins" | CUT-CANDIDATE: Pixel annihilate |
| "either individuate it and add more parameters so we can get different results out of it, or cut it" | F19: Differentiate or cut |
| "pixel fax, like fax machine — insane. So cool" | POSITIVE: pixel fax (strong) |
| "Pixel Risograph. Very cool, also" | POSITIVE: pixel risograph |
| "It would be awesome if we could change the colors" | F20: Pixel risograph — changeable colors |
| "Xerox seems a tad redundant" | CUT-CANDIDATE: Xerox |
| "It might be cool if you individuated it a bit more" | F21: Xerox differentiation |
| "allowed you to patch the order of the effects inside Xerox" | F21-ext: Patchable effect order within xerox |
| "like the skips. The skipped regions might be cool if it went before everything so it blurred also" | F21-ext: Skip regions with blur |
| "reconsider the physical model of Xerox and try and emulate that a bit more" | F21-ext: Better physical modeling |
| "this one might be on the chopping block. You tell me" | CUT-CANDIDATE: Xerox (deferred to CTO) |
| "Real datamosh doesn't render. Massive glitch because the datamosh is a key feature for me" | B2: CRITICAL — primary feature broken |
| "Row Shift is a decent utility" | POSITIVE: row shift |
| "Kind of redundant in some ways, but I think it has a different visual character" | STATUS: Row shift — unique but borderline |
| "If we could double down on that different visual character, that'd be cool too" | F22: Row shift — emphasize uniqueness |
| "If we could rotate it or mess with things" | F22-ext: Rotation |
| "interesting overall if we could place gravity concentrations in certain areas of the frames" | S6: Spatial gravity concentrations (theoretical) |
| "where it affected all of the parameters and just got kind of gravitated toward it" | S6-detail: Parameters intensify near gravity points |
| "like the parameters increased at that area" | S6-detail: Spatial parameter modulation |
| "Maybe that's a way down the line future improvement" | S6-priority: Future/theoretical |
| "That's a theoretical ask" | S6: Confirmed theoretical |
| "XOR glitch. Very cool" | POSITIVE: XOR glitch |
| "Needs more modes" | F23: XOR glitch — more modes |
| "Are there other parameters there?" | F23-ext: More params needed |
| "I don't even know what it's supposed to be doing or emulating" | UX: XOR glitch purpose unclear |
| "but it's very cool. Makes me want to explore it more" | POSITIVE: XOR glitch (strong engagement) |

### CLI Performance Mode

| Quote | Maps To |
|-------|---------|
| "I can't really use CLI performance mode because I need things like layering" | BLOCKER: CLI perf mode insufficient for tonight |
| "I need to be able to see what I'm doing" | REQUIREMENT: Visual feedback essential |
| "CLI freaks me out like that" | USER-PREF: CLI anxiety, needs GUI |

### Meta / Process

| Quote | Maps To |
|-------|---------|
| "go back and map everything that I said to a request or a learning" | THIS DOCUMENT |
| "Make sure there is no stone unturned" | COMPLETENESS REQUIREMENT |
| "if you miss anything, that's going to suck" | SEVERITY: Missing items = failure |
| "Really just break up all of my language phrases and map that in quotes to all of the breakdown items" | METHOD: Quote-level granularity |

---

## ITEMS NOT IN ORIGINAL FINDINGS (Discovered in Quote Mapping)

These items were in the user's feedback but MISSED in the first capture:

| # | New Item | Quote | Category |
|---|----------|-------|----------|
| NEW-1 | Pixel explode behavior unclear | "just kind of pinches things at the center. Is that the intent?" | Q1: Needs clarification |
| NEW-2 | Blur→Pixelsort preset recipe | "having things blurred before a layer that affects pixels creates interference patterns" | RECIPE |
| NEW-3 | False color lacks flexibility | "not really sure what it does...doesn't seem very flexible" | UX + F |
| NEW-4 | Wavefold operates on luminosity | "seems to deal with brightness a ton, or like luminosity levels" | UNDERSTANDING |
| NEW-5 | Enumerate all Photoshop color tools | "enumerate all the things that are in the Photoshop color brightness, hue, saturation, contrast" | A7-ACTION |
| NEW-6 | Flanger vs Phaser vs LFO differences | "we'd have to identify how it's different than an LFO" | ARCH-Q |
| NEW-7 | Operator target = any spectrum value | "pick a color value or luminosity or opacity or light-dark histogram or RGB" | ARCH |
| NEW-8 | Phaser/flanger concept for video | "resonant peaks kind of moving across as if it was a phaser or flanger" | ARCH |
| NEW-9 | Ring mod needs external modulation source | "modulate it by another source" | REWORK |
| NEW-10 | Dead params erode user trust | "offering me something that's not doing anything...It's confusing me" | UX-PRINCIPLE |
| NEW-11 | Animation/motion is RECURRING theme | Multiple: smear motion, noise motion, grain motion, glitch flicker, band motion, wormhole motion, static displacement | PATTERN |
| NEW-12 | Transparent layer rendering | "Once something is transparent...have these other effects on top of it...pixel distortion over transparent region" | S7 (expanded) |
| NEW-13 | Cyanotype purpose questioned | "just makes it blue. Is that the intent?" | Q2 |
| NEW-14 | Return of the Obra Dinn aesthetic | "low threshold...old video game...Return of the Obra Dinn" | VISUAL-REF |
| NEW-15 | Copy competitors, don't innovate on utilities | "we don't need to innovate there, but it has to be as good" | PRINCIPLE |
| NEW-16 | 4 categories confirmed: Effects, Tools, Operators, Image Editing | "we should have effects, tools, operators, and then image editing" | A3-FULL |
| NEW-17 | Current effects → presets when operator system built | "these are good presets for if we want to have it separate" | A4/A5 migration |
| NEW-18 | User needs GUI for tonight's video | "CLI freaks me out...I need to be able to see what I'm doing" | BLOCKER |

---

## TOTAL ITEM COUNT (FINAL)

| Category | Count |
|----------|-------|
| Critical Bugs | 14 |
| Parameter Bugs | 7 |
| UX/Design Bugs | 3 |
| Feature Requests | 28 |
| System-Wide Requests | 9 |
| Architecture Proposals | 7 (added Image Editing as 4th category) |
| Cut Candidates | 3 (AM radio, pixel annihilate, xerox) |
| Rework Candidates | 3 (ring mod, tapesaturation, cyanotype) |
| Positive Effects | 23 |
| Recipes/Presets to Create | 1 (blur→pixelsort) |
| Questions for CTO | 3 |
| New Items from Quote Mapping | 18 |
| **TOTAL TRACKED ITEMS** | **116** |

---

*Captured: 2026-02-15, live UAT session*
*Quote mapping: 2026-02-15, exhaustive pass — 150+ quotes mapped*

---

## ADDENDUM: UX REFACTOR SHIPPED (2026-02-15)

> **Context:** Don Norman heuristic analysis scored Entropic 7/10. 17 UX improvements implemented to target 9.5/10. 8 whimsy effects added. 2655 tests passing.

### Shipped Features (Sections 45-50 in UAT Plan)

| # | Feature | What It Does | Files Changed |
|---|---------|-------------|---------------|
| UXR-1 | Effect search bar | Type to filter effects across all categories | index.html, app.js, style.css |
| UXR-2 | Favorites system | Star effects, localStorage persistence, dedicated tab | app.js, style.css, index.html |
| UXR-3 | Info view panel | Ableton-style hover descriptions at bottom-left | app.js, style.css, index.html |
| UXR-4 | Chain complexity meter | Light/Medium/Heavy indicator + buffer count + click-to-clear-cache | app.js, style.css, index.html |
| UXR-5 | Effect hover preview | 400ms debounced thumbnail via /api/preview/thumbnail | app.js, server.py, style.css |
| UXR-6 | Parameter presets | Save/load/delete per-effect param snapshots via localStorage | app.js, style.css |
| UXR-7 | Automation lane switching | Right-click lane header to switch which param is automated | timeline.js, app.js |
| UXR-8 | Perform bake to timeline | Convert perform session events into timeline automation lanes | app.js |
| UXR-9 | Top 3 categories auto-expand | Most-used categories expand on load | app.js |
| UXR-10 | Arc visibility improvements | Better knob arc visibility in dark theme | style.css |
| UXR-11 | Export toast | Success notification after export completes | app.js |
| UXR-12 | 8 Whimsy effects | kaleidoscope, softbloom, shapeoverlay, lensflare, watercolor, rainbowshift, sparkle, filmgrainwarm | effects/whimsy.py, __init__.py, packages.py |

### Test Evidence
- 2655 tests passing (2547 pre-existing + 108 whimsy)
- 123 effects total (was 115)
- 12 categories (was 11)
- 16 packages (was 15)
- node -c syntax checks pass for all JS
- py_compile passes for all Python

---

## ADDENDUM: PERFORMANCE AUTOMATION FEATURES (2026-02-15, Planned)

> **Context:** User session identified gaps in performance recording workflow. 8 new feature areas documented with acceptance criteria (UAT Sections 51-56).

### Quote-to-Feature Mapping

| Quote | Maps To |
|-------|---------|
| "we might need to mimic Ableton's Overdub and Record buttons separately" | SEC-52: Separate Rec/Overdub buttons |
| "maybe we want an automation record" | SEC-53: Automation recording mode |
| "in a performance if there was a buffer of automation and we could claim it from not having recorded it by accident" | SEC-54: MIDI Capture / Retroactive Buffer (HIGHEST PRIORITY) |
| "In Ableton, there's that MIDI capture button. I think that would be great." | SEC-54: Confirms Ableton MIDI Capture as reference |
| "any automation performance can come from the computer keyboard via toggle" | SEC-51: Keyboard as performance input |
| "any MIDI input via keyboard and knob mappings" | SEC-55: MIDI controller mapping |
| "figure out how to map knobs to parameters and make macros" | SEC-56: Macro system |
| "hot key to toggle automation view on and off, so that would be the A button" | SEC-53.5: A key toggles automation lanes visibility |
| "keyboard toggle on for having it as a MIDI input, which would be M for triggering stuff" | SEC-51.1: M key toggles keyboard-as-controller mode |
| "different effect layers doing it...Ableton's Drum Rack and Sampler" | SEC-51.5: Drum rack-style multi-layer key mapping |

### Priority (User-Stated)
1. **MIDI Capture / Retroactive Buffer** (SEC-54) — "I think that would be great"
2. **Keyboard input mode** (SEC-51) — foundational for all performance
3. **Automation recording** (SEC-53) — knob movements to timeline
4. **Record vs Overdub** (SEC-52) — essential for iterative performance
5. **MIDI controller** (SEC-55) — hardware integration
6. **Macros** (SEC-56) — power user feature

---

## UAT ROUND 2: UX ARCHITECTURE (Same Session, Later)

> **Context:** User refreshed browser after Round 1 fixes were applied. Found fundamental architecture issues.

### ARCHITECTURE ISSUES (CRITICAL)

| # | Issue | Severity | User Quote |
|---|-------|----------|------------|
| A1 | **Separate Perform mode is a UX nightmare** | CRITICAL | "This separate mixer view is a UX nightmare. It compounds so terribly; it's a completely different interface." |
| A2 | **Perform mode removes timeline** | CRITICAL | "If a performance is supposed to be time-based, why do I have no timeline?" |
| A3 | **Multiple histograms for no reason** | HIGH | "There are multiple histograms for no reason." |
| A4 | **Can't resize panels** | HIGH | "I can drag the side of the effects thingy, and it gets bigger, but it disappears behind the preview area." |
| A5 | **Timeline takes up entire space** | HIGH | "When I first refreshed it, the timeline took up the entire space." |
| A6 | **Chain area cuts off content** | HIGH | "The windowing of the effect chain row is such that it cuts off stuff from the bottom." |
| A7 | **Devices tab redundant** | MEDIUM | "I don't think that the devices are relevant; it's redundant." |
| A8 | **Info panel too cluttered** | MEDIUM | "The info panel might be out of scope. Too much work." |
| A9 | **Theme toggle in wrong place** | LOW | "The toggle light/dark theme is placed in a terrible place." |
| A10 | **No way to add tracks** | HIGH | "I should be able to create new tracks. There should be a plus button." |
| A11 | **Mixer pre-loads random effects** | HIGH | "Why do I have four random effects pre-loaded and a master bus that just pulled up out of nowhere?" |
| A12 | **Loop as button, not timeline selection** | MEDIUM | "Loop should not be a button; it should be a selection on the timeline." |
| A13 | **Preview downsamples too aggressively** | MEDIUM | "It downsampled it, which I don't love." |
| A14 | **Undo/Redo buttons too large** | LOW | "Undo and redo can be just the icons; smaller." |
| A15 | **Export in wrong position** | LOW | "Export should go to the left, next to load file." |

### DECISIONS MADE

| Decision | Detail | Reference |
|----------|--------|-----------|
| Kill Quick/Timeline/Perform modes | ONE unified timeline view | ARCHITECTURE-DEEP-DIVE.md §7.2 |
| Perform = per-track device (Drum Rack) | Not a separate view | ARCHITECTURE-DEEP-DIVE.md §7.8 |
| Mixer = per-track controls in timeline | Opacity/Solo/Mute/Blend in track header (left side) | ARCHITECTURE-DEEP-DIVE.md §7.6 |
| Transport in top bar center | Always visible, Ableton-style icons | ARCHITECTURE-DEEP-DIVE.md §7.7 |
| Drag dividers for panel resizing | Standard IDE/DAW pattern | ARCHITECTURE-DEEP-DIVE.md §7.5 |
| History = dropdown button | Not a sidebar column | ARCHITECTURE-DEEP-DIVE.md §7.11 |
| Keyboard MIDI: transport still works | Only letter/number keys become MIDI | ARCHITECTURE-DEEP-DIVE.md §7.9 |
| Histogram hidden by default | View menu toggle, overlay on preview | ARCHITECTURE-DEEP-DIVE.md §7.13 |
| Render = Freeze/Flatten per-track | Right-click context menu, not toolbar button | ARCHITECTURE-DEEP-DIVE.md §7.14 |
| Browser collapsible via button | Tab key or button | ARCHITECTURE-DEEP-DIVE.md §7.12 |
| Max 8 tracks | Right-click or "+" to add | ARCHITECTURE-DEEP-DIVE.md §7.6 |
| MIDI routing in Preferences | Enable/disable per MIDI device | ARCHITECTURE-DEEP-DIVE.md §7.9 |

---

## UAT ROUND 3: POST-SPRINT TESTING (2026-02-15)

> **Context:** Following UI refactor sprint, all toolbar/layout/track issues addressed. Test plan covers merged toolbar, track system, transport controls, preview cleanup, and panel resizing.

### Test Plan

#### A. Toolbar & Navigation
- [ ] Single merged toolbar (File/Edit/View + transport + status)
- [ ] File menu: Open File, Export, Save Preset all work
- [ ] Edit menu: Undo, Redo, Randomize, Refresh all work
- [ ] View menu: Toggle Histogram, Toggle Sidebar, Split Compare, Pop Out Preview, Keyboard Shortcuts
- [ ] Transport centered: Play/Pause, Rec, Overdub, Capture, Loop buttons visible
- [ ] Transport icons are appropriately sized (not too small)
- [ ] Loop and Refresh have DIFFERENT icons (Loop = ↻, Refresh = ↻ but visually distinct)
- [ ] No Mixer button visible anywhere
- [ ] History dropdown opens on right side

#### B. Track System
- [ ] Default Track 1 appears on startup (before file load)
- [ ] Can add tracks with "+" button (up to 8)
- [ ] "+" button is channel-strip width, not full row
- [ ] Track header shows: name, opacity, Solo, Mute, blend mode
- [ ] Click track to select → chain panel updates
- [ ] Right-click track → context menu (Add/Duplicate/Delete/Move)
- [ ] Track collapse toggle works
- [ ] Solo/Mute buttons toggle correctly

#### C. Preview Canvas
- [ ] Preview video maintains aspect ratio (not stretched)
- [ ] No confusing buttons on preview (Capture/Diff/Split hidden)
- [ ] Split Compare accessible via View menu
- [ ] Pop Out Preview opens in new window

#### D. Panel Resizing
- [ ] Browser width draggable (120-500px)
- [ ] Canvas↔Timeline divider draggable
- [ ] Timeline↔Chain divider draggable
- [ ] Panel sizes persist on page reload
- [ ] Browser collapses via Tab key
- [ ] Chain/Timeline collapse to header only (28px)

#### E. Transport Controls
- [ ] Play/Pause toggles (Space key)
- [ ] Record activates (R key)
- [ ] Overdub activates (Shift+R)
- [ ] Capture blinks on trigger (Cmd+Shift+C)
- [ ] Loop toggles (L key)
- [ ] Timecode updates during playback
- [ ] Frame counter updates

---

*Added: 2026-02-15, post-sprint UAT cycle*

---

## ADDENDUM: UI REDESIGN SPRINT — COMPLETE (2026-02-15)

> **Context:** Full UI architecture overhaul based on UX heuristic analysis and UAT Rounds 1-2. Unified timeline view replacing 3-mode system.

### Phase A: Layout Foundation (COMPLETE)
| # | Feature | Status |
|---|---------|--------|
| A1 | Kill 3-mode system (Quick/Timeline/Perform) | DONE — mode toggle hidden |
| A2 | Merge topbar + menubar into single 38px bar | DONE |
| A3 | Move Load File + Export into File menu | DONE |
| A4 | Move Undo/Redo into Edit menu | DONE |
| A5 | Replace dice emoji with "Rand" text | DONE |
| A6 | Fix icon sizes to 18px | DONE |
| A7 | Hide right panel (layers/history sidebar) | DONE |
| A8 | Hide histogram panel + toggle | DONE |
| A9 | Drag dividers (browser, canvas-timeline, timeline-chain) | DONE |
| A10 | Collapsible browser sidebar (Tab key) | DONE |
| A11 | Panel collapse to 28px header | DONE |
| A12 | History as dropdown button (right-aligned) | DONE |
| A13 | Light/dark theme toggle | DONE |
| A14 | Panel sizes saved to localStorage | DONE |
| A15 | Collapsed panel grid rows adjusted | DONE |

### Phase B: Track System (COMPLETE)
| # | Feature | Status |
|---|---------|--------|
| B1 | Multi-track data model (max 8 tracks) | DONE |
| B2 | Track strip UI (name, controls, color) | DONE |
| B3-B5 | Add Track button, context menus | DONE |
| B6 | Track selection updates chain panel | DONE |
| B7-B8 | Track collapse/expand, color indicator | DONE |
| B9-B11 | Opacity, Solo (yellow), Mute (red) | DONE |
| B12 | Blend mode dropdown (7 modes) | DONE |
| B13 | Multi-track rendering pipeline (LayerStack compositing, 7 blend modes, solo/mute logic, export support) | DONE |

### Phase C: Transport Bar (COMPLETE)
| # | Feature | Status |
|---|---------|--------|
| C1-C8 | Play/Pause, Rec, Overdub, Capture, Loop with keyboard shortcuts | DONE |
| C10 | Frame navigation (arrow keys) | DONE |
| C9 | Loop region drag on ruler | IN PROGRESS |

### Immediate Fixes (COMPLETE)
- I1-I10: All resolved (dice to Rand, icons 18px, merged toolbar, history right, panel collapse, default Track 1, Add Track sizing, diff hidden, Loop vs Refresh icons, Mixer removed)

### Additional Changes
| Change | Detail |
|--------|--------|
| Tooltips removed | Both native title attributes (stripped via MutationObserver in init()) and custom data-tooltip CSS (display: none). Effect hover preview deprecated to no-op. User feedback: tooltips block content, same color scheme, hard to tell from UI. |
| Preview controls | Play/pause overlay, scrubber, fullscreen, pop-out window on hover |
| Split Compare | Moved from toolbar to View menu |
| Multi-track export | Export pipeline supports tracks array with per-track compositing |

---

## UAT ROUND 3: POST-SPRINT TESTING (2026-02-15) — UPDATED

> **Context:** Following UI refactor sprint, all toolbar/layout/track issues addressed. Test plan covers merged toolbar, track system, transport controls, preview cleanup, and panel resizing.

### Test Plan

#### A. Toolbar & Navigation
- [ ] Single merged toolbar (File/Edit/View + transport + status)
- [ ] File menu: Open File, Export, Save Preset all work
- [ ] Edit menu: Undo, Redo, Randomize, Refresh all work
- [ ] View menu: Toggle Histogram, Toggle Sidebar, Split Compare, Pop Out Preview, Keyboard Shortcuts
- [ ] Transport centered: Play/Pause, Rec, Overdub, Capture, Loop buttons visible
- [ ] Transport icons are appropriately sized (not too small)
- [ ] Loop and Refresh have DIFFERENT icons (Loop = ↻, Refresh = ↻ but visually distinct)
- [ ] No Mixer button visible anywhere
- [ ] History dropdown opens on right side

#### B. Track System
- [ ] Default Track 1 appears on startup (before file load)
- [ ] Can add tracks with "+" button (up to 8)
- [ ] "+" button is channel-strip width, not full row
- [ ] Track header shows: name, opacity, Solo, Mute, blend mode
- [ ] Click track to select → chain panel updates
- [ ] Right-click track → context menu (Add/Duplicate/Delete/Move)
- [ ] Track collapse toggle works
- [ ] Solo/Mute buttons toggle correctly

#### C. Preview Canvas
- [ ] Preview video maintains aspect ratio (not stretched)
- [ ] No confusing buttons on preview (Capture/Diff/Split hidden)
- [ ] Split Compare accessible via View menu
- [ ] Pop Out Preview opens in new window

#### D. Panel Resizing
- [ ] Browser width draggable (120-500px)
- [ ] Canvas↔Timeline divider draggable
- [ ] Timeline↔Chain divider draggable
- [ ] Panel sizes persist on page reload
- [ ] Browser collapses via Tab key
- [ ] Chain/Timeline collapse to header only (28px)

#### E. Transport Controls
- [ ] Play/Pause toggles (Space key)
- [ ] Record activates (R key)
- [ ] Overdub activates (Shift+R)
- [ ] Capture blinks on trigger (Cmd+Shift+C)
- [ ] Loop toggles (L key)
- [ ] Timecode updates during playback
- [ ] Frame counter updates

#### F. Multi-Track Rendering
- [ ] Add effect to Track 1, different effect to Track 2, preview shows composite
- [ ] Solo Track 2, only its effect visible
- [ ] Mute Track 1, its effect disappears
- [ ] Change blend mode to Multiply, visual changes
- [ ] Export with multi-track, output has composited effects

#### G. Tooltips
- [ ] No native browser tooltips on hover
- [ ] No custom data-tooltip popups
- [ ] Effect hover preview is disabled

---

## UAT ROUND 4: NEW FEATURES (Phases C9, D, E, F) — 2026-02-15

> **Context:** Manual test checklist for 4 new feature areas:
> - **C9:** Loop region (toggle, drag handles, playback wrap)
> - **Phase D:** Perform module (8 trigger pads, toggle/hold modes)
> - **Phase E:** MIDI input (keyboard as controller, Web MIDI, MIDI Learn)
> - **Phase F:** Freeze/Flatten (per-track freeze, 300-frame cap, frozen preview cache)

---

### Phase C9: Loop Region

#### Loop Toggle
- [ ] Click Loop button in transport bar → loop region appears on timeline ruler
- [ ] Loop region defaults to visible portion of timeline (or sensible range)
- [ ] Click Loop button again → loop region disappears
- [ ] Loop button shows active state when enabled (highlight/color)

#### Drag Handles
- [ ] Loop region has TWO drag handles (left=start, right=end)
- [ ] Drag left handle → start boundary updates, playhead follows
- [ ] Drag right handle → end boundary updates
- [ ] Handles snap to frame boundaries (no subframe positions)
- [ ] Cannot drag left handle past right handle (minimum 1-frame loop)
- [ ] Cannot drag right handle before left handle

#### Playback Wrap
- [ ] Enable loop, press Play → playback starts at loop start
- [ ] Playhead reaches loop end → wraps to loop start immediately
- [ ] Playback wraps smoothly (no pause/stutter)
- [ ] Frame counter shows correct wrapped frame number
- [ ] Disable loop during playback → playback continues linearly past loop end

#### Loop + Timeline Interaction
- [ ] Scrubbing inside loop region → preview updates normally
- [ ] Scrubbing outside loop region while loop enabled → playback still wraps on Play
- [ ] Loop region persists across session (localStorage)
- [ ] Loop region shown in timeline minimap (if applicable)

---

### Phase D: Perform Module (8 Trigger Pads)

#### Trigger Pad UI
- [ ] 8 trigger pads visible (keys 1-8)
- [ ] Each pad shows assigned effect name
- [ ] Each pad shows mode indicator (Toggle/Hold)
- [ ] Click pad → activates (visual feedback: color/border)
- [ ] Click again (Toggle mode) → deactivates
- [ ] Release mouse (Hold mode) → deactivates
- [ ] Keyboard keys 1-8 trigger pads (same as click)

#### Toggle Mode
- [ ] Assign effect to pad in Toggle mode
- [ ] Press key "1" → effect activates
- [ ] Press key "1" again → effect deactivates
- [ ] Toggle state persists until key pressed again
- [ ] Multiple pads can be active simultaneously (layering)

#### Hold Mode
- [ ] Assign effect to pad in Hold mode
- [ ] Press and hold key "2" → effect activates
- [ ] Release key "2" → effect deactivates immediately
- [ ] Hold mode does NOT persist state

#### Perform Backend Pass-Through
- [ ] Perform effect in chain → renders without crashing
- [ ] Preview updates reflect active perform layers
- [ ] Perform session persists across page refresh (if saved)
- [ ] Export with perform layers → output includes triggered effects

#### Perform Effect Assignment
- [ ] Right-click pad → "Assign Effect" menu opens
- [ ] Select effect from list → pad updates
- [ ] Change effect params → pad reflects new params
- [ ] Clear assignment → pad shows "Empty"
- [ ] Cannot assign more than 8 effects (pads 1-8)

---

### Phase E: MIDI Input

#### Keyboard as MIDI Controller
- [ ] Press "M" key → enables keyboard-as-MIDI mode
- [ ] Mode indicator shows "MIDI: ON"
- [ ] Transport controls (Space, R, L) still work in MIDI mode
- [ ] Letter keys (A-Z) map to MIDI notes
- [ ] Number keys (1-8) still trigger perform pads
- [ ] Press "M" again → disables MIDI mode

#### Key-to-Note Mapping
- [ ] QWERTY row maps to chromatic scale starting at C4 (configurable)
- [ ] Lower row maps to octave below (C3)
- [ ] Press key → MIDI note-on event fires
- [ ] Release key → MIDI note-off event fires
- [ ] Velocity fixed at 100 (or velocity-sensitive if implemented)

#### Web MIDI Integration
- [ ] Connect MIDI controller via USB
- [ ] Open Preferences → MIDI tab
- [ ] MIDI device appears in device list
- [ ] Enable device → MIDI input routes to perform layers
- [ ] MIDI note-on triggers perform pads (mapped to keys 1-8)
- [ ] MIDI CC messages modulate parameters (if MIDI Learn active)

#### MIDI Learn
- [ ] Click param knob → "MIDI Learn" button appears
- [ ] Click "MIDI Learn" → knob highlights (learning mode)
- [ ] Twist MIDI knob/fader → binding created
- [ ] Move MIDI controller → param updates in real-time
- [ ] Right-click param → "Clear MIDI" removes binding
- [ ] MIDI mappings persist across sessions (localStorage)

#### MIDI Routing Preferences
- [ ] Preferences → MIDI tab shows all connected devices
- [ ] Enable/disable per-device routing
- [ ] Set MIDI channel filter (1-16 or "All")
- [ ] MIDI Learn mappings listed in table (CC#, Param, Effect)
- [ ] Delete button removes individual mappings

---

### Phase F: Freeze/Flatten Track

#### Freeze Track (Backend)
- [ ] Select track, right-click → "Freeze Track" option appears
- [ ] Click "Freeze Track" → progress indicator shows
- [ ] Track freezes (effects baked into cached frames)
- [ ] Frozen track shows "FROZEN" badge in header
- [ ] Frozen track effect rack is disabled (grayed out)
- [ ] Scrubbing frozen track → preview uses cached frames (fast)

#### Freeze 300-Frame Cap
- [ ] Attempt to freeze 301+ frames → error message shown
- [ ] Error message: "Freeze limited to 300 frames. Select shorter region."
- [ ] Freeze exactly 300 frames → succeeds
- [ ] Freeze < 300 frames → succeeds

#### Frozen Preview Cache
- [ ] Freeze track → cache written to disk (or memory)
- [ ] Multitrack preview with frozen track → uses cache
- [ ] Frozen preview is pixel-identical to live render (no drift)
- [ ] Cache persists across page refresh (if saved)
- [ ] Cache invalidated on unfreeze

#### Unfreeze Track
- [ ] Right-click frozen track → "Unfreeze Track" option
- [ ] Click "Unfreeze" → badge removed, effect rack re-enabled
- [ ] Scrubbing unfrozen track → renders live again
- [ ] Can modify effects after unfreeze
- [ ] Re-freeze after changes → new cache generated

#### Export with Frozen Tracks
- [ ] Export project with 1 frozen track → output correct
- [ ] Export project with mixed frozen/live tracks → composite correct
- [ ] Frozen track opacity/blend mode respected in export
- [ ] Export progress indicator shows freeze status per-track

#### Freeze Error Handling
- [ ] Freeze track with no video loaded → error shown
- [ ] Freeze track with invalid frame range → error shown
- [ ] Freeze track when disk space low → error shown (if applicable)
- [ ] Freeze track with unsupported effect → warning shown, proceeds

---

### Integration: All Features Together

#### Scenario 1: Loop + Perform + Freeze
- [ ] Freeze track 0 (frames 0-50)
- [ ] Enable loop region (frames 10-40)
- [ ] Assign perform effect to pad 1
- [ ] Press Play → playback wraps at frame 40
- [ ] Press key "1" during playback → perform effect applies
- [ ] Frozen track renders from cache (no lag)

#### Scenario 2: MIDI + Perform + Loop
- [ ] Connect MIDI controller
- [ ] Enable MIDI routing
- [ ] Map MIDI note C4 to perform pad 1
- [ ] Enable loop region
- [ ] Press MIDI key → pad 1 triggers
- [ ] Playback wraps seamlessly with MIDI input active

#### Scenario 3: Freeze + Export
- [ ] Freeze 2 tracks with different effects
- [ ] Set blend modes (Multiply, Screen)
- [ ] Export 30-second clip
- [ ] Output video matches preview composite
- [ ] Frozen tracks don't cause export delay (cached)

---

### Performance Benchmarks

#### Freeze Performance
- [ ] Freeze 300 frames with 1 effect → completes in < 60 seconds
- [ ] Freeze 100 frames with 5 effects → completes in < 90 seconds
- [ ] Frozen preview at 60 FPS → no dropped frames
- [ ] CPU usage during frozen playback < 30%

#### MIDI Latency
- [ ] MIDI note-on to visual feedback < 50ms
- [ ] MIDI CC to param change < 50ms
- [ ] No audio dropouts during MIDI input
- [ ] No UI freeze during MIDI input burst (rapid notes)

#### Loop Playback
- [ ] Loop wrap latency < 1 frame (imperceptible)
- [ ] No memory leak during 100+ loop iterations
- [ ] CPU usage stable during looped playback

---

*Added: 2026-02-15, Phases C9/D/E/F manual test plan*

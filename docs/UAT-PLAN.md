# Entropic v0.2 — User Acceptance Testing Plan

> **Date:** 2026-02-08
> **Version:** 0.2.0 (37 effects, 7 categories, 27 presets, 31 package recipes)
> **Tester:** nissimdirect
> **Prepared by:** CTO, Red Team, Mad Scientist, Lenny

---

## How To Use This Document

1. Work through each section top-to-bottom
2. Mark each test: **PASS**, **FAIL**, or **SKIP** (with reason)
3. For FAIL: write what happened in the Notes column
4. You need a **test video** — a short clip (5-10 seconds) in the `test-videos/clips/` folder
5. All commands run from `~/Development/entropic/`

**Quick setup:**
```bash
cd ~/Development/entropic

# If you haven't already created a test project:
python3 entropic.py new uat-test --source test-videos/clips/YOURCLIP.mp4
```

---

## SECTION 1: SMOKE TESTS (Do These First)

> **Goal:** Confirm the system boots and basic operations work.
> **Time:** ~5 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 1.1 | Python runs | `python3 --version` | 3.x output | [ ] | |
| 1.2 | FFmpeg installed | `ffmpeg -version` | Version info | [ ] | |
| 1.3 | Import works | `python3 -c "from effects import EFFECTS; print(len(EFFECTS))"` | `37` | [ ] | |
| 1.4 | CLI help | `python3 entropic.py --help` | Shows commands | [ ] | |
| 1.5 | Version | `python3 entropic.py --version` | `entropic 0.2.0` | [ ] | |
| 1.6 | List effects | `python3 entropic.py list-effects --compact` | 37 effects, 7 categories | [ ] | |
| 1.7 | Packages CLI help | `python3 entropic_packages.py --help` | Shows commands | [ ] | |
| 1.8 | Packages list | `python3 entropic_packages.py list` | 7 packages | [ ] | |
| 1.9 | Existing tests pass | `python3 -m pytest tests/ -v` | All pass (312 expected) | [ ] | |

---

## SECTION 2: PROJECT MANAGEMENT

> **Goal:** Confirm projects can be created, listed, and inspected.
> **Time:** ~5 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 2.1 | Create project | `python3 entropic.py new uat-test --source test-videos/clips/YOURCLIP.mp4` | "Created project: uat-test" | [ ] | |
| 2.2 | Project dir exists | `ls ~/.entropic/projects/uat-test/` | source/, recipes/, renders/ | [ ] | |
| 2.3 | Source symlinked | `ls -la ~/.entropic/projects/uat-test/source/` | Symlink to clip | [ ] | |
| 2.4 | project.json valid | `cat ~/.entropic/projects/uat-test/project.json` | JSON with name, source, budget | [ ] | |
| 2.5 | List projects | `python3 entropic.py projects` | Shows "uat-test" | [ ] | |
| 2.6 | Project status | `python3 entropic.py status uat-test` | Name, source, 0 recipes | [ ] | |
| 2.7 | Duplicate blocked | `python3 entropic.py new uat-test --source test-videos/clips/YOURCLIP.mp4` | Error: already exists | [ ] | |

---

## SECTION 3: INDIVIDUAL EFFECTS (Original Workflow)

> **Goal:** Every effect produces visible output and doesn't crash.
> **Time:** ~30 minutes (37 effects)
> **Method:** Apply each effect, confirm a lo-res preview renders and opens.

### 3A. Glitch Effects (4)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.1 | pixelsort | `python3 entropic.py apply uat-test --effect pixelsort` | Sorted pixel streaks | [ ] | |
| 3.2 | channelshift | `python3 entropic.py apply uat-test --effect channelshift` | RGB offset visible | [ ] | |
| 3.3 | displacement | `python3 entropic.py apply uat-test --effect displacement` | Block displacement | [ ] | |
| 3.4 | bitcrush | `python3 entropic.py apply uat-test --effect bitcrush` | Reduced colors | [ ] | |

### 3B. Distortion Effects (3)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.5 | wave | `python3 entropic.py apply uat-test --effect wave` | Wavy distortion | [ ] | |
| 3.6 | mirror | `python3 entropic.py apply uat-test --effect mirror` | Symmetrical image | [ ] | |
| 3.7 | chromatic | `python3 entropic.py apply uat-test --effect chromatic` | RGB edge fringing | [ ] | |

### 3C. Texture Effects (7)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.8 | scanlines | `python3 entropic.py apply uat-test --effect scanlines` | Horizontal lines | [ ] | |
| 3.9 | vhs | `python3 entropic.py apply uat-test --effect vhs` | VHS degradation | [ ] | |
| 3.10 | noise | `python3 entropic.py apply uat-test --effect noise` | Grain overlay | [ ] | |
| 3.11 | blur | `python3 entropic.py apply uat-test --effect blur` | Soft/blurred | [ ] | |
| 3.12 | sharpen | `python3 entropic.py apply uat-test --effect sharpen` | Crisper edges | [ ] | |
| 3.13 | edges | `python3 entropic.py apply uat-test --effect edges` | Edge lines visible | [ ] | |
| 3.14 | posterize | `python3 entropic.py apply uat-test --effect posterize` | Fewer color levels | [ ] | |

### 3D. Color Effects (6)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.15 | hueshift | `python3 entropic.py apply uat-test --effect hueshift` | Colors rotated | [ ] | |
| 3.16 | contrast | `python3 entropic.py apply uat-test --effect contrast` | Higher contrast | [ ] | |
| 3.17 | saturation | `python3 entropic.py apply uat-test --effect saturation` | More vivid | [ ] | |
| 3.18 | exposure | `python3 entropic.py apply uat-test --effect exposure` | Brighter | [ ] | |
| 3.19 | invert | `python3 entropic.py apply uat-test --effect invert` | Negative image | [ ] | |
| 3.20 | temperature | `python3 entropic.py apply uat-test --effect temperature` | Warmer tones | [ ] | |

### 3E. Temporal Effects (9)

> **Important:** Temporal effects need VIDEO playback to see. A single frame may look normal.

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.21 | stutter | `python3 entropic.py apply uat-test --effect stutter` | Repeating frames | [ ] | |
| 3.22 | dropout | `python3 entropic.py apply uat-test --effect dropout` | Random black frames | [ ] | |
| 3.23 | timestretch | `python3 entropic.py apply uat-test --effect timestretch` | Slowed playback | [ ] | |
| 3.24 | feedback | `python3 entropic.py apply uat-test --effect feedback` | Ghost trails | [ ] | |
| 3.25 | tapestop | `python3 entropic.py apply uat-test --effect tapestop` | Freeze + fade | [ ] | |
| 3.26 | tremolo | `python3 entropic.py apply uat-test --effect tremolo` | Brightness pulsing | [ ] | |
| 3.27 | delay | `python3 entropic.py apply uat-test --effect delay` | Echo ghosts | [ ] | |
| 3.28 | decimator | `python3 entropic.py apply uat-test --effect decimator` | Choppy motion | [ ] | |
| 3.29 | samplehold | `python3 entropic.py apply uat-test --effect samplehold` | Random freezes | [ ] | |

### 3F. Modulation Effects (2)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.30 | ringmod | `python3 entropic.py apply uat-test --effect ringmod` | Sine wave bands | [ ] | |
| 3.31 | gate | `python3 entropic.py apply uat-test --effect gate` | Dark areas → black | [ ] | |

### 3G. Enhance Effects (6)

| # | Effect | Command | Expected Output | Result | Notes |
|---|--------|---------|----------------|--------|-------|
| 3.32 | solarize | `python3 entropic.py apply uat-test --effect solarize` | Partial inversion | [ ] | |
| 3.33 | duotone | `python3 entropic.py apply uat-test --effect duotone` | Two-color map | [ ] | |
| 3.34 | emboss | `python3 entropic.py apply uat-test --effect emboss` | 3D raised texture | [ ] | |
| 3.35 | autolevels | `python3 entropic.py apply uat-test --effect autolevels` | Better contrast | [ ] | |
| 3.36 | median | `python3 entropic.py apply uat-test --effect median` | Soft/painterly | [ ] | |
| 3.37 | falsecolor | `python3 entropic.py apply uat-test --effect falsecolor` | Heat map colors | [ ] | |

---

## SECTION 4: CUSTOM PARAMETERS

> **Goal:** Verify custom params override defaults correctly.
> **Time:** ~10 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 4.1 | Pixelsort threshold | `python3 entropic.py apply uat-test --effect pixelsort --params threshold=0.2` | More sorting (lower threshold = more pixels sort) | [ ] | |
| 4.2 | VHS heavy tracking | `python3 entropic.py apply uat-test --effect vhs --params tracking=0.9 noise_amount=0.5` | Very distorted VHS | [ ] | |
| 4.3 | Hueshift 90deg | `python3 entropic.py apply uat-test --effect hueshift --params degrees=90` | Colors shifted 90 degrees | [ ] | |
| 4.4 | Mix param (dry/wet) | `python3 entropic.py apply uat-test --effect pixelsort --params mix=0.3` | Subtle sort (30% wet) | [ ] | |
| 4.5 | Mix=0 (full dry) | `python3 entropic.py apply uat-test --effect invert --params mix=0.0` | Original (unchanged) | [ ] | |
| 4.6 | Tuple param | `python3 entropic.py apply uat-test --effect channelshift --params "r_offset=(20,0)"` | Large red offset | [ ] | |

---

## SECTION 5: RECIPE MANAGEMENT

> **Goal:** Recipes save, load, branch, and favorite correctly.
> **Time:** ~10 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 5.1 | History shows recipes | `python3 entropic.py history uat-test` | Lists all recipes created above | [ ] | |
| 5.2 | Recipe files exist | `ls ~/.entropic/projects/uat-test/recipes/*.json` | JSON files present | [ ] | |
| 5.3 | Preview single frame | `python3 entropic.py preview uat-test 001` | PNG opens in Preview.app | [ ] | |
| 5.4 | Branch recipe | `python3 entropic.py branch uat-test 001 --params threshold=0.8` | "Branched: NNN from 001" | [ ] | |
| 5.5 | Branch has parent | Check branched recipe JSON | `"parent": "001"` field set | [ ] | |
| 5.6 | Favorite toggle ON | `python3 entropic.py favorite uat-test 001` | "favorited" | [ ] | |
| 5.7 | Favorite toggle OFF | `python3 entropic.py favorite uat-test 001` | "unfavorited" | [ ] | |
| 5.8 | Named recipe | `python3 entropic.py apply uat-test --effect wave --name my-wave-test` | Recipe name = "my-wave-test" | [ ] | |

---

## SECTION 6: RENDERING QUALITY TIERS

> **Goal:** All 3 quality tiers produce valid output at correct resolution.
> **Time:** ~10 minutes

Pick any recipe ID from history (e.g., 001).

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 6.1 | Lo render | `python3 entropic.py render uat-test 001 --quality lo` | 480p MP4, small file | [ ] | |
| 6.2 | Mid render | `python3 entropic.py render uat-test 001 --quality mid` | 720p MP4, medium file | [ ] | |
| 6.3 | Hi render | `python3 entropic.py render uat-test 001 --quality hi` | Full-res MOV (ProRes) | [ ] | |
| 6.4 | Lo file exists | `ls ~/.entropic/projects/uat-test/renders/lo/` | .mp4 file present | [ ] | |
| 6.5 | Mid file exists | `ls ~/.entropic/projects/uat-test/renders/mid/` | .mp4 file present | [ ] | |
| 6.6 | Hi file exists | `ls ~/.entropic/projects/uat-test/renders/hi/` | .mov file present | [ ] | |
| 6.7 | Output plays in QuickTime | Double-click any render | Video plays correctly | [ ] | |

---

## SECTION 7: PACKAGES (Challenger Prototype)

> **Goal:** All 7 packages and 31 recipes render without errors.
> **Time:** ~20 minutes

### 7A. Package Exploration

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.1 | List all packages | `python3 entropic_packages.py list` | 7 packages shown | [ ] | |
| 7.2 | Explore analog-decay | `python3 entropic_packages.py explore analog-decay` | 4 recipes with effect chains | [ ] | |
| 7.3 | Explore digital-corruption | `python3 entropic_packages.py explore digital-corruption` | 4 recipes | [ ] | |
| 7.4 | Explore color-lab | `python3 entropic_packages.py explore color-lab` | 5 recipes | [ ] | |
| 7.5 | Explore temporal-chaos | `python3 entropic_packages.py explore temporal-chaos` | 5 recipes | [ ] | |
| 7.6 | Explore distortion-engine | `python3 entropic_packages.py explore distortion-engine` | 4 recipes | [ ] | |
| 7.7 | Explore enhancement-suite | `python3 entropic_packages.py explore enhancement-suite` | 5 recipes | [ ] | |
| 7.8 | Explore signal-processing | `python3 entropic_packages.py explore signal-processing` | 4 recipes | [ ] | |
| 7.9 | Invalid package | `python3 entropic_packages.py explore fake-package` | Error: unknown package | [ ] | |

### 7B. Single Recipe Apply (One Per Package)

| # | Package | Recipe | Command | Expected | Result | Notes |
|---|---------|--------|---------|----------|--------|-------|
| 7.10 | analog-decay | worn-tape | `python3 entropic_packages.py apply uat-test --package analog-decay --recipe worn-tape` | VHS look, renders + opens | [ ] | |
| 7.11 | digital-corruption | data-rot | `python3 entropic_packages.py apply uat-test --package digital-corruption --recipe data-rot` | Bitcrushed, posterized | [ ] | |
| 7.12 | color-lab | psychedelic | `python3 entropic_packages.py apply uat-test --package color-lab --recipe psychedelic` | Wild colors | [ ] | |
| 7.13 | temporal-chaos | echo-trail | `python3 entropic_packages.py apply uat-test --package temporal-chaos --recipe echo-trail` | Ghost trails | [ ] | |
| 7.14 | distortion-engine | earthquake | `python3 entropic_packages.py apply uat-test --package distortion-engine --recipe earthquake` | Heavy warping | [ ] | |
| 7.15 | enhancement-suite | neon-edges | `python3 entropic_packages.py apply uat-test --package enhancement-suite --recipe neon-edges` | Neon outlines | [ ] | |
| 7.16 | signal-processing | full-signal-chain | `python3 entropic_packages.py apply uat-test --package signal-processing --recipe full-signal-chain` | Ring mod + gate + scanlines | [ ] | |

### 7C. Batch (All Recipes in One Package)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.17 | Batch analog-decay | `python3 entropic_packages.py batch uat-test --package analog-decay` | 4 renders, summary table | [ ] | |
| 7.18 | Batch results | Check output | "4 passed, 0 failed" | [ ] | |

### 7D. Full Matrix (If Time Allows)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 7.19 | Full matrix | `python3 entropic_packages.py matrix uat-test` | 31 renders, summary table | [ ] | |
| 7.20 | Matrix results | Check output | "31 passed, 0 failed" (ideally) | [ ] | |

---

## SECTION 8: SEARCH AND DISCOVERY

> **Goal:** Effect search and info commands work.
> **Time:** ~3 minutes

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 8.1 | Search by name | `python3 entropic.py search pixel` | Finds pixelsort | [ ] | |
| 8.2 | Search by description | `python3 entropic.py search "noise"` | Finds noise, gate (noise gate) | [ ] | |
| 8.3 | No results | `python3 entropic.py search zzzzz` | "No effects matching" | [ ] | |
| 8.4 | Effect info | `python3 entropic.py info pixelsort` | Shows params, example | [ ] | |
| 8.5 | Unknown effect | `python3 entropic.py info doesnt-exist` | Error + fuzzy suggestion | [ ] | |
| 8.6 | Category filter | `python3 entropic.py list-effects --category temporal` | Only temporal effects (9) | [ ] | |

---

## SECTION 9: SAFETY GUARDS (Red Team)

> **Goal:** Entropic rejects bad inputs gracefully — no crashes, no data loss.
> **Time:** ~10 minutes

### 9A. File Safety

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.1 | Missing source | `python3 entropic.py new bad-test --source /nonexistent/video.mp4` | Error: file not found | [ ] | |
| 9.2 | Wrong extension | `python3 entropic.py new bad-test --source /etc/passwd` | Error: file type not allowed | [ ] | |
| 9.3 | Path traversal | `python3 entropic.py new bad-test --source ../../../../../../etc/passwd` | Error: path outside home | [ ] | |
| 9.4 | File too large | Create >500MB file, try to use | Error: exceeds limit | [ ] | SKIP if no large file |

### 9B. Effect Chain Safety

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.5 | Unknown effect name | `python3 entropic.py apply uat-test --effect DOESNT_EXIST` | Error: unknown effect | [ ] | |
| 9.6 | Chain depth limit | Apply recipe with 11+ effects | SafetyError: max 10 chain depth | [ ] | |
| 9.7 | Invalid param value | `python3 entropic.py apply uat-test --effect pixelsort --params threshold=NaN` | Error: NaN not allowed | [ ] | |
| 9.8 | Infinity param | `python3 entropic.py apply uat-test --effect exposure --params stops=inf` | Error: Inf not allowed | [ ] | |

### 9C. Resource Limits

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.9 | Frame limit (3000) | Use a very long video (if available) | Error: exceeds 3000 frames | [ ] | |
| 9.10 | Processing timeout | Set extremely heavy chain on long clip | Timeout after 5 minutes | [ ] | |
| 9.11 | Disk budget tracking | `python3 entropic.py status uat-test` | Shows MB used / 2.0GB budget | [ ] | |

### 9D. Input Sanitization

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 9.12 | Special chars in name | `python3 entropic.py new '../../../tmp/evil' --source clip.mp4` | Sanitized name (no path traversal) | [ ] | |
| 9.13 | Very long name | Use 200+ char project name | Truncated to 100 chars | [ ] | |

---

## SECTION 10: VISUAL QUALITY (Mad Scientist)

> **Goal:** Effects actually look different from each other and produce visually interesting results.
> **Time:** ~15 minutes
> **Method:** A/B comparison — compare original clip to processed output

### 10A. Intensity Gradients

Test that "light" recipes are visibly less intense than "heavy" recipes:

| # | Test | What to Compare | Expected | Result | Notes |
|---|------|----------------|----------|--------|-------|
| 10.1 | Analog light vs heavy | `light-wear` vs `destroyed-tape` | destroyed-tape MUCH more degraded | [ ] | |
| 10.2 | Digital light vs heavy | `minor-glitch` vs `full-corruption` | full-corruption way more broken | [ ] | |
| 10.3 | Warm vs cold | `warm-grade` vs `cold-grade` | Clearly opposite color temps | [ ] | |

### 10B. Effect Distinctiveness

| # | Test | What to Compare | Expected | Result | Notes |
|---|------|----------------|----------|--------|-------|
| 10.4 | VHS vs noise | Apply vhs, then noise separately | Different looks (VHS has tracking/bleed) | [ ] | |
| 10.5 | Pixelsort vs displacement | Apply each separately | Different looks (sort vs block shift) | [ ] | |
| 10.6 | Solarize vs invert | Apply each separately | Different (solarize = partial, invert = full) | [ ] | |

### 10C. Temporal Effects Are Temporal

| # | Test | What to Check | Expected | Result | Notes |
|---|------|--------------|----------|--------|-------|
| 10.7 | Stutter changes over time | Play stutter output | Not a static image — frames repeat/hold | [ ] | |
| 10.8 | Feedback builds | Play feedback output | Ghost trails increase with motion | [ ] | |
| 10.9 | Tapestop ends | Play tapestop output | Video freezes near end | [ ] | |

---

## SECTION 11: EDGE CASES (Lenny's Product Corner)

> **Goal:** Handle real-world usage patterns gracefully.
> **Time:** ~10 minutes

| # | Test | What to Do | Expected | Result | Notes |
|---|------|-----------|----------|--------|-------|
| 11.1 | Very short video (1-2s) | Create project with 1-2 second clip | Works, renders small output | [ ] | |
| 11.2 | No audio video | Use clip with `-an` (no audio) | Renders fine, no audio errors | [ ] | |
| 11.3 | Different formats | Test .mp4, .mov, .webm if available | All accepted | [ ] | |
| 11.4 | Apply to nonexistent project | `python3 entropic.py apply fake-project --effect pixelsort` | Clear error message | [ ] | |
| 11.5 | Preview nonexistent recipe | `python3 entropic.py preview uat-test 999` | Clear error message | [ ] | |
| 11.6 | Empty params list | `python3 entropic.py apply uat-test --effect wave --params` | Uses defaults, prints hint | [ ] | |
| 11.7 | Multiple projects | Create 2+ projects | Both work independently | [ ] | |

---

## SECTION 12: TEST CLIP EXTRACTION

> **Goal:** Verify the clip extraction script works on downloaded videos.
> **Time:** ~5 minutes (after copying videos)

| # | Test | Command | Expected | Result | Notes |
|---|------|---------|----------|--------|-------|
| 12.1 | Copy videos | `cp -r ~/Documents/TrippyVisuals ~/Development/entropic/test-videos` | Files copied | [ ] | |
| 12.2 | Run extraction | `bash scripts/extract_test_clips.sh` | Clips created in test-videos/clips/ | [ ] | |
| 12.3 | Clips are 10s max | `ffprobe -v error -show_entries format=duration -of csv=p=0 test-videos/clips/ANYCLIP.mp4` | <=10 seconds | [ ] | |
| 12.4 | Clips are 640x480 max | `ffprobe -v error -show_entries stream=width,height -of csv=p=0 test-videos/clips/ANYCLIP.mp4` | <=640 wide, <=480 tall | [ ] | |
| 12.5 | Use clip as source | `python3 entropic.py new clip-test --source test-videos/clips/ANYCLIP.mp4` | Project created | [ ] | |

---

## SCORING SUMMARY

Fill this in after testing:

| Section | Tests | Pass | Fail | Skip |
|---------|-------|------|------|------|
| 1. Smoke Tests | 9 | | | |
| 2. Project Management | 7 | | | |
| 3. Individual Effects | 37 | | | |
| 4. Custom Parameters | 6 | | | |
| 5. Recipe Management | 8 | | | |
| 6. Rendering Tiers | 7 | | | |
| 7. Packages | 20 | | | |
| 8. Search & Discovery | 6 | | | |
| 9. Safety Guards | 13 | | | |
| 10. Visual Quality | 9 | | | |
| 11. Edge Cases | 7 | | | |
| 12. Clip Extraction | 5 | | | |
| **TOTAL** | **134** | | | |

**Ship criteria:** 90%+ pass rate (121+ of 134), zero critical failures in Sections 1, 2, 9.

---

## PRIORITY ORDER

If you're short on time, test in this order:

1. **Section 1** (Smoke) — if this fails, stop here
2. **Section 9** (Safety) — security issues are blockers
3. **Section 7B** (One recipe per package) — validates packages work
4. **Section 3** (Individual effects) — the core product
5. **Section 6** (Render tiers) — quality output matters
6. Everything else

---

## KNOWN ISSUES / WATCH FOR

- **Temporal effects on single frames:** stutter, feedback, delay, etc. need multi-frame video to show their effect. A single-frame preview will look unchanged. Test by playing the rendered VIDEO, not by looking at a preview PNG.
- **Color tuple params in CLI:** Use quotes around tuples like `"r_offset=(20,0)"` — shells can interpret parentheses.
- **macOS auto-open:** After `apply`, the rendered video auto-opens in your default player. If too many renders pile up, close them periodically.
- **Disk usage:** Each rendered video takes 1-10MB at lo quality. The `matrix` command (7.19) will create ~31 renders. Check `status` afterward.

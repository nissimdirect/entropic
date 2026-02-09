# UX Review: Region Selection + Pop Chaos Design System

**Reviewers:** Don Norman (Design Principles) + Lenny Rachitsky (Product Thinking)
**Scope:** Region selection feature, CLI integration, Pop Chaos Design System v1.0
**Date:** 2026-02-08

---

## Part 1: Don Norman Analysis (Design of Everyday Things)

### DN-1. The Percent-vs-Pixel Ambiguity (CRITICAL)

**Principle violated:** Conceptual Model, Constraints

**The problem:** In `/Users/nissimagent/Development/entropic/core/region.py` lines 78-82, the parser uses a heuristic to decide whether `"0.25,0.1,0.5,0.8"` means percentages or pixels:

```python
# Check for percent mode (all values between 0 and 1)
if all(0.0 <= v <= 1.0 for v in values):
    # Could be pixels 0,0,1,1 or percentages — treat as percent
    return _percent_to_pixels(*values, frame_width, frame_height)
```

The code itself acknowledges the problem in its own comment: "Could be pixels 0,0,1,1 or percentages." A user who wants to target a 1x1 pixel region at the origin (`0,0,1,1`) will get a full-frame percentage region instead. The system guesses, and guessing creates a wrong mental model.

This is the exact kind of "mode error" Norman warns about: the system is in one mode (percent) but the user believes they are in another (pixels). The user has no way to know which mode their input triggered unless they inspect the output.

**Severity:** Critical -- silent data misinterpretation changes the effect output without warning.

**Fix:** Add an explicit prefix to disambiguate. Accept `%0.25,0.1,0.5,0.8` for percentages and bare numbers for pixels. Or: require values above 1.0 to mean pixels and 0.0-1.0 to mean percent, but WARN the user in the output which interpretation was used (e.g., "Region interpreted as: 25% x, 10% y, 50% width, 80% height (160x96 pixels)").

---

### DN-2. No Feedback on Region Application (MAJOR)

**Principle violated:** Feedback

**The problem:** When a user runs:
```bash
entropic apply myproject --effect pixelsort --threshold 0.6 --region center
```

The CLI output (in `/Users/nissimagent/Development/entropic/entropic.py`, lines 139-148) says:

```
Created recipe 001: pixelsort_001
Rendering lo-res preview...
Preview: /path/to/preview.mp4
```

There is zero feedback about the region. The user does not learn:
- What region was actually applied (resolved pixel coordinates)
- Whether their input was interpreted as percent or pixels
- What the feather radius resolved to
- That the effect was spatially limited at all

Compare this to audio production tools (which this user knows): a compressor always shows its threshold line, gain reduction meter, and affected frequency range. The equivalent here would be printing the resolved region.

**Severity:** Major -- users cannot verify their intent was correctly captured without watching the full preview video.

**Fix:** After creating the recipe, print the resolved region:
```
Created recipe 001: pixelsort_001
  Region: center (160,120 to 480,360 — 320x240px, 25% of frame)
  Feather: 0px (hard edge)
```

---

### DN-3. Preset Discoverability is Zero from the CLI (MAJOR)

**Principle violated:** Discoverability, Signifiers

**The problem:** A user who types `entropic apply --help` sees this help text for `--region` (line 345):

```
--region  Apply effect to region only: 'x,y,w,h' (pixels or 0-1 percent) or preset name (center, top-half, etc.)
```

The "(center, top-half, etc.)" is a non-exhaustive hint. There are 13 presets (`center`, `top-half`, `bottom-half`, `left-half`, `right-half`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, `center-strip`, `thirds-left`, `thirds-center`, `thirds-right`), but the user only learns about 2 of them from the help text.

There is no `entropic list-regions` or `entropic list-presets` command. The `list_presets()` function exists in `region.py` (line 231) and is exposed via the server API (`server.py` line 381), but there is no CLI path to it.

For a beginner user, undiscoverable features do not exist.

**Severity:** Major -- 11 of 13 presets are invisible to CLI users.

**Fix:** Add a `list-regions` subcommand to `entropic.py`, or add all preset names to the `--region` help text, or print available presets when the user passes an invalid region name. The error message in `region.py` line 71 does list presets on failure, which is good error recovery, but the user should not have to fail first to discover them.

---

### DN-4. `--feather` Without `--region` is Silently Ignored (MINOR)

**Principle violated:** Constraints, Feedback

**The problem:** In `entropic.py` lines 130-133:

```python
if args.region:
    params["region"] = args.region
if args.feather:
    params["feather"] = args.feather
```

A user can pass `--feather 20` without `--region`, and the feather value gets stored in the recipe params but has no effect (because `apply_effect` in `effects/__init__.py` line 577 pops feather and only uses it when region is not None at line 591-593). No warning is given.

This violates Norman's principle of constraints: the system should prevent meaningless combinations, or at minimum warn about them.

**Severity:** Minor -- does not cause incorrect output, but wastes user time and creates confusion about what happened.

**Fix:** If `args.feather > 0` and `args.region is None`, print a warning: "Note: --feather has no effect without --region. Feather controls edge blending for region selections."

---

### DN-5. Error Messages Are Good but Recovery Path is Missing (MINOR)

**Principle violated:** Error Recovery

**The problem:** The error messages in `region.py` are informative. For example, line 70-71:

```python
raise RegionError(
    f"Region must be 'x,y,w,h' or a preset name. Got: '{spec}'. "
    f"Presets: {', '.join(sorted(REGION_PRESETS.keys()))}"
)
```

This is good -- it lists available presets. But the error surfaces in `entropic.py` line 424-426 as:

```python
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

The RegionError's helpful preset list gets printed, but the user has to re-type the entire command from scratch. There is no interactive recovery (e.g., "Did you mean 'center'?"), and the broad `except Exception` catches everything with the same generic wrapper.

**Severity:** Minor -- the error content is good, but the recovery experience is abrupt. For a beginner user, seeing `Error:` and being dropped back to the shell is demoralizing.

**Fix:** For effect-not-found and region-not-found errors, suggest the closest match (fuzzy matching already exists for effects in `cmd_apply` lines 104-108 -- extend this pattern to regions).

---

### DN-6. Affordance Gap: Region Is a Parameter, Not a Concept (MINOR)

**Principle violated:** Affordances

**The problem:** Region selection is buried as two optional flags (`--region`, `--feather`) on the `apply` command. There is no conceptual introduction to the idea that effects can be spatially targeted. A user discovering Entropic for the first time sees:

```
entropic apply myproject --effect pixelsort --threshold 0.6
```

Nothing in this interaction suggests that spatial targeting is possible. The `--region` flag does not appear in the default help output unless the user runs `entropic apply --help`. The `entropic info pixelsort` command (lines 276-287) does not mention region support.

Compare this to Photoshop, where the selection tool is a primary, visible concept -- not an optional flag hidden inside another command.

**Severity:** Minor -- the feature exists and works, but its discoverability depends entirely on the user reading `--help` for the apply subcommand.

**Fix:** Add a note to `cmd_info` output: "Tip: All effects support --region and --feather for spatial targeting." Add region to the global help description of `apply`: "Apply an effect (supports --region for spatial targeting)."

---

### DN-7. The `center-strip` Preset Name Is Ambiguous (MINOR)

**Principle violated:** Signifiers

**The problem:** In `region.py` line 28:

```python
"center-strip": (0.00, 0.33, 1.00, 0.34),
```

"center-strip" is a horizontal strip through the middle third of the frame. But the name could equally mean a vertical strip through the center. A "strip" has no inherent orientation. Compare with `top-half` and `left-half`, which unambiguously encode both position and orientation in their names.

**Severity:** Minor -- the name communicates "center" correctly but fails on "strip" orientation.

**Fix:** Rename to `horizontal-center` or `mid-band` or `center-row`. Or add both `horizontal-center` and `vertical-center` as presets.

---

## Part 2: Lenny Rachitsky Analysis (Product Thinking)

### LR-1. User Journey: "I Want to Glitch Just This Part"

**Mapping the journey for a beginner user:**

1. User has a video. They want to pixelsort only the sky (top portion).
2. User runs `entropic list-effects` -- sees pixelsort. Good.
3. User runs `entropic info pixelsort` -- sees params but no mention of regions.
4. User runs `entropic apply --help` -- sees `--region` flag. First discovery point.
5. User reads the help text: "pixels or 0-1 percent or preset name (center, top-half, etc.)"
6. User tries `--region top-half`. It works.
7. User wants the edge to be soft. They have to discover `--feather` exists (it is in the same help text, so OK).
8. User tries `--feather 20`. No feedback on what this did. They watch the preview.

**Total steps to success: 8.** Steps 3-4 are friction points (info does not mention regions). Step 8 lacks feedback.

**Minimum viable path should be 4 steps:**
1. `entropic apply myproject --effect pixelsort --region top-half`
2. See output: "Applied pixelsort to top-half (0,0 to 640,240). Preview: [path]"
3. Open preview.
4. Done, or adjust.

**Gap:** Steps 3-4 in the current journey (discovering that regions exist) are unnecessary friction. The feature is hidden behind a help flag that a beginner may never read.

---

### LR-2. Friction Points

| Friction Point | Severity | Why It Matters |
|----------------|----------|----------------|
| No region mention in `entropic info` | High | Info is the natural place to learn about an effect's capabilities |
| No `list-regions` command | High | Users cannot discover presets without reading source or failing first |
| No feedback on resolved region | Medium | Users cannot verify intent without watching the preview |
| Percent/pixel ambiguity | Medium | Wrong mental model leads to wrong output, user blames themselves |
| Feather without region silently ignored | Low | Minor confusion, no damage |
| No region in `list-effects` output | Low | List is already dense; adding region info would clutter it |

---

### LR-3. Growth Loops and Shareability

**Region selection strengthens shareability.** When a user applies a pixelsort to only the sky of a landscape video, the result is more visually striking than a full-frame effect. The contrast between glitched and untouched areas creates an "how did they do that?" moment. This is the core of a growth loop:

1. User creates striking region-targeted effect
2. Shares on social media / sends to friend
3. Viewer asks "what tool is this?"
4. New user discovers Entropic

**But the current implementation does not help with this loop:**
- There is no watermark, attribution, or "made with Entropic" option in the output
- The recipe JSON (which captures the exact settings) is not designed to be shared
- There is no `entropic share` command or export-to-social workflow

**Opportunity:** The recipe system is already structured for sharing (JSON with effect names and params). A `entropic share myproject 001` command that generates a shareable link or embeds metadata would close the growth loop. Region presets like "center" make recipes reproducible across different videos -- the same recipe creates different but consistently interesting results on any input.

---

### LR-4. Impact on First-Time Activation

**Risk: Region selection could hurt activation if it's presented too early.**

A beginner user's first experience should be: apply one effect to one video, see the result, feel excitement. Adding `--region` and `--feather` to the `apply` command increases cognitive load. The user sees:

```
--effect EFFECT
--name NAME
--params [PARAMS ...]
--region REGION
--feather FEATHER
```

Five optional flags. For a beginner, this is overwhelming. The user may feel they need to understand all of them before they can start.

**Mitigation (already in place):** The flags are optional with sane defaults (no region = full frame, feather = 0). The `apply` command works with just `--effect`. This is correct.

**Recommendation:** Do not surface region in the introductory help or onboarding. Let users discover it after they have had their first success. The `entropic info` command is the right place to introduce it -- after the user has already applied their first effect and is exploring deeper.

---

### LR-5. Power User Path: Composing Regions with Effect Chains

**Current capability:** In `effects/__init__.py` lines 608-614, `apply_chain` applies effects sequentially. Each effect in the chain can have its own region and feather params (stored in the effect's params dict). This is verified in the test at `tests/test_region.py` lines 303-309.

**The power user journey:**
1. Pixelsort the top half with high threshold
2. Chromatic aberration on the center with feather
3. Noise on the bottom-right corner

This is possible today through the recipe system (each effect in the chain carries its own params including region). But the CLI only lets you apply one effect at a time -- multi-effect chains require the API or editing the recipe JSON directly.

**Opportunity:** A `--chain` mode or multi-step `apply` that builds a recipe with multiple effects would unlock power users. But this is a separate feature, not a bug in region selection.

**What regions enable for power users:**
- Spatial composition of different effects (different zones, different treatments)
- Edge blending between zones (feather creates smooth transitions)
- Combining with the `mix` parameter for per-region intensity control

This is genuinely powerful. The architecture supports it cleanly.

---

## Part 3: Design System UX Review

### DS-1. Internal Consistency: tokens.py vs. POP-CHAOS-DESIGN-SYSTEM.md

**Alignment check:**

| Token | Spec Doc (MD) | tokens.py | Status |
|-------|---------------|-----------|--------|
| `--bg-void` | `#050506` | `#050506` | Aligned |
| `--bg-darkest` | `#0a0a0b` | `#0A0A0B` | Aligned (case) |
| `--bg-dark` | `#111114` | `#111114` | Aligned |
| `--red-core` | `#ff2d2d` | `#FF2D2D` | Aligned (case) |
| `--green-phosphor` | `#39ff14` | `#39FF14` | Aligned (case) |
| `--amber-warm` | `#ffbf00` | `#FFBF00` | Aligned (case) |

**Hex case inconsistency:** The spec doc uses lowercase hex (`#ff2d2d`), `tokens.py` uses uppercase (`#FF2D2D`). This is cosmetic and functionally identical, but it creates a subtle inconsistency between the canonical spec and the programmatic implementation. If someone copies a value from the spec into code, or vice versa, string comparisons would fail.

**Extra tokens in tokens.py not in the spec doc:**
- `COLORS["text"]["inverse"]` (`#0A0A0B`) -- not in the spec
- `COLORS["text"]["glow"]` (`#C8FFE0`) -- not in the spec
- `COLORS["glitch"]` dict (7 values) -- not in the spec
- `COLORS["palettes"]` dict (6 palettes) -- not in the spec
- `COLORS["categories"]` dict (8 values) -- in the spec but under Section 9 "Application to Entropic," not in the core token table

These extras are reasonable extensions, but they create a discrepancy: the spec doc claims to be "the single source of truth" (line 733) while `tokens.py` contains tokens the spec does not define.

**Severity:** Minor. Functional code is not broken. But the "single source of truth" claim is incorrect -- `tokens.py` is a superset of the spec.

**Fix:** Either add the extra tokens to the spec doc, or add a note to `tokens.py` marking which tokens are spec-defined and which are implementation extensions.

---

### DS-2. CSS Variable Naming: Collision Risk

In `tokens.py`, the `get_css_variables()` function (lines 244-276) generates CSS custom properties by flattening nested dict keys:

```python
css_name = f"{category}-{name}".replace("_", "-")
lines.append(f"    --{css_name}: {hex_val};")
```

This produces variables like `--primary-red-core`, `--phosphor-green`, `--accent-uv-violet`. But the spec doc defines them as `--red-core`, `--green-phosphor`, `--uv-violet` -- without the category prefix.

The generated CSS variable names do not match the spec doc. Code that follows the spec will use `--red-core`; code generated by `tokens.py` will output `--primary-red-core`. These are different variables.

**Severity:** Major for anyone who tries to use both the spec doc and `tokens.py` together. The CSS variables are incompatible.

**Fix:** Either update `get_css_variables()` to match the spec's naming convention, or update the spec to use the category-prefixed names.

---

### DS-3. ASCII Art Assets: Function vs. Decoration

**Assessment:** The ASCII assets in `/Users/nissimagent/Development/design-system/ascii_assets.py` serve three distinct functions:

1. **Brand identity in terminal context** (logos, headers): Functional. The CLI is the primary interface, and ASCII art provides brand presence where graphical logos cannot render. The corrupted variants (`LOGO_ENTROPIC_CORRUPTED`) directly embody the product's philosophy. This is good.

2. **Progress indicators** (`progress_bar()` function, lines 215-232): Functional. The glitch-style progress bar (`style="glitch"`) that uses random block characters in the unfilled portion is a subtle brand touch on a utility element. This adds personality without sacrificing clarity (the percentage is always shown numerically).

3. **Decorative elements** (dividers, borders, corruption overlays): Mixed. The `border_glitched()` function (line 107) and `corruption_overlay()` function (line 200) are usable for documentation and marketing materials. But they are not currently used anywhere in the actual Entropic CLI output. They exist in the assets file but have no consumer.

**Verdict:** The logos and progress bars are functional. The decorative borders and corruption overlays are currently orphaned -- they have no integration point in Entropic's CLI. They are prepared for future use (marketing, README, documentation headers) but serve no function today.

**Recommendation:** This is acceptable as infrastructure. Do not remove them, but do not over-invest in expanding them until there is a concrete consumer (e.g., a README, a marketing page, a `--fancy` output mode).

---

### DS-4. Iconography Set: Terminal-First Is Correct

The icon set in `ascii_assets.py` (lines 243-276) is well-designed for a CLI-first tool. Every icon is renderable in a monospace terminal. The bracket convention (`[+]`, `[x]`, `[ON]`) for interactive targets provides clear hit-area signaling.

One issue: the `"file"` icon (`"[ ]"`) and the `"stop"` icon (`"[ ]"`) are identical. This creates an ambiguity in any context where both could appear.

**Severity:** Minor -- these icons are not currently used in the CLI, so the collision is theoretical.

**Fix:** Differentiate them. Use `[.]` for file (dot = content inside) or `[=]` for stop (equals = pause bars).

---

### DS-5. The Design System Spec Is Excellent But Has No Enforcement Mechanism

The spec doc at 735 lines is thorough, art-historically grounded, and internally coherent. The philosophical foundation (Section 1) is genuinely rigorous -- it is not decoration, it provides actual decision criteria for future design questions ("would Rosa Menkman consider this a glitch or a glitch-alike?").

But there is no automated enforcement. The `tokens.py` file provides programmatic access to values, but there is:
- No linter or CI check that verifies UI code uses token values
- No test that validates the spec doc and `tokens.py` are in sync
- No theme validation for the Gradio UI

For a solo developer, this is fine. But if the system grows, drift between the spec and implementation is inevitable without automation.

**Recommendation:** Do not build enforcement tooling now. But when the first UI refactor happens, write a simple script that compares `tokens.py` values against the spec doc's tables.

---

## Part 4: Recommended Changes (Prioritized)

### Priority 1: Do These Now (Before Next Release)

| # | Change | File | Effort | Impact |
|---|--------|------|--------|--------|
| 1 | **Print resolved region in CLI output** | `entropic.py` line ~139 | 5 lines | Fixes DN-2 (no feedback). Users can verify their intent. |
| 2 | **Add `list-regions` subcommand** | `entropic.py` | 15 lines | Fixes DN-3 (discoverability). Print all presets with their coordinate ranges. |
| 3 | **Warn when `--feather` used without `--region`** | `entropic.py` line ~130 | 3 lines | Fixes DN-4 (silent ignore). |
| 4 | **Add region/feather mention to `cmd_info` output** | `entropic.py` line ~283 | 2 lines | Fixes DN-6 + LR-1 (affordance gap, friction). |

### Priority 2: Do These Soon (Quality-of-Life)

| # | Change | File | Effort | Impact |
|---|--------|------|--------|--------|
| 5 | **Log which interpretation was used (percent vs pixel)** | `core/region.py` line ~82 | 5 lines (return metadata) | Fixes DN-1 partially. Full fix requires format change. |
| 6 | **Rename `center-strip` to something unambiguous** | `core/region.py` line 28 | 1 line + alias | Fixes DN-7 (ambiguous name). Keep old name as alias for backward compat. |
| 7 | **Fix CSS variable naming in `get_css_variables()`** | `design-system/tokens.py` line ~257 | 10 lines | Fixes DS-2. Critical if anyone uses the generated CSS. |
| 8 | **Fix file/stop icon collision** | `design-system/ascii_assets.py` line ~270 | 1 line | Fixes DS-4. |

### Priority 3: Consider for Future (Strategic)

| # | Change | File | Effort | Impact |
|---|--------|------|--------|--------|
| 9 | **Add explicit percent prefix (`%` or `p:`) to disambiguate** | `core/region.py` parsing | 20 lines | Full fix for DN-1. Breaking change, needs migration. |
| 10 | **Fuzzy matching for region preset names** | `core/region.py` | 10 lines | Fixes DN-5 (error recovery). |
| 11 | **Recipe sharing / export** | New feature | 50+ lines | Closes LR-3 growth loop. |
| 12 | **Add extra tokens to spec doc** | `docs/POP-CHAOS-DESIGN-SYSTEM.md` | Text only | Fixes DS-1 (single source of truth). |

---

## Part 5: What Is Already Good

These are genuine strengths. Do not change them.

1. **The error messages in `region.py` are excellent.** Lines 68-76 show the expected format AND list all available presets when parsing fails. This is textbook error communication. Most CLI tools just say "invalid input."

2. **The preset names (mostly) follow Norman's principle of natural mapping.** `top-half`, `bottom-left`, `right-half` -- these names map directly to spatial intuition. A user does not need to learn a coordinate system to use them. The only exception is `center-strip` (see DN-7).

3. **The clamping behavior in `_validate_pixels` is smart.** Lines 133-136 clamp regions that exceed frame bounds rather than rejecting them. This is forgiving design -- the user gets the closest valid result rather than an error. This is exactly what Norman recommends for constraints: guide toward success rather than block on failure.

4. **The safety validation layer is thorough.** The `validate_region` function in `safety.py` catches NaN, Inf, overlong strings, wrong counts, and non-numeric values before they reach the parser. Defense in depth.

5. **Feather mask implementation is robust.** The `create_feather_mask` function (lines 148-178) correctly handles edge cases: negative feather treated as 0, feather clamped to half the region size (prevents degenerate masks), float32 precision for smooth gradients. The for-loop implementation is clear and correct, even if it could be vectorized for performance.

6. **The design system's philosophical foundation is not decorative.** Section 1 of the spec provides genuine decision criteria. When a future design question arises ("should we add a gradient background?"), the answer can be derived from principles ("does this serve structural engagement or is it surface decoration?"). This is rare in design system documents.

7. **The recipe system is a powerful undo mechanism.** Every application of an effect creates a new recipe. Users never lose their previous state. This is implicit error recovery at the architecture level -- better than undo/redo because every branch is preserved.

8. **The test suite for regions is comprehensive.** `test_region.py` has 381 lines covering string parsing, dict parsing, tuple parsing, edge cases, clamping, feathering, integration with `apply_effect`, safety validation, and preset listing. 30+ test cases with parametrized coverage of all 13 presets. This is production-quality testing.

9. **`tokens.py` is cleanly structured.** The nested dict approach with semantic groupings (`primary`, `phosphor`, `accent`, `semantic`) makes token lookup intuitive. The `get_css_variables()` function (despite the naming issue) provides a bridge between Python and CSS that many design systems lack.

10. **The `apply` command's auto-preview behavior.** After creating a recipe, the command automatically renders a lo-res preview and opens it (lines 142-148). This is excellent feedback -- the user immediately sees the result. For region effects, this is where they will verify their region was correctly applied (even though explicit text feedback is missing, the visual feedback is fast).

---

*Review conducted applying Don Norman's seven fundamental principles of design (The Design of Everyday Things, revised edition) and Lenny Rachitsky's product thinking framework (growth loops, activation, friction analysis). All file paths and line numbers reference the codebase as of 2026-02-08.*

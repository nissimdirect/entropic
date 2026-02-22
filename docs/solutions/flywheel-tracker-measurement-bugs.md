---
title: Flywheel Tracker Measurement Bugs
date: 2026-02-21
category: infrastructure
tags: [flywheel, metrics, instrumentation, debugging]
severity: medium
root_cause: wrong key names and wrong directory paths
loops_affected: [1, 3, 7]
---

# Flywheel Tracker Measurement Bugs

## Problem

`flywheel_tracker.py` reported 0 for three loops that actually had data:
- **Loop 1 (Learn → Enforce):** Showed 0 learnings (actual: 149)
- **Loop 3 (Knowledge Accumulation):** Showed 0 articles (actual: 87,293)
- **Loop 7 (Cross-Model Validation):** Showed 0 delegations (actual: 61)

This made the flywheel appear less healthy than it was (4/10 spinning instead of 7/10).

## Root Causes

### Loop 1: Wrong pattern match
- **Code:** `content.count("\n## L#")` — looking for `## L#` section headers
- **Reality:** Learnings are numbered items like `1. **Assuming builds work**`
- **Fix:** `re.findall(r"^\d+\. \*\*", content, re.MULTILINE)` — count numbered bold items

### Loop 3: Wrong directory path
- **Code:** `Path.home() / "Development" / "knowledge-base"` (singular, doesn't exist)
- **Reality:** KB articles are spread across 40+ directories under `~/Development/` (fonts-in-use, music-production, art-criticism, etc.)
- **Fix:** Scan all subdirs of `~/Development/`, skip known code project dirs, count `.md` and `.html` files with `find -maxdepth 3`, threshold ≥3 files

### Loop 7: Wrong JSON key
- **Code:** `ds.get("total_delegations", 0)` (plural 's' at end)
- **Reality:** `delegation-compliance.json` uses `total_delegated` (past tense, no 's')
- **Fix:** `ds.get("total_delegated", ds.get("total_delegations", 0))` — check both for backwards compat

## Prevention

- **Test with real data:** The tracker was written without checking actual file formats. Should have run `head -50 learnings.md` and `cat delegation-compliance.json` before coding.
- **Ground truth validation:** Any metric tool should print its raw data source on first run so discrepancies are visible immediately.
- **Pattern:** When reading a file format, always read the actual file first — don't assume the format from the variable name.

## Verification

```bash
python3 ~/Development/tools/flywheel_tracker.py
# Expected: Loop 1 shows ~149 learnings, Loop 3 shows ~87K articles, Loop 7 shows ~61 delegations
```

## Related Learnings
- L#5: Working from memory — ALWAYS read/grep files
- L#19: Not verifying data accuracy — verify all data sources before displaying metrics

#!/usr/bin/env python3
"""
Seed Audit Script
Checks which effects expose a 'seed' parameter but don't actually use it.
"""

import inspect
import re
from effects import EFFECTS

def check_seed_usage(fn, fn_name):
    """Check if a function uses its seed parameter.

    Returns:
        - 'used': seed is used (random.seed, np.random.seed, RandomState, etc.)
        - 'unused': seed param exists but not referenced in code
        - 'no_param': no seed parameter in function signature
    """
    if fn is None:
        return 'no_fn'

    # Get source code
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError):
        return 'no_source'

    # Get signature to check if seed is a parameter
    sig = inspect.signature(fn)
    if 'seed' not in sig.parameters:
        return 'no_param'

    # Check for seed usage patterns
    patterns = [
        r'random\.seed\s*\(\s*seed',
        r'np\.random\.seed\s*\(\s*seed',
        r'RandomState\s*\(\s*seed',
        r'default_rng\s*\(\s*seed',
        r'Random\s*\(\s*seed',
        r'seed\s*=\s*seed',  # Passed to another function
        r'rng\s*=.*seed',
    ]

    for pattern in patterns:
        if re.search(pattern, source):
            return 'used'

    # Check if seed is mentioned at all (might be used in other ways)
    if re.search(r'\bseed\b', source):
        # Seed is mentioned but not in standard patterns — flag for manual review
        return 'mentioned'

    return 'unused'


def main():
    # Find all effects with seed param
    effects_with_seed = []
    for name, entry in EFFECTS.items():
        params = entry.get('params', {})
        if 'seed' in params:
            fn = entry.get('fn')
            fn_name = fn.__name__ if fn else None
            usage = check_seed_usage(fn, fn_name)

            effects_with_seed.append({
                'name': name,
                'category': entry.get('category', 'unknown'),
                'fn': fn_name,
                'usage': usage
            })

    # Group by usage status
    by_status = {}
    for e in effects_with_seed:
        status = e['usage']
        by_status.setdefault(status, []).append(e)

    # Report
    print(f"SEED AUDIT REPORT")
    print(f"=" * 80)
    print(f"Total effects with seed parameter: {len(effects_with_seed)}\n")

    for status in ['unused', 'mentioned', 'used', 'no_param', 'no_source', 'no_fn']:
        if status not in by_status:
            continue

        items = by_status[status]
        print(f"\n{status.upper()}: {len(items)} effects")
        print("-" * 80)

        for e in sorted(items, key=lambda x: (x['category'], x['name'])):
            print(f"  {e['category']:15s} | {e['name']:25s} | {e['fn']}")

    # Summary of action items
    print("\n" + "=" * 80)
    print("ACTION ITEMS:")
    print("-" * 80)

    if 'unused' in by_status:
        print(f"\n1. REMOVE SEED PARAM from {len(by_status['unused'])} effects (seed not used):")
        for e in by_status['unused']:
            print(f"   - {e['name']}")

    if 'mentioned' in by_status:
        print(f"\n2. MANUAL REVIEW needed for {len(by_status['mentioned'])} effects (seed mentioned but not in standard pattern):")
        for e in by_status['mentioned']:
            print(f"   - {e['name']}")


if __name__ == '__main__':
    main()

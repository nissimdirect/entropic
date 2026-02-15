"""
Entropic — Taxonomy UAT Tests
Tests for effect categorization, CATEGORIES dict, and CATEGORY_ORDER.

Run with: pytest tests/test_taxonomy.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from effects import EFFECTS, CATEGORIES, CATEGORY_ORDER


class TestTaxonomy:

    def test_every_effect_has_category(self):
        """Every effect in EFFECTS must have a 'category' key."""
        missing = []
        for name, entry in EFFECTS.items():
            if 'category' not in entry:
                missing.append(name)
        assert missing == [], f"Effects missing category: {missing}"

    def test_every_category_is_valid(self):
        """Every effect's category must be a key in CATEGORIES."""
        invalid = []
        for name, entry in EFFECTS.items():
            cat = entry.get('category')
            if cat not in CATEGORIES:
                invalid.append((name, cat))
        assert invalid == [], f"Effects with invalid category: {invalid}"

    def test_categories_covers_all_used(self):
        """CATEGORIES dict should contain all unique categories from EFFECTS."""
        used_cats = {entry.get('category') for entry in EFFECTS.values() if entry.get('category')}
        for cat in used_cats:
            assert cat in CATEGORIES, f"Category '{cat}' used by effects but not in CATEGORIES"

    def test_category_order_matches_categories(self):
        """CATEGORY_ORDER should contain all keys from CATEGORIES."""
        for key in CATEGORIES:
            assert key in CATEGORY_ORDER, f"Category '{key}' not in CATEGORY_ORDER"

    def test_category_order_no_extras(self):
        """CATEGORY_ORDER should not contain keys not in CATEGORIES."""
        for key in CATEGORY_ORDER:
            assert key in CATEGORIES, f"CATEGORY_ORDER has '{key}' not in CATEGORIES"

    def test_no_duplicate_effect_names(self):
        """Effect names in EFFECTS should be unique (dict guarantees this, but verify keys)."""
        names = list(EFFECTS.keys())
        assert len(names) == len(set(names)), "Duplicate effect names found"

    def test_every_effect_has_required_keys(self):
        """Every effect must have fn, params, description, category keys."""
        required = {'fn', 'params', 'description', 'category'}
        missing = {}
        for name, entry in EFFECTS.items():
            lacking = required - set(entry.keys())
            if lacking:
                missing[name] = lacking
        assert missing == {}, f"Effects missing required keys: {missing}"

    def test_categories_have_display_names(self):
        """Every CATEGORIES value should be a non-empty string (display name)."""
        for key, display in CATEGORIES.items():
            assert isinstance(display, str), f"CATEGORIES['{key}'] is not a string"
            assert len(display) > 0, f"CATEGORIES['{key}'] has empty display name"

    def test_all_used_categories_in_categories(self):
        """Every category used by effects exists in CATEGORIES dict."""
        used_cats = {entry.get('category') for entry in EFFECTS.values() if entry.get('category')}
        for cat in used_cats:
            assert cat in CATEGORIES, f"Category '{cat}' used but not in CATEGORIES"

    def test_effect_params_are_dicts(self):
        """Every effect's params should be a dict."""
        bad = []
        for name, entry in EFFECTS.items():
            if not isinstance(entry.get('params'), dict):
                bad.append(name)
        assert bad == [], f"Effects with non-dict params: {bad}"

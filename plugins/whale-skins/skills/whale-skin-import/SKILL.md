---
name: whale-skin-import
description: Import, validate or inspect an existing Codex-native pet package, ZIP, PNG or WebP sprite atlas without changing its character art.
---

Run `scripts/skin_manager.py validate <path>` using a Python runtime with Pillow. Supported inputs are a package directory, its `pet.json`, a ZIP containing one package, or a complete native PNG/WebP atlas. Single character images and arbitrary GIFs are references for `whale-skin-create`; they cannot be installed as full native action sets.

New skins use v2. Use `--allow-v1` only when the user is importing a pre-existing legacy 1536×1872 pet. Do not silently downgrade newly generated pets. Show validation failures with row/frame details and repair the source when authorized; do not bypass empty-frame or transparency checks.

On installation, preserve source files, use managed copies, refuse outside-package paths, and keep an existing differing ID unless replacement was requested. Verify installation with `doctor`. Treat installed, selected, visible and verified task-driven states as separate outcomes. Do not infer the app's active selection by reading unrelated account caches or conversation history.

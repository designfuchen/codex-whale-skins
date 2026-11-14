---
name: whale-skin-setup
description: Install or check a native Codex pet skin when the user asks to set up this plugin or activate an existing pet package.
---

Use the plugin's `scripts/skin_manager.py` with a Python runtime containing Pillow. In Codex desktop, use `load_workspace_dependencies` to find the bundled runtime instead of asking the user to install Python.

For a supplied native pet package, run `validate`, then `install`, passing the package path. Read the JSON result and use `doctor` to verify the installed pet's ID, version and image hash. Respect `CODEX_HOME`; use `--codex-home` for a test installation. Existing differing pets require explicit replacement intent; `--replace` creates a backup before replacing them. Preserve unrelated pets and settings.

Installation copies a declarative `pet.json` and PNG/WebP into the native pets directory. It does not prove that the app selected or displayed the pet. Use a supported pet-selection tool when it applies to this surface; otherwise direct the user to Settings > Pets, Refresh and select the installed name. Verify the returned active ID or ask the user to confirm the visible pet. Do not edit private desktop state, spoof task events, run another agent just to animate a demo, or claim activation from file existence alone.

The native app owns Running, Needs input, Ready and Blocked behavior. No log-monitoring daemon, approval hook, model API key or extra desktop app is required for this skin plugin. During an active task, confirm the working animation if observation is available; completion can only be claimed after a real completion event or user observation.

If the user supplies a character illustration rather than a valid sprite atlas, route to `whale-skin-create`. The local Lanlan preview is distributed separately from public source; do not upload or publish reference art without authorization.

---
name: whale-skin-setup
description: Register, select or check a native Codex pet skin when the user asks to set up this plugin or activate an existing pet package.
---

Use the plugin's `scripts/skin_manager.py` with a Python runtime containing Pillow. In Codex desktop, use `load_workspace_dependencies` to find the bundled runtime instead of asking the user to install Python.

First validate the supplied package locally. For modern desktop clients using the account pet library, prefer the available official Pets tools for registration. File staging alone may not make a character appear in Settings > Pets.

1. Resolve an existing stable pet ID from a prior verified registration or `list_pets`. Follow pagination. Avoid duplicate creation; names alone are not unique. Check matching name/description and source identity; ask only when candidates remain ambiguous.
2. For a new verified skin, call `validate_pet_spritesheet` on the exact final PNG/WebP and require `valid: true`. Then call `prepare_pet_upload` with the same absolute file path. Consume its `upload.upload_session_id` once with `create_pet`. Preserve the returned stable pet ID.
3. When the user asked to use the pet, call `select_pet` with that exact ID and verify the returned `active_pet_id`. Read back the pet collection when needed. Do not claim selection from a copied file or guess a cloud ID.
4. Confirm the native floating character is visible, using permitted observation or a concise user confirmation. When floating controls are hidden, `/pet` shows or hides them. If computer-use policy blocks the Codex window, explain that boundary and request only the remaining visible-state check.

Keep exported/local packages via `skin_manager.py install`, respecting `CODEX_HOME`. Its result is `local-package-only`, not account registration. Existing differing files require replacement intent; `--replace` creates a backup. Store this plugin's own verified ID/hash records separately from private desktop state, and always re-resolve IDs for the current account.

The native app owns Running, Needs input, Ready and Blocked behavior. Ready includes completed unread activity; a foreground already-read conversation can return to idle. Never spoof task events, edit private desktop preferences, intercept approvals, or start an extra agent solely to fake a demo. Public pet sharing is separate from private installation and requires the user's intended scope.

If official Pets tools are unavailable, use the client's supported custom-pet creation/import route or provide the valid package with an explicit registration/selection handoff. Do not extract authentication tokens or call reverse-engineered private endpoints. If the input is an ordinary character illustration, use `whale-skin-create` before attempting installation.

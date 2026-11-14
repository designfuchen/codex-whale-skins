---
name: whale-skin-create
description: Turn the user's character idea or reference art into a Codex-native animated pet skin with validated actions and gaze directions.
---

Read and follow `../../vendor/hatch-pet/SKILL.md` relative to this skill directory. It contains the full native v2 production and QA workflow; its scripts, references and Apache license are packaged with this plugin. Use imagegen for new or changed artwork and the bundled deterministic scripts for extraction, composition and validation. Preserve the user's chosen character and style.

New pets need 1536×2288 transparent PNG/WebP, 192×208 cells, nine standard animation rows and sixteen look directions. In v2, row 0 column 6 is the neutral-look cell. A small contact sheet, an arbitrary GIF loop, or one repeated pose is not a native pet package.

Keep work, waiting and completed-output review semantically distinct. Avoid clipping, identity drift, whole-character rotations that fake gaze, floating effect fragments and painted backgrounds. Preview the real motion and validate the exact final bytes before installation. Keep frame count, per-direction semantics, blind direction checks and continuity reports; do not invent successful QA output.

When a source jump really rises but per-pose fitting flattens its height, use the vendored extractor's `--method stable-slots --body-height 160 --baseline 203` for the standard rows, followed by `inspect_frames.py --allow-stable-slots`. This preserves each row's motion, keeps the non-jump baseline aligned and reserves room above the character for jumping. Review cross-state scale before accepting it. Approved full-cell neutral references retain their registration during extended-atlas assembly.

After the hatch pipeline passes, use `scripts/skin_manager.py pack <run> <new-output-dir> --id <id> --name <name>` from the plugin root, then follow `whale-skin-setup`. Keep source-code and artwork licensing separate. A request to create a skin authorizes local creation; public sharing or posting still needs the user's intended scope.

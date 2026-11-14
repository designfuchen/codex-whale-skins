#!/usr/bin/env python3
"""Validate a Codex pet spritesheet atlas."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image

COLUMNS = 8
ROWS = 9
EXTENDED_ROWS = 11
CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_WIDTH = COLUMNS * CELL_WIDTH
ATLAS_HEIGHT = ROWS * CELL_HEIGHT
EXTENDED_ATLAS_HEIGHT = EXTENDED_ROWS * CELL_HEIGHT
EXTENDED_NEUTRAL_LOOK_FRAME = (0, 6)
ROW_BY_INDEX = {
    0: ("idle", 6),
    1: ("running-right", 8),
    2: ("running-left", 8),
    3: ("waving", 4),
    4: ("jumping", 5),
    5: ("failed", 8),
    6: ("waiting", 6),
    7: ("running", 6),
    8: ("review", 6),
    9: ("look-000-to-157.5", 8),
    10: ("look-180-to-337.5", 8),
}


def alpha_nonzero_count(image: Image.Image) -> int:
    alpha = image.getchannel("A")
    return sum(alpha.histogram()[1:])


def transparent_rgb_residue_count(image: Image.Image) -> int:
    rgba = image.convert("RGBA")
    data = rgba.tobytes()
    count = 0
    for index in range(0, len(data), 4):
        red, green, blue, alpha = data[index : index + 4]
        if alpha == 0 and (red or green or blue):
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("atlas")
    parser.add_argument("--json-out")
    parser.add_argument("--min-used-pixels", type=int, default=50)
    parser.add_argument("--near-opaque-threshold", type=float, default=0.95)
    parser.add_argument("--allow-near-opaque-used-cells", action="store_true")
    parser.add_argument("--require-v2", action="store_true")
    args = parser.parse_args()

    atlas_path = Path(args.atlas).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    near_opaque_used_cells: dict[str, list[int]] = defaultdict(list)
    cells: list[dict[str, object]] = []

    try:
        with Image.open(atlas_path) as opened:
            source_mode = opened.mode
            source_format = opened.format
            has_encoded_alpha = "A" in opened.getbands() or "transparency" in opened.info
            image = opened.convert("RGBA")
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "errors": [f"could not open atlas: {exc}"], "warnings": []}
        print(json.dumps(result, indent=2))
        raise SystemExit(1) from exc

    expected_heights = (
        {EXTENDED_ATLAS_HEIGHT}
        if args.require_v2
        else {
            ATLAS_HEIGHT,
            EXTENDED_ATLAS_HEIGHT,
        }
    )
    if image.width != ATLAS_WIDTH or image.height not in expected_heights:
        expected = (
            f"{ATLAS_WIDTH}x{EXTENDED_ATLAS_HEIGHT} for a v2 pet"
            if args.require_v2
            else f"{ATLAS_WIDTH}x{ATLAS_HEIGHT} or {ATLAS_WIDTH}x{EXTENDED_ATLAS_HEIGHT}"
        )
        errors.append(f"expected {expected}, got {image.width}x{image.height}")

    if source_format not in {"PNG", "WEBP"}:
        errors.append(f"expected PNG or WebP, got {source_format}")

    if not has_encoded_alpha:
        errors.append("atlas does not have an encoded alpha channel")

    corners = (
        (0, 0),
        (image.width - 1, 0),
        (0, image.height - 1),
        (image.width - 1, image.height - 1),
    )
    alpha = image.getchannel("A")
    if any(alpha.getpixel(corner) for corner in corners):
        errors.append("atlas background must be transparent at all four corners")

    row_count = image.height // CELL_HEIGHT
    is_extended_atlas = image.height == EXTENDED_ATLAS_HEIGHT
    for row_index in range(row_count):
        state, frame_count = ROW_BY_INDEX[row_index]
        for column_index in range(COLUMNS):
            left = column_index * CELL_WIDTH
            top = row_index * CELL_HEIGHT
            cell = image.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT))
            nontransparent = alpha_nonzero_count(cell)
            used = column_index < frame_count or (
                is_extended_atlas and (row_index, column_index) == EXTENDED_NEUTRAL_LOOK_FRAME
            )
            cell_info = {
                "state": state,
                "row": row_index,
                "column": column_index,
                "used": used,
                "nontransparent_pixels": nontransparent,
            }
            cells.append(cell_info)
            if used and nontransparent < args.min_used_pixels:
                errors.append(
                    f"{state} row {row_index} column {column_index} is empty or too sparse ({nontransparent} pixels)"
                )
            if used and nontransparent > CELL_WIDTH * CELL_HEIGHT * args.near_opaque_threshold:
                near_opaque_used_cells[f"{state} row {row_index}"].append(column_index)
            if not used and nontransparent != 0:
                errors.append(
                    f"{state} row {row_index} unused column {column_index} is not transparent ({nontransparent} pixels)"
                )

    for row_label, columns in near_opaque_used_cells.items():
        message = (
            f"{row_label} has {len(columns)} nearly opaque used cells; "
            "this usually means the sprite has a non-transparent background"
        )
        if args.allow_near_opaque_used_cells:
            warnings.append(message)
        else:
            errors.append(message)

    alpha_count = alpha_nonzero_count(image)
    if alpha_count == image.width * image.height:
        errors.append("atlas is fully opaque; custom pets require a transparent sprite background")

    transparent_rgb_residue = transparent_rgb_residue_count(image)
    if transparent_rgb_residue:
        errors.append(
            f"atlas has {transparent_rgb_residue} fully transparent pixels with non-zero RGB residue"
        )

    result = {
        "ok": not errors,
        "file": str(atlas_path),
        "format": source_format,
        "mode": source_mode,
        "columns": COLUMNS,
        "rows": row_count,
        "sprite_version_number": 2 if is_extended_atlas else 1,
        "width": image.width,
        "height": image.height,
        "transparent_rgb_residue_pixels": transparent_rgb_residue,
        "errors": errors,
        "warnings": warnings,
        "cells": cells,
    }

    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps({k: v for k, v in result.items() if k != "cells"}, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()

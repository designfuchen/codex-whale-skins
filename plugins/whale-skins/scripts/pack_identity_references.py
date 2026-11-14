#!/usr/bin/env python3
"""Make a reference-only contact board when a visual job exceeds an image cap.

This arranges existing reference pixels; it never synthesizes pet artwork or
production frames. Source files are preserved and hashes recorded.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


def compose(sources, output, max_height=1024):
    images = []
    records = []
    for source in sources:
        source = Path(source).resolve()
        with Image.open(source) as opened:
            image = opened.convert("RGBA")
        image.thumbnail((1024, max_height), Image.Resampling.LANCZOS)
        images.append(image)
        records.append({"source": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "display_size": list(image.size)})
    if len(images) < 2:
        raise ValueError("A reference contact board needs at least two source images.")
    gap = 24
    board = Image.new("RGBA", (sum(image.width for image in images) + gap * (len(images) - 1), max(image.height for image in images)))
    x = 0
    for image, record in zip(images, records):
        y = (board.height - image.height) // 2
        board.alpha_composite(image, (x, y))
        record["display_box"] = [x, y, x + image.width, y + image.height]
        x += image.width + gap
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    board.save(output)
    value = {"purpose": "identity references only; not generated artwork", "sources": records, "output": str(output), "size": list(board.size)}
    output.with_suffix(".json").write_text(json.dumps(value, indent=2) + "\n")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(compose(args.sources, args.output), indent=2))

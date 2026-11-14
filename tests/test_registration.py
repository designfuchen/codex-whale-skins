"""Regression tests for preserving generated motion during deterministic layout."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/whale-skins/vendor/hatch-pet/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegistrationTest(unittest.TestCase):
    def test_cardinal_edge_noise_is_distinct_from_visible_clipping(self):
        cardinal = load("extract_cardinal_anchors")
        image = Image.new("RGBA", (20, 20), (20, 100, 210, 1))
        ImageDraw.Draw(image).rectangle((5, 5, 14, 14), fill=(20, 100, 210, 255))
        self.assertEqual(cardinal.edge_alpha_count(image, 2), 0)
        image.putpixel((0, 10), (20, 100, 210, 255))
        self.assertGreater(cardinal.edge_alpha_count(image, 2), 0)

    def test_faint_alpha_bridge_does_not_merge_poses_or_erase_edges(self):
        extract = load("extract_strip_frames")
        extract.CONNECTIVITY_ALPHA_THRESHOLD = 96
        image = Image.new("RGBA", (200, 100))
        draw = ImageDraw.Draw(image)
        draw.line((0, 50, 199, 50), fill=(0, 100, 220, 32), width=1)
        for x in [20, 120]:
            draw.rectangle((x - 1, 19, x + 30, 81), fill=(60, 120, 190, 8))
            draw.rectangle((x, 20, x + 29, 80), fill=(60, 120, 190, 255))
        groups = extract.component_frame_groups(image, 2)
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(extract.component_bounds(group)[2] - extract.component_bounds(group)[0] < 50 for group in groups))
        sprite = extract.component_group_image(image, groups[0])
        self.assertGreater(sprite.getchannel("A").histogram()[8], 0)

    def test_jump_keeps_source_vertical_displacement(self):
        extract = load("extract_strip_frames")
        extract.FRAME_BODY_HEIGHT = 160
        extract.FRAME_BASELINE = 203
        strip = Image.new("RGBA", (500, 160))
        draw = ImageDraw.Draw(strip)
        for column, top in enumerate([50, 35, 10, 35, 50]):
            draw.rectangle((column * 100 + 35, top, column * 100 + 64, top + 89), fill=(40, 100, 180, 255))
        frames = extract.extract_stable_slot_frames(strip, 5, preserve_jump=True)
        boxes = [frame.getchannel("A").getbbox() for frame in frames]
        self.assertLess(boxes[2][3], boxes[0][3] - 20)
        self.assertEqual(boxes[0][3], boxes[4][3])
        self.assertLessEqual(max(box[3] - box[1] for box in boxes) - min(box[3] - box[1] for box in boxes), 2)

    def test_extended_neutral_preserves_approved_cell_registration(self):
        assemble = load("assemble_extended_atlas")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "neutral.png"
            image = Image.new("RGBA", (192, 208))
            ImageDraw.Draw(image).rectangle((60, 43, 130, 202), fill=(40, 100, 180, 255))
            image.save(path)
            result = assemble.load_neutral_cell(path, Image.new("RGBA", (1536, 1872)))
            self.assertEqual(result.tobytes(), image.tobytes())


if __name__ == "__main__":
    unittest.main()

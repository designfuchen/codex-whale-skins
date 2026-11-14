"""Exercise real package validation and filesystem behavior using synthetic test pixels."""
from pathlib import Path
import io
import json
import sys
import tempfile
import unittest
import zipfile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/whale-skins/src"))
from whale_skins.packages import ROW_FRAMES, SkinError, doctor, inspect_package, install, package_source


class PackagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image = Image.new("RGBA", (1536, 2288))
        draw = ImageDraw.Draw(image)
        for row, count in enumerate(ROW_FRAMES):
            for column in range(count):
                draw.rectangle((column * 192 + 50, row * 208 + 50, column * 192 + 90, row * 208 + 110), fill=(50, 100, 180, 255))
        draw.rectangle((6 * 192 + 50, 50, 6 * 192 + 90, 110), fill=(50, 100, 180, 255))
        output = io.BytesIO()
        image.save(output, format="PNG")
        cls.image_bytes = output.getvalue()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.package = self.root / "source"
        self.package.mkdir()
        (self.package / "spritesheet.png").write_bytes(self.image_bytes)
        self.manifest = {"id": "whale-test", "displayName": "Test only", "description": "Synthetic validation fixture, not pet artwork.", "spriteVersionNumber": 2, "spritesheetPath": "spritesheet.png"}
        self.write_manifest()

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self):
        (self.package / "pet.json").write_text(json.dumps(self.manifest))

    def test_native_v2_including_reserved_neutral_cell_is_valid(self):
        result = inspect_package(self.package)
        self.assertEqual(result["version"], 2)
        self.assertEqual(result["width"], 1536)

    def test_install_copies_source_and_is_idempotent(self):
        home = self.root / "codex"
        first = install(self.package, home=home)
        second = install(self.package, home=home)
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(first["install_mode"], "local-package-only")
        self.assertFalse(first["registered_in_account"])
        self.assertFalse(first["activation_verified"])
        self.assertTrue((self.package / "spritesheet.png").exists())
        self.assertFalse(doctor(home)["activation_verified"])

    def test_replacement_requires_intent_and_preserves_backup(self):
        home = self.root / "codex"
        install(self.package, home=home)
        self.manifest["displayName"] = "Different metadata"
        self.write_manifest()
        with self.assertRaises(SkinError):
            install(self.package, home=home)
        result = install(self.package, home=home, replace=True)
        self.assertTrue(Path(result["backup"]).is_dir())
        self.assertEqual(inspect_package(result["backup"])["name"], "Test only")

    def test_explicit_replace_can_repair_a_broken_existing_pet(self):
        home = self.root / "codex"
        destination = home / "pets/whale-test"
        destination.mkdir(parents=True)
        (destination / "pet.json").write_text("broken")
        with self.assertRaises(SkinError):
            install(self.package, home=home)
        result = install(self.package, home=home, replace=True)
        self.assertEqual((Path(result["backup"]) / "pet.json").read_text(), "broken")
        self.assertTrue(doctor(home)["pets"][0]["valid"])

    def test_idempotence_ignores_source_image_filename(self):
        original = self.package / "spritesheet.png"
        nested = self.package / "art"
        nested.mkdir()
        original.rename(nested / "character.png")
        self.manifest["spritesheetPath"] = "art/character.png"
        self.write_manifest()
        home = self.root / "codex"
        install(self.package, home=home)
        self.assertFalse(install(self.package, home=home)["changed"])

    def test_rejects_outside_paths_and_symlink_escape(self):
        self.manifest["spritesheetPath"] = "../outside.png"
        self.write_manifest()
        with self.assertRaises(SkinError):
            inspect_package(self.package)
        outside = self.root / "outside.png"
        outside.write_bytes(self.image_bytes)
        (self.package / "link.png").symlink_to(outside)
        self.manifest["spritesheetPath"] = "link.png"
        self.write_manifest()
        with self.assertRaises(SkinError):
            inspect_package(self.package)

    def test_rejects_blank_used_frame_and_filled_unused_slot(self):
        with Image.open(self.package / "spritesheet.png") as source:
            image = source.copy()
        image.paste((0, 0, 0, 0), (0, 0, 192, 208))
        image.save(self.package / "spritesheet.png")
        with self.assertRaisesRegex(SkinError, "empty"):
            inspect_package(self.package)
        (self.package / "spritesheet.png").write_bytes(self.image_bytes)
        with Image.open(self.package / "spritesheet.png") as source:
            image = source.copy()
        ImageDraw.Draw(image).rectangle((7 * 192 + 50, 50, 7 * 192 + 90, 110), fill=(1, 2, 3, 255))
        image.save(self.package / "spritesheet.png")
        with self.assertRaisesRegex(SkinError, "Unused"):
            inspect_package(self.package)

    def test_imports_zip_without_extracting_unrelated_files(self):
        archive = self.root / "pet.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.write(self.package / "pet.json", "pet/pet.json")
            output.write(self.package / "spritesheet.png", "pet/spritesheet.png")
            output.writestr("pet/extra.txt", "not installed")
        result = install(archive, home=self.root / "codex")
        self.assertFalse((Path(result["path"]) / "extra.txt").exists())

    def test_rejects_zip_traversal_even_in_unused_entries(self):
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("../escape.txt", "bad")
        with self.assertRaises(SkinError):
            with package_source(archive):
                pass

    def test_plain_character_image_is_not_an_animation_atlas(self):
        image = Image.new("RGBA", (128, 128))
        image.save(self.package / "spritesheet.png")
        with self.assertRaisesRegex(SkinError, "Expected"):
            inspect_package(self.package)


if __name__ == "__main__":
    unittest.main()

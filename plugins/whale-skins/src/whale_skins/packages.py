"""Bounded, declarative native-pet package validation and atomic installation."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import uuid
import zipfile

from PIL import Image

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_MANIFEST_BYTES = 32 * 1024
ROW_FRAMES = (6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8)


class SkinError(ValueError):
    """The input does not satisfy the native pet contract."""


def codex_home(value: str | Path | None = None) -> Path:
    return Path(value or os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser().resolve()


def slug(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise SkinError("Pet ID must use 1–64 lower-case letters, digits or hyphens.")
    return value


def _relative(value: str) -> PurePosixPath:
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or any(x in ("..", ".") for x in p.parts) or "\\" in value:
        raise SkinError("Spritesheet path must remain inside the pet package.")
    return p


def _read_manifest(path: Path) -> dict:
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise SkinError("pet.json exceeds 32 KiB.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise SkinError("pet.json is not valid UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise SkinError("pet.json must be an object.")
    return value


def inspect_package(directory: str | Path, *, allow_v1: bool = False) -> dict:
    root = Path(directory).expanduser().resolve()
    manifest = _read_manifest(root / "pet.json")
    pet_id = slug(str(manifest.get("id", "")))
    name = manifest.get("displayName")
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise SkinError("displayName must contain 1–80 characters.")
    description = manifest.get("description", "")
    if not isinstance(description, str) or len(description) > 600:
        raise SkinError("description must contain at most 600 characters.")
    version = manifest.get("spriteVersionNumber", 1)
    if type(version) is not int or version not in (1, 2) or (version == 1 and not allow_v1):
        raise SkinError("New pets require spriteVersionNumber: 2. Use --allow-v1 only for an existing legacy pet.")
    relative = _relative(str(manifest.get("spritesheetPath", "")))
    image_path = root.joinpath(*relative.parts).resolve()
    if not image_path.is_relative_to(root) or not image_path.is_file():
        raise SkinError("Spritesheet is missing or points outside the package.")
    if image_path.stat().st_size > MAX_IMAGE_BYTES:
        raise SkinError("Spritesheet exceeds 20 MiB.")
    expected = (1536, 2288 if version == 2 else 1872)
    with Image.open(image_path) as source:
        if source.format not in ("PNG", "WEBP") or source.size != expected:
            raise SkinError(f"Expected transparent PNG/WebP {expected[0]}×{expected[1]}.")
        if "A" not in source.getbands() and "transparency" not in source.info:
            raise SkinError("Spritesheet has no encoded transparency.")
        image = source.convert("RGBA")
    alpha = image.getchannel("A")
    if any(alpha.getpixel(p) for p in [(0, 0), (1535, 0), (0, expected[1] - 1), (1535, expected[1] - 1)]):
        raise SkinError("Atlas corners must be fully transparent.")
    for row, count in enumerate(ROW_FRAMES[: expected[1] // 208]):
        for column in range(8):
            cell = alpha.crop((column * 192, row * 208, (column + 1) * 192, (row + 1) * 208))
            filled = sum(cell.histogram()[1:])
            used = column < count or (version == 2 and row == 0 and column == 6)
            if used and filled < 50:
                raise SkinError(f"Row {row}, frame {column} is empty.")
            if not used and filled:
                raise SkinError(f"Unused row {row}, frame {column} is not transparent.")
            if used and filled > 0.95 * 192 * 208:
                raise SkinError(f"Row {row}, frame {column} appears to contain a painted panel.")
    return {"id": pet_id, "name": name, "version": version, "width": expected[0], "height": expected[1],
            "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(), "image": str(image_path), "manifest": manifest}


@contextmanager
def package_source(source: str | Path, *, pet_id: str | None = None, name: str | None = None):
    source = Path(source).expanduser().resolve()
    if source.is_dir():
        yield source
        return
    if source.suffix.lower() == ".json":
        if source.name != "pet.json":
            raise SkinError("Choose pet.json or its package directory.")
        yield source.parent
        return
    with tempfile.TemporaryDirectory(prefix="whale-skin-") as temporary:
        root = Path(temporary)
        if source.suffix.lower() == ".zip":
            if source.stat().st_size > 32 * 1024 * 1024:
                raise SkinError("ZIP exceeds 32 MiB.")
            with zipfile.ZipFile(source) as archive:
                entries = archive.infolist()
                if len(entries) > 256 or sum(x.file_size for x in entries) > 48 * 1024 * 1024:
                    raise SkinError("ZIP expands beyond the skin package limit.")
                for entry in entries:
                    _relative(entry.filename.rstrip("/"))
                    if stat.S_ISLNK(entry.external_attr >> 16):
                        raise SkinError("ZIP symbolic links are not supported.")
                manifests = [x for x in entries if PurePosixPath(x.filename).name == "pet.json"]
                if len(manifests) != 1 or manifests[0].file_size > MAX_MANIFEST_BYTES:
                    raise SkinError("ZIP must contain exactly one pet.json.")
                manifest_entry = manifests[0]
                manifest = json.loads(archive.read(manifest_entry))
                if not isinstance(manifest, dict):
                    raise SkinError("pet.json must be an object.")
                relative = _relative(str(manifest.get("spritesheetPath", "")))
                member = str(PurePosixPath(manifest_entry.filename).parent.joinpath(relative))
                info = archive.getinfo(member)
                if info.file_size > MAX_IMAGE_BYTES:
                    raise SkinError("Spritesheet exceeds 20 MiB.")
                image_name = "spritesheet" + Path(member).suffix.lower()
                (root / image_name).write_bytes(archive.read(info))
                manifest["spritesheetPath"] = image_name
        else:
            if source.stat().st_size > MAX_IMAGE_BYTES:
                raise SkinError("Spritesheet exceeds 20 MiB.")
            with Image.open(source) as image:
                version = {2288: 2, 1872: 1}.get(image.height)
            manifest = {"id": slug(pet_id or "my-native-pet"), "displayName": name or source.stem,
                        "description": "Imported native Codex pet skin.", "spriteVersionNumber": version,
                        "spritesheetPath": "spritesheet" + source.suffix.lower()}
            shutil.copy2(source, root / manifest["spritesheetPath"])
        (root / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        yield root


def install(source: str | Path, *, home: str | Path | None = None, replace: bool = False,
            allow_v1: bool = False, pet_id: str | None = None, name: str | None = None) -> dict:
    home = codex_home(home)
    with package_source(source, pet_id=pet_id, name=name) as root:
        result = inspect_package(root, allow_v1=allow_v1)
        pets = home / "pets"
        destination = pets / result["id"]
        if destination.exists():
            try:
                old = inspect_package(destination, allow_v1=True)
            except (SkinError, OSError, ValueError):
                old = None
            normalized = dict(result["manifest"], spritesheetPath="spritesheet" + Path(result["image"]).suffix.lower())
            if old is not None and old["sha256"] == result["sha256"] and old["manifest"] == normalized:
                return {"installed": True, "changed": False, "path": str(destination), "id": result["id"], "sha256": result["sha256"]}
            if not replace:
                raise SkinError("A different pet already uses that ID. Pass --replace to create a backup and replace it.")
        pets.mkdir(parents=True, exist_ok=True)
        stage = pets / f".{result['id']}-{uuid.uuid4().hex}.tmp"
        stage.mkdir()
        backup = None
        try:
            image = Path(result["image"])
            image_name = "spritesheet" + image.suffix.lower()
            manifest = dict(result["manifest"], spritesheetPath=image_name)
            shutil.copy2(image, stage / image_name)
            (stage / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            inspect_package(stage, allow_v1=allow_v1)
            if destination.exists():
                backups = home / "pet-skin-backups"
                backups.mkdir(exist_ok=True)
                backup = backups / f"{result['id']}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:6]}"
                destination.rename(backup)
            try:
                stage.rename(destination)
            except OSError:
                if backup is not None and not destination.exists():
                    backup.rename(destination)
                raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return {"installed": True, "changed": True, "id": result["id"], "path": str(destination),
                "sha256": result["sha256"], "backup": str(backup) if backup else None,
                "activation": "Choose this pet in the desktop app's Settings > Pets. Installation alone does not prove activation."}


def doctor(home: str | Path | None = None) -> dict:
    root = codex_home(home)
    pets = []
    for folder in sorted((root / "pets").glob("*")):
        if not folder.is_dir() or folder.name.startswith("."):
            continue
        try:
            value = inspect_package(folder, allow_v1=True)
            pets.append({"id": value["id"], "name": value["name"], "version": value["version"], "valid": True, "sha256": value["sha256"]})
        except (OSError, ValueError, KeyError) as exc:
            pets.append({"id": folder.name, "valid": False, "error": str(exc)})
    return {"codex_home": str(root), "pets": pets, "task_driver": "Codex native status", "activation_verified": False}


def package_run(run: str | Path, destination: str | Path, *, pet_id: str, name: str) -> dict:
    run, destination = Path(run).resolve(), Path(destination).resolve()
    checks = {"atlas": run / "final/validation-extended.json", "frames": run / "qa/review.json",
              "blind": run / "qa/direction-blind-validation.json", "semantics": run / "qa/direction-semantics.json"}
    for key, path in checks.items():
        if not path.is_file():
            raise SkinError(f"Missing {key} QA report: {path.name}")
        value = json.loads(path.read_text())
        if key != "semantics" and value.get("ok") is not True:
            raise SkinError(f"{key} QA has not passed.")
        if key == "semantics":
            records = value.get("directions", value.get("verdicts", value))
            records = list(records.values()) if isinstance(records, dict) else records
            if not isinstance(records, list) or len(records) != 16 or any(not isinstance(x, dict) or x.get("verdict") not in ("pass", "warning") for x in records):
                raise SkinError("All 16 gaze directions need a passing or reviewed-warning semantic verdict.")
    image = run / "final/spritesheet-extended.webp"
    if destination.exists():
        raise SkinError("Output package already exists; choose a new versioned path.")
    destination.mkdir(parents=True)
    try:
        shutil.copy2(image, destination / "spritesheet.webp")
        manifest = {"id": slug(pet_id), "displayName": name, "description": "鲸娘原生桌宠；任务状态由 Codex 驱动。",
                    "spriteVersionNumber": 2, "spritesheetPath": "spritesheet.webp"}
        (destination / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = inspect_package(destination)
    except Exception:
        shutil.rmtree(destination)
        raise
    return {"packaged": True, "path": str(destination), "sha256": result["sha256"]}

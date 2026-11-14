"""Exercise Hatch's raster variant using the canonical behavioral cases in a full checkout."""

import importlib.util
import os
import unittest
from pathlib import Path


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None
) -> unittest.TestSuite:
    """Reuse fixtures while executing the shipped Hatch entrypoints, including its distinct fitter."""
    relative = Path(
        "chatgpt/oai-maintained-plugins/plugins/pets/skills/create-pet/tests/test_native_alpha_pipeline.py"
    )
    source = next(
        (
            parent / relative
            for parent in Path(__file__).resolve().parents
            if (parent / relative).is_file()
        ),
        None,
    )
    if source is None:
        raise unittest.SkipTest("Shared raster cases require both skill trees in the checkout")
    spec = importlib.util.spec_from_file_location("hatch_shared_raster_cases", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load shared raster cases from {source}")
    module = importlib.util.module_from_spec(spec)
    previous = os.environ.get("PET_TEST_SKILL_DIR")
    os.environ["PET_TEST_SKILL_DIR"] = str(Path(__file__).resolve().parents[1])
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            os.environ.pop("PET_TEST_SKILL_DIR", None)
        else:
            os.environ["PET_TEST_SKILL_DIR"] = previous
    return loader.loadTestsFromModule(module)

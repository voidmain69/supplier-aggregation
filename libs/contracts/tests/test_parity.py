"""Drift guard: generated models must stay in lockstep with the source-of-truth schemas.

If someone edits a schema in contracts/events/ without running `make contracts`, or adds
a schema without registering it, these tests fail — the models and the JSON Schemas can
never silently diverge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sa_contracts import EVENT_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_DIR = REPO_ROOT / "contracts" / "events"

SCHEMA_FILES = sorted(p for p in EVENTS_DIR.glob("*.json") if not p.name.startswith("_"))
SCHEMA_TITLES = [json.loads(p.read_text(encoding="utf-8"))["title"] for p in SCHEMA_FILES]


def _load(title: str) -> dict[str, Any]:
    for path in SCHEMA_FILES:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema["title"] == title:
            return schema
    raise AssertionError(f"no schema file for {title}")


def test_every_schema_is_registered_and_vice_versa() -> None:
    assert set(EVENT_REGISTRY) == set(SCHEMA_TITLES)


@pytest.mark.parametrize("title", SCHEMA_TITLES)
def test_model_properties_match_schema(title: str) -> None:
    schema = _load(title)
    model_schema = EVENT_REGISTRY[title].model.model_json_schema()

    assert set(model_schema["properties"]) == set(schema["properties"]), (
        f"{title}: model fields drifted from schema — run `make contracts`"
    )


@pytest.mark.parametrize("title", SCHEMA_TITLES)
def test_model_required_matches_schema(title: str) -> None:
    schema = _load(title)
    model_schema = EVENT_REGISTRY[title].model.model_json_schema()

    assert set(model_schema.get("required", [])) == set(schema.get("required", [])), (
        f"{title}: required fields drifted from schema — run `make contracts`"
    )

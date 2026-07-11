"""Validate event schemas in contracts/events/.

Checks:
  1. Every schema is valid JSON Schema (draft 2020-12).
  2. File name matches the `title` and the <domain>.<entity>.<past-action> convention.
  3. `schema_version` const is present and payloads forbid unknown fields (additionalProperties: false).
  4. Backward compatibility vs. the version on `main` (if git is available):
     removing required fields, removing properties or changing a property type is a breaking change.

Exit code != 0 on any violation. Run: uv run python tools/check_event_schemas.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from jsonschema.validators import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
EVENTS_DIR = ROOT / "contracts" / "events"
TYPE_RE = re.compile(r"^[a-z]+\.[a-z-]+\.[a-z-]+$")

errors: list[str] = []


def fail(path: Path, msg: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def load_main_version(rel_path: str) -> dict | None:
    try:
        out = subprocess.run(
            ["git", "show", f"origin/main:{rel_path}"],
            capture_output=True, text=True, cwd=ROOT, check=False,
        )
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except (OSError, json.JSONDecodeError):
        return None


def check_compatibility(path: Path, old: dict, new: dict) -> None:
    old_props = old.get("properties", {})
    new_props = new.get("properties", {})
    for name, spec in old_props.items():
        if name not in new_props:
            fail(path, f"BREAKING: property '{name}' was removed")
        elif spec.get("type") != new_props[name].get("type") and "enum" not in spec:
            fail(path, f"BREAKING: property '{name}' changed type {spec.get('type')} -> {new_props[name].get('type')}")
        elif "enum" in spec:
            removed = set(spec["enum"]) - set(new_props[name].get("enum", []))
            if removed:
                fail(path, f"BREAKING: enum values removed from '{name}': {sorted(removed)}")
    new_required = set(new.get("required", [])) - set(old.get("required", []))
    added_props = set(new_props) - set(old_props)
    for req in new_required:
        if req in added_props:
            fail(path, f"BREAKING: new property '{req}' must be optional, not required")


def main() -> int:
    schemas = sorted(EVENTS_DIR.glob("*.json"))
    if not schemas:
        print(f"no schemas found in {EVENTS_DIR}", file=sys.stderr)
        return 1

    for path in schemas:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(path, f"invalid JSON: {exc}")
            continue

        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # jsonschema raises SchemaError subclasses
            fail(path, f"invalid JSON Schema: {exc}")
            continue

        name = path.stem
        if name.startswith("_"):  # envelope and other meta files
            continue

        if not TYPE_RE.match(name):
            fail(path, "file name must be <domain>.<entity>.<past-tense-action>.json")
        if schema.get("title") != name:
            fail(path, f"schema title '{schema.get('title')}' must equal file name '{name}'")
        props = schema.get("properties", {})
        if "schema_version" not in props or "const" not in props.get("schema_version", {}):
            fail(path, "payload must declare 'schema_version' with a const value")
        if schema.get("additionalProperties") is not False:
            fail(path, "payload schemas must set additionalProperties: false")
        if not schema.get("description"):
            fail(path, "schema must have a description (topic, key, semantics) — it is read by LLMs too")

        old = load_main_version(str(path.relative_to(ROOT)).replace("\\", "/"))
        if old is not None:
            check_compatibility(path, old, schema)

    if errors:
        print("event schema check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"event schemas OK ({len(schemas)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

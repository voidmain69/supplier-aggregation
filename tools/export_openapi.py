"""Export each API service's OpenAPI schema to services/<name>/openapi.json.

Discovers services whose ``<pkg>.main`` exposes ``create_app`` and writes a deterministic
openapi.json for those that actually serve an API (non-empty paths). Commit the diff; CI
lints these with spectral and checks they are up to date.

Usage: uv run python tools/export_openapi.py
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"


def _package_name(service_dir: Path) -> str | None:
    src = service_dir / "src"
    if not src.exists():
        return None
    packages = [p.name for p in src.iterdir() if p.is_dir() and (p / "__init__.py").exists()]
    return packages[0] if packages else None


def main() -> int:
    written: list[str] = []
    for service_dir in sorted(p for p in SERVICES.iterdir() if p.is_dir()):
        package = _package_name(service_dir)
        if package is None:
            continue
        try:
            module = importlib.import_module(f"{package}.main")
        except ModuleNotFoundError:
            continue
        create_app = getattr(module, "create_app", None)
        if create_app is None:
            continue

        app = create_app()
        if not hasattr(app, "openapi"):
            continue  # not a REST app (e.g. the MCP gateway) — no OpenAPI to export
        schema = app.openapi()
        if not schema.get("paths"):
            continue  # no public API surface (e.g. a connector) — nothing to export

        out = service_dir / "openapi.json"
        out.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(str(out.relative_to(ROOT)))

    if written:
        print("exported:\n  " + "\n  ".join(written))
    else:
        print("no API services found")
    return 0


if __name__ == "__main__":
    sys.exit(main())

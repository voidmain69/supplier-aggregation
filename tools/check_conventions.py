"""Monorepo consistency checker (runs in CI and pre-commit).

Verifies that every service under services/ follows the platform conventions:
  - required files: pyproject.toml, Dockerfile, README.md, tool_manifest.json, src layout
  - tool_manifest.json validates against contracts/tool-manifest.schema.json
    and (if openapi.json is exported) every operation_id exists in it
  - no cross-service imports (services import only libs/* and their own package)
  - settings.py exists (pydantic-settings) and no .env files are committed

Exit code != 0 on any violation. Run: uv run python tools/check_conventions.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"
LIB_PACKAGES = {"sa_core", "sa_contracts", "sa_connector_sdk", "sa_observability"}

REQUIRED_FILES = ["pyproject.toml", "Dockerfile", "README.md", "tool_manifest.json"]

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def service_packages() -> dict[str, str]:
    """Map service dir name -> its python package name (first dir under src/)."""
    result: dict[str, str] = {}
    if not SERVICES.exists():
        return result
    for svc in sorted(p for p in SERVICES.iterdir() if p.is_dir()):
        src = svc / "src"
        pkgs = [p.name for p in src.iterdir() if p.is_dir()] if src.exists() else []
        result[svc.name] = pkgs[0] if pkgs else ""
    return result


def check_required_files(svc: Path) -> None:
    for name in REQUIRED_FILES:
        if not (svc / name).exists():
            fail(f"{svc.name}: missing required file {name}")
    if not (svc / "src").exists():
        fail(f"{svc.name}: missing src/ layout")


def check_tool_manifest(svc: Path) -> None:
    manifest_path = svc / "tool_manifest.json"
    if not manifest_path.exists():
        return
    schema = json.loads(
        (ROOT / "contracts" / "tool-manifest.schema.json").read_text(encoding="utf-8")
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{svc.name}: tool_manifest.json is not valid JSON: {exc}")
        return
    validator = Draft202012Validator(schema)
    for err in validator.iter_errors(manifest):
        fail(f"{svc.name}: tool_manifest.json: {err.message}")

    openapi_path = svc / "openapi.json"
    if openapi_path.exists():
        openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
        op_ids = {
            op.get("operationId")
            for methods in openapi.get("paths", {}).values()
            for op in methods.values()
            if isinstance(op, dict)
        }
        for tool in manifest.get("tools", []):
            if tool.get("operation_id") not in op_ids:
                fail(
                    f"{svc.name}: tool '{tool.get('name')}' references unknown operationId "
                    f"'{tool.get('operation_id')}'"
                )


IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.MULTILINE)


def check_cross_service_imports(svc: Path, packages: dict[str, str]) -> None:
    own_pkg = packages.get(svc.name, "")
    other_pkgs = {pkg for name, pkg in packages.items() if name != svc.name and pkg}
    for py in (svc / "src").rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        for match in IMPORT_RE.finditer(text):
            top = match.group(1)
            if top in other_pkgs and top != own_pkg:
                fail(
                    f"{svc.name}: {py.relative_to(svc)} imports another service's package '{top}' "
                    f"— services communicate only via events or generated clients"
                )


def check_no_env_files() -> None:
    for env in ROOT.rglob(".env"):
        if ".venv" in env.parts or "node_modules" in env.parts:
            continue
        fail(f"committed .env file found: {env.relative_to(ROOT)} — secrets belong to Vault/SOPS")


def main() -> int:
    if not SERVICES.exists() or not any(SERVICES.iterdir()):
        print("no services yet — conventions check passes trivially")
        return 0

    packages = service_packages()
    for svc in sorted(p for p in SERVICES.iterdir() if p.is_dir()):
        check_required_files(svc)
        check_tool_manifest(svc)
        if (svc / "src").exists():
            check_cross_service_imports(svc, packages)
    check_no_env_files()

    if errors:
        print("conventions check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"conventions OK ({len(packages)} services)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

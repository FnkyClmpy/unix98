"""Known Exherbo repository definitions and local git checkout management."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

OFFICIAL_REPOSITORIES = {
    "arbor": "https://gitlab.exherbo.org/exherbo/arbor.git",
    "desktop": "https://gitlab.exherbo.org/exherbo/desktop.git",
    "x11": "https://gitlab.exherbo.org/exherbo/x11.git",
}


def state_dir(override: str | None = None) -> Path:
    """Return PIE's user-owned state directory, without creating it on reads."""
    return Path(override or os.environ.get("PIE_STATE_DIR") or Path.home() / ".local/share/paludis-pie")


def _config_path(root: Path) -> Path:
    return root / "repositories.json"


def load(root: Path) -> dict[str, dict[str, str]]:
    path = _config_path(root)
    if not path.exists():
        return {}
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("repository configuration is not a JSON object")
    return content


def add(name: str, root: Path, url: str | None = None) -> dict[str, str]:
    if not name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("repository names may only use letters, digits, hyphens, and underscores")
    source = url or OFFICIAL_REPOSITORIES.get(name)
    if not source:
        raise ValueError(f"no built-in URL for '{name}'; provide --url")
    root.mkdir(parents=True, exist_ok=True)
    repositories = load(root)
    entry = {"url": source, "path": str(root / "repos" / name)}
    repositories[name] = entry
    _config_path(root).write_text(json.dumps(repositories, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry


def sync(name: str, root: Path) -> Path:
    repositories = load(root)
    if name not in repositories:
        raise ValueError(f"repository '{name}' is not configured; run 'paludis-pie repo add {name}' first")
    entry = repositories[name]
    location = Path(entry["path"])
    if location.exists():
        subprocess.run(["git", "-C", str(location), "pull", "--ff-only"], check=True)
    else:
        location.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", entry["url"], str(location)], check=True)
    return location


def _version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Natural-sort conventional Exheres versions without a shell or RPM call."""
    parts = re.findall(r"\d+|[A-Za-z]+", version)
    return tuple((1, int(part)) if part.isdigit() else (0, part.lower()) for part in parts)


def _recipe_version(candidate: Path, package: str) -> str:
    return candidate.name.removesuffix(".exheres-0").removeprefix(f"{package}-")


def resolve_recipe(name: str, root: Path, atom: str, version: str | None = None) -> Path:
    """Resolve a recipe from ``category/package``, preferring the latest stable version."""
    if "/" not in atom or atom.count("/") != 1:
        raise ValueError("package atom must be category/package, for example app-admin/chrpath")
    repositories = load(root)
    if name not in repositories:
        raise ValueError(f"repository '{name}' is not configured; run 'paludis-pie repo add {name}' first")
    category, package = atom.split("/", 1)
    recipe_dir = Path(repositories[name]["path"]) / "packages" / category / package
    candidates = sorted(recipe_dir.glob("*.exheres-0"))
    if not candidates:
        raise ValueError(f"no Exheres recipe found for {atom} in {name}; sync the repository first")
    if version:
        selected = [candidate for candidate in candidates if _recipe_version(candidate, package) == version]
        if not selected:
            choices = ", ".join(_recipe_version(candidate, package) for candidate in candidates)
            raise ValueError(f"version {version} is not available for {atom}; available: {choices}")
        return selected[0]
    stable = [candidate for candidate in candidates if _recipe_version(candidate, package) != "scm"]
    if stable:
        return max(stable, key=lambda candidate: _version_key(_recipe_version(candidate, package)))
    if len(candidates) > 1:
        choices = ", ".join(candidate.name for candidate in candidates)
        raise ValueError(f"only development recipes found for {atom}: {choices}; pass --version scm to select one")
    return candidates[0]


def synced_repositories(root: Path) -> dict[str, Path]:
    """Return configured repositories that have a local checkout."""
    return {
        name: Path(entry["path"])
        for name, entry in load(root).items()
        if Path(entry["path"]).is_dir()
    }

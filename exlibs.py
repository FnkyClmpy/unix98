"""Non-executing lookup and composition of Exheres Exlibs."""

from __future__ import annotations

from pathlib import Path

from .exheres import parse
from .model import ExheresPackage


def repository_root(recipe: Path) -> Path | None:
    """Find a repository root from a conventional ``packages/`` recipe path."""
    for ancestor in recipe.parents:
        if ancestor.name == "packages":
            return ancestor.parent
    return None


def _find_exlib(name: str, package: ExheresPackage, roots: list[Path]) -> Path | None:
    recipe = Path(package.path)
    candidates = [recipe.parent / f"{name}.exlib"]
    if package.category:
        candidates.append(recipe.parent.parent / "exlibs" / f"{name}.exlib")
    candidates.extend(root / "exlibs" / f"{name}.exlib" for root in roots)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def enrich(package: ExheresPackage, roots: list[Path]) -> ExheresPackage:
    """Merge static metadata from required Exlibs without evaluating shell code."""
    seen: set[str] = set()

    def visit(target: ExheresPackage) -> None:
        for name in list(target.required_exlibs):
            if name in seen:
                continue
            seen.add(name)
            location = _find_exlib(name, target, roots)
            if location is None:
                continue
            exlib = parse(location)
            visit(exlib)
            # Exlib metadata is inherited; the package recipe keeps precedence.
            for key, value in exlib.fields.items():
                package.fields.setdefault(key, value)
            for key, atoms in exlib.dependencies.items():
                package.dependencies.setdefault(key, [])
                package.dependencies[key] = sorted(set(package.dependencies[key] + atoms))
            package.loaded_exlibs.append(name)
            package.required_exlibs.extend(exlib.required_exlibs)
            if exlib.notes:
                package.notes.append(f"Exlib '{name}' contains dynamic or custom shell logic requiring an adapter")

    visit(package)
    package.required_exlibs = sorted(set(package.required_exlibs))
    package.loaded_exlibs = sorted(set(package.loaded_exlibs))
    return package

"""Translate Paludis atoms through an explicit Fedora mapping."""

from __future__ import annotations

import re

from .model import ExheresPackage, Translation
from .adapters import adapt

DEFAULT_MAP = {
    "dev-lang/python": "python3-devel",
    "dev-util/cmake": "cmake",
    "dev-util/ninja": "ninja-build",
    "sys-devel/gcc": "gcc",
    "sys-devel/make": "make",
    "virtual/pkg-config": "pkgconf-pkg-config",
}


def _translate_atom(atom: str, mapping: dict[str, str]) -> str | None:
    category_package = re.sub(r"^[<>=~]+", "", atom)
    return mapping.get(category_package)


def translate(package: ExheresPackage, mapping: dict[str, str] | None = None) -> Translation:
    names = {**DEFAULT_MAP, **(mapping or {})}
    build_atoms = package.dependencies.get("DEPENDENCIES", []) + package.dependencies.get("BUILD_DEPENDENCIES", [])
    runtime_atoms = package.dependencies.get("RDEPENDENCIES", [])
    unresolved: list[str] = []

    def resolve(atoms: list[str]) -> list[str]:
        result: list[str] = []
        for atom in atoms:
            translated = _translate_atom(atom, names)
            if translated:
                result.append(translated)
            else:
                unresolved.append(atom)
        return sorted(set(result))

    build_requires = resolve(build_atoms)
    runtime_requires = resolve(runtime_atoms)
    adapted_requires, adapter_notes, unknown_exlibs = adapt(package.required_exlibs)
    build_requires = sorted(set(build_requires + adapted_requires))
    unresolved.extend(f"exlib:{name}" for name in unknown_exlibs if name not in package.loaded_exlibs)
    adapter_notes.extend(
        f"loaded static metadata from Exlib '{name}'; custom phases still need an adapter"
        for name in package.loaded_exlibs
        if name not in {"autotools", "cmake", "meson"}
    )
    return Translation(build_requires, runtime_requires, sorted(set(unresolved)), adapter_notes)

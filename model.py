"""Domain objects used by PIE."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExheresPackage:
    path: str
    fields: dict[str, str] = field(default_factory=dict)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    required_exlibs: list[str] = field(default_factory=list)
    loaded_exlibs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        """Return the repository package name when this is a normal tree path."""
        parts = Path(self.path).parts
        if "packages" in parts:
            position = parts.index("packages")
            if len(parts) > position + 2:
                return parts[position + 2]
        return self.path.removesuffix(".exheres-0").rsplit("/", 1)[-1]

    @property
    def category(self) -> str | None:
        parts = Path(self.path).parts
        if "packages" in parts:
            position = parts.index("packages")
            if len(parts) > position + 2:
                return parts[position + 1]
        return None

    @property
    def version(self) -> str | None:
        """Infer the Exheres version from a conventional recipe filename."""
        filename = Path(self.path).name.removesuffix(".exheres-0")
        prefix = f"{self.name}-"
        if filename.startswith(prefix):
            return filename.removeprefix(prefix)
        return None


@dataclass
class Translation:
    build_requires: list[str]
    runtime_requires: list[str]
    unresolved: list[str]
    adapter_notes: list[str] = field(default_factory=list)

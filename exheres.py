"""Parse only a deliberately small, non-executing Exheres subset."""

from __future__ import annotations

import re
from pathlib import Path

from .model import ExheresPackage

_ASSIGNMENT_START = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*)=(?P<quote>['\"])(?P<value>.*)$")
_DEPENDENCY_KEYS = {"DEPENDENCIES", "BUILD_DEPENDENCIES", "RDEPENDENCIES"}
_REQUIRE = re.compile(r"^require\s+(?P<name>[A-Za-z0-9+_.-]+)(?:\s|$)")


def _atoms(value: str) -> list[str]:
    """Extract simple Paludis category/package atoms without evaluating syntax."""
    return re.findall(r"(?:[<>=~]{0,2})?[A-Za-z0-9+_.-]+/[A-Za-z0-9+_.@-]+", value)


def _labelled_atoms(value: str) -> dict[str, list[str]]:
    """Keep Exheres build/run labels without attempting to evaluate conditions."""
    result = {"BUILD_DEPENDENCIES": [], "RDEPENDENCIES": []}
    labels = {"build+run"}
    for raw_line in value.splitlines():
        line = raw_line.strip()
        label_match = re.match(r"^(build\+run|build|run|post|recommendation|suggestion|test|test-expensive|fetch|install):\s*(.*)$", line)
        if label_match:
            label, line = label_match.groups()
            labels = {label}
        atoms = _atoms(line)
        if not atoms:
            continue
        if labels & {"build+run", "build", "test", "test-expensive", "fetch", "install"}:
            result["BUILD_DEPENDENCIES"].extend(atoms)
        if labels & {"build+run", "run", "post", "recommendation", "suggestion"}:
            result["RDEPENDENCIES"].extend(atoms)
    return {key: sorted(set(atoms)) for key, atoms in result.items() if atoms}


def _safe_download_expansion(value: str, package: ExheresPackage) -> str | None:
    """Expand only static Exheres naming metadata used in DOWNLOADS.

    This deliberately does not execute Bash or expand environment variables.
    """
    version = package.version
    if not version:
        return None
    replacements = {
        "${HOMEPAGE}": package.fields.get("HOMEPAGE", ""),
        "${PN}": package.name,
        "${PV}": version,
        "${PNV}": f"{package.name}-{version}",
    }
    expanded = value
    for variable, replacement in replacements.items():
        expanded = expanded.replace(variable, replacement)
    return expanded if "$" not in expanded and "`" not in expanded and "$(" not in expanded else None


def parse(path: str | Path) -> ExheresPackage:
    source = Path(path)
    package = ExheresPackage(path=str(source))
    lines = source.read_text(encoding="utf-8").splitlines()
    line_index = 0
    while line_index < len(lines):
        line_no = line_index + 1
        raw_line = lines[line_index]
        line = raw_line.strip()
        if not line or line.startswith("#"):
            line_index += 1
            continue
        match = _ASSIGNMENT_START.match(line)
        if not match:
            required = _REQUIRE.match(line)
            if required:
                package.required_exlibs.append(required.group("name"))
                line_index += 1
                continue
            if "=" in line or "(" in line:
                package.notes.append(f"line {line_no}: unsupported shell syntax left for review")
            line_index += 1
            continue
        key, quote, value = match.group("key"), match.group("quote"), match.group("value")
        # Dynamic values cannot be safely interpreted. Handle these before
        # looking for a closing quote because Exheres may concatenate quoted
        # and unquoted fragments, e.g. WORK="${WORKBASE}"/${PN}.
        if key == "DOWNLOADS" and "$" in value:
            expanded = _safe_download_expansion(value, package)
            if expanded is not None:
                value = expanded
            else:
                package.notes.append(f"line {line_no}: dynamic expansion in {key} was not evaluated")
                line_index += 1
                continue
        elif "$" in value or "`" in value or "$((" in value:
            package.notes.append(f"line {line_no}: dynamic expansion in {key} was not evaluated")
            line_index += 1
            continue
        if value.endswith(quote):
            value = value[:-1]
        else:
            value_lines = [value]
            while line_index + 1 < len(lines):
                line_index += 1
                continuation = lines[line_index]
                if continuation.rstrip().endswith(quote):
                    value_lines.append(continuation.rstrip()[:-1])
                    break
                value_lines.append(continuation)
            else:
                package.notes.append(f"line {line_no}: unterminated value for {key}")
            value = "\n".join(value_lines)
        if key == "DOWNLOADS" and "$" in value:
            expanded = _safe_download_expansion(value, package)
            if expanded is not None:
                value = expanded
            else:
                package.notes.append(f"line {line_no}: dynamic expansion in {key} was not evaluated")
                line_index += 1
                continue
        elif "$" in value or "`" in value or "$((" in value:
            package.notes.append(f"line {line_no}: dynamic expansion in {key} was not evaluated")
            line_index += 1
            continue
        package.fields[key] = value
        if key == "DEPENDENCIES":
            for dependency_key, atoms in _labelled_atoms(value).items():
                package.dependencies[dependency_key] = atoms
            if value and not package.dependencies:
                package.notes.append(f"line {line_no}: no simple dependency atoms found in {key}")
        elif key in _DEPENDENCY_KEYS:
            package.dependencies[key] = _atoms(value)
            if value and not package.dependencies[key]:
                package.notes.append(f"line {line_no}: no simple dependency atoms found in {key}")
        line_index += 1
    return package

"""Reviewed, non-executing translations for common Exherbo Exlibs.

An adapter is intentionally much narrower than an Exlib: it records a Fedora
equivalent for a known pattern and never imports or evaluates the Exlib's Bash.
"""

from __future__ import annotations


EXLIB_BUILD_REQUIRES: dict[str, tuple[list[str], str]] = {
    "autotools": (
        ["autoconf", "automake", "libtool"],
        "autotools Exlib recognised; review the generated %build and %prep phases",
    ),
    "cmake": (
        ["cmake"],
        "cmake Exlib recognised; review the generated %build and %install phases",
    ),
    "meson": (
        ["meson", "ninja-build"],
        "meson Exlib recognised; review the generated %build and %install phases",
    ),
}


def adapt(exlibs: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return Fedora build requirements, review notes, and unknown Exlibs."""
    requirements: list[str] = []
    notes: list[str] = []
    unknown: list[str] = []
    for exlib in exlibs:
        adapter = EXLIB_BUILD_REQUIRES.get(exlib)
        if adapter is None:
            unknown.append(exlib)
            continue
        names, note = adapter
        requirements.extend(names)
        notes.append(note)
    return sorted(set(requirements)), sorted(set(notes)), sorted(set(unknown))

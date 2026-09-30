"""RPM spec scaffold renderer."""

from __future__ import annotations

import re

from .model import ExheresPackage, Translation


def _rpm_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9+_.-]", "-", name).lower()


def _source_url(downloads: str) -> str:
    """Use the URL side of Exheres' ``URL -> local-name`` syntax."""
    return downloads.split(" -> ", 1)[0].strip()


def render(package: ExheresPackage, translation: Translation) -> str:
    fields = package.fields
    name = _rpm_name(package.name)
    summary = fields.get("SUMMARY", f"TODO: package {name}")
    description = fields.get("DESCRIPTION", summary)
    homepage = fields.get("HOMEPAGE", "TODO: upstream URL")
    license_name = fields.get("LICENCES", "TODO: verify SPDX expression")
    source = _source_url(fields.get("DOWNLOADS", "TODO: source URL"))
    lines = [
        f"Name:           {name}",
        f"Version:        {package.version or 'TODO'}",
        "Release:        1%{?dist}",
        f"Summary:        {summary}",
        f"License:        {license_name}",
        f"URL:            {homepage}",
        f"Source0:        {source}",
        "",
    ]
    lines.extend(f"BuildRequires:  {item}" for item in translation.build_requires)
    lines.extend(f"Requires:       {item}" for item in translation.runtime_requires)
    lines.extend([
        "",
        "%description",
        description,
        "",
        "%prep",
        "%autosetup -n %{name}-%{version}",
        "",
        "%build",
        "# TODO: replace with the project's Fedora build command.",
        "",
        "%install",
        "# TODO: install into %{buildroot}; never install into the host filesystem.",
        "",
        "%check",
        "# TODO: run the upstream test suite if it is reliable and available.",
        "",
        "%files",
        "# TODO: list every packaged file explicitly.",
        "",
        "%changelog",
        "* Thu Sep 10 2026 PIE <noreply@example.invalid> - TODO-1",
        "- Initial porting scaffold.",
        "",
    ])
    return "\n".join(lines)

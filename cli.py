"""Command-line interface for PIE."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .exheres import parse
from .exlibs import enrich, repository_root
from .spec import render
from .translate import translate
from . import repositories


def _load_mapping(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError("mapping must be a JSON object of Exheres atoms to Fedora package names")
    return value


def _report(package, translation) -> dict:
    return {
        "package": package.name,
        "category": package.category,
        "metadata": package.fields,
        "dependencies": package.dependencies,
        "required_exlibs": package.required_exlibs,
        "loaded_exlibs": package.loaded_exlibs,
        "build_requires": translation.build_requires,
        "runtime_requires": translation.runtime_requires,
        "unresolved_atoms": translation.unresolved,
        "adapter_notes": translation.adapter_notes,
        "review_notes": package.notes,
    }


def _search(repository: Path, query: str) -> list[dict[str, str]]:
    """Search a local Exheres checkout; never executes recipes while indexing."""
    if not repository.is_dir():
        raise ValueError(f"repository directory does not exist: {repository}")
    needle = query.lower()
    hits: list[dict[str, str]] = []
    for recipe in repository.rglob("*.exheres-0"):
        package = parse(recipe)
        searchable = " ".join((package.name, package.fields.get("SUMMARY", ""))).lower()
        if needle in searchable:
            hits.append({
                "name": package.name,
                "atom": f"{package.category}/{package.name}" if package.category else package.name,
                "version": package.version or "unknown",
                "summary": package.fields.get("SUMMARY", "(no summary)"),
                "path": str(recipe),
            })
    return sorted(hits, key=lambda item: item["name"])


def _search_configured(root: Path, query: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for name, location in repositories.synced_repositories(root).items():
        for item in _search(location, query):
            hits.append({"repository": name, **item})
    return sorted(hits, key=lambda item: (item["name"], item["repository"]))


def _with_exlibs(package, state_root: Path | None = None):
    if state_root is not None:
        roots = list(repositories.synced_repositories(state_root).values())
    else:
        root = repository_root(Path(package.path))
        roots = [root] if root else []
    return enrich(package, roots)


def _plan(package, translation) -> dict:
    blockers: list[str] = []
    fields = package.fields
    for required in ("SUMMARY", "HOMEPAGE", "LICENCES", "DOWNLOADS", "SLOT", "PLATFORMS", "MYOPTIONS", "DEPENDENCIES"):
        if required not in fields:
            blockers.append(f"missing or unevaluated Exheres metadata: {required}")
    if translation.unresolved:
        blockers.append("unmapped Exherbo dependency atoms")
    if package.notes or translation.adapter_notes:
        blockers.append("recipe has shell logic or dynamic values requiring a porting rule")
    return {
        "package": f"{package.category}/{package.name}" if package.category else package.name,
        "ready_for_rpm_build": not blockers,
        "blockers": blockers,
        "next_step": "generate and review the RPM spec" if not blockers else "add translation rules or review the reported blockers",
    }


def _doctor() -> dict[str, dict[str, str | bool]]:
    tools = {
        "git": "repository synchronisation",
        "dnf": "installing built RPMs",
        "rpmbuild": "building RPM specs",
        "mock": "isolated Fedora builds",
    }
    return {
        name: {"available": shutil.which(name) is not None, "purpose": purpose}
        for name, purpose in tools.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paludis-pie", description="Conservative Exheres-to-Fedora RPM porting helper")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "port"):
        sub = commands.add_parser(name)
        sub.add_argument("source", help="recipe path, or repository name when porting an atom")
        sub.add_argument("package", nargs="?", help="category/package; only valid with 'port REPOSITORY'")
        sub.add_argument("--mapping", help="JSON atom-to-Fedora-name mapping")
    commands.choices["port"].add_argument("--output-dir", default=".", help="where to write generated files")
    commands.choices["port"].add_argument("--state-dir", help="override PIE's state directory")
    commands.choices["port"].add_argument("--version", help="exact Exheres version when using REPOSITORY ATOM")
    search = commands.add_parser("search", help="search configured Exheres repositories")
    search.add_argument("query", help="text to match against package name or summary")
    search.add_argument("--repo", help="optional direct path to a local Exheres repository checkout")
    search.add_argument("--state-dir", help="override PIE's state directory")
    info = commands.add_parser("info", help="show translated metadata for a repository package")
    info.add_argument("repository", help="configured repository name")
    info.add_argument("package", help="package atom, e.g. app-admin/chrpath")
    info.add_argument("--state-dir", help="override PIE's state directory")
    info.add_argument("--version", help="exact Exheres version")
    plan = commands.add_parser("plan", help="show whether a package is ready for a Fedora RPM build")
    plan.add_argument("repository", help="configured repository name")
    plan.add_argument("package", help="package atom, e.g. app-admin/chrpath")
    plan.add_argument("--mapping", help="JSON atom-to-Fedora-name mapping")
    plan.add_argument("--state-dir", help="override PIE's state directory")
    plan.add_argument("--version", help="exact Exheres version")
    commands.add_parser("doctor", help="check required Fedora build and installation tools")
    repo = commands.add_parser("repo", help="manage Exheres repository checkouts")
    repo_commands = repo.add_subparsers(dest="repo_command", required=True)
    repo_add = repo_commands.add_parser("add", help="add a known repository")
    repo_add.add_argument("name", help="repository name, e.g. arbor")
    repo_add.add_argument("--url", help="Git URL for a non-built-in repository")
    repo_sync = repo_commands.add_parser("sync", help="clone or update a configured repository")
    repo_sync.add_argument("name", help="repository name")
    repo_commands.add_parser("list", help="list configured repositories")
    repo.add_argument("--state-dir", help="override PIE's state directory (useful for testing)")
    args = parser.parse_args(argv)
    try:
        if args.command == "repo":
            root = repositories.state_dir(args.state_dir)
            if args.repo_command == "add":
                entry = repositories.add(args.name, root, args.url)
                print(f"Added {args.name}: {entry['url']}")
                print(f"Run: paludis-pie repo sync {args.name}")
                return 0
            if args.repo_command == "sync":
                location = repositories.sync(args.name, root)
                print(f"Repository {args.name} is ready at {location}")
                return 0
            print(json.dumps(repositories.load(root), indent=2, sort_keys=True))
            return 0
        if args.command == "search":
            if args.repo:
                hits = _search(Path(args.repo), args.query)
            else:
                hits = _search_configured(repositories.state_dir(args.state_dir), args.query)
            print(json.dumps(hits, indent=2))
            return 0
        if args.command == "doctor":
            print(json.dumps(_doctor(), indent=2, sort_keys=True))
            return 0
        if args.command in {"info", "plan"}:
            recipe = repositories.resolve_recipe(args.repository, repositories.state_dir(args.state_dir), args.package, args.version)
            package = _with_exlibs(parse(recipe), repositories.state_dir(args.state_dir))
            converted = translate(package, _load_mapping(getattr(args, "mapping", None)))
            report = _report(package, converted)
            if args.command == "plan":
                report["build_plan"] = _plan(package, converted)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if args.command == "inspect" and args.package:
            raise ValueError("inspect accepts a recipe path only")
        recipe = Path(args.source)
        if args.command == "port" and args.package:
            recipe = repositories.resolve_recipe(args.source, repositories.state_dir(args.state_dir), args.package, args.version)
        package = _with_exlibs(parse(recipe), repositories.state_dir(args.state_dir) if args.command == "port" and args.package else None)
        converted = translate(package, _load_mapping(args.mapping))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    report = _report(package, converted)
    if args.command == "inspect":
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = package.name.lower()
    spec_path = output / f"{stem}.spec"
    report_path = output / f"{stem}.pie-review.json"
    spec_path.write_text(render(package, converted), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Created {spec_path} and {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

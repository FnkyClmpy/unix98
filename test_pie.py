from pathlib import Path

from pie.exheres import parse
from pie.spec import render
from pie.translate import translate
from pie import repositories
from pie.exlibs import enrich


def test_parse_translate_and_render(tmp_path: Path):
    recipe = tmp_path / "hello.exheres-0"
    recipe.write_text(
        "SUMMARY=\"Friendly test package\"\n"
        "DEPENDENCIES=\"dev-lang/python dev-util/cmake unknown/pkg\"\n"
        "RDEPENDENCIES=\"dev-lang/python\"\n"
        "MY_DYNAMIC=\"${PV}\"\n",
        encoding="utf-8",
    )
    package = parse(recipe)
    result = translate(package)
    spec = render(package, result)
    assert result.build_requires == ["cmake", "python3-devel"]
    assert result.runtime_requires == ["python3-devel"]
    assert result.unresolved == ["unknown/pkg"]
    assert "BuildRequires:  cmake" in spec
    assert any("dynamic expansion" in item for item in package.notes)


def test_package_name_comes_from_exherbo_tree_path(tmp_path: Path):
    recipe = tmp_path / "repo" / "packages" / "app-admin" / "example" / "example-1.exheres-0"
    recipe.parent.mkdir(parents=True)
    recipe.write_text('SUMMARY="Example"\n', encoding="utf-8")
    package = parse(recipe)
    assert package.name == "example"
    assert package.category == "app-admin"


def test_multiline_exheres_labels_preserve_build_and_run_dependencies(tmp_path: Path):
    recipe = tmp_path / "labels.exheres-0"
    recipe.write_text(
        'DEPENDENCIES="\n'
        '    build+run: dev-lang/python\n'
        '    build: dev-util/cmake\n'
        '    run: app-admin/chrpath\n'
        '"\n',
        encoding="utf-8",
    )
    package = parse(recipe)
    assert package.dependencies["BUILD_DEPENDENCIES"] == ["dev-lang/python", "dev-util/cmake"]
    assert package.dependencies["RDEPENDENCIES"] == ["app-admin/chrpath", "dev-lang/python"]


def test_safe_exheres_download_variables_become_an_rpm_source(tmp_path: Path):
    recipe = tmp_path / "demo-1.2.exheres-0"
    recipe.write_text(
        'HOMEPAGE="https://example.invalid/"\n'
        'DOWNLOADS="${HOMEPAGE}demo-${PV}.tar.gz -> ${PNV}.tar.gz"\n',
        encoding="utf-8",
    )
    package = parse(recipe)
    spec = render(package, translate(package))
    assert package.version == "1.2"
    assert package.fields["DOWNLOADS"] == "https://example.invalid/demo-1.2.tar.gz -> demo-1.2.tar.gz"
    assert "Version:        1.2" in spec
    assert "Source0:        https://example.invalid/demo-1.2.tar.gz" in spec


def test_known_exlib_adds_reviewed_fedora_build_tools(tmp_path: Path):
    recipe = tmp_path / "tool-1.exheres-0"
    recipe.write_text("require autotools\n", encoding="utf-8")
    result = translate(parse(recipe))
    assert result.build_requires == ["autoconf", "automake", "libtool"]
    assert result.unresolved == []


def test_recipe_resolution_prefers_latest_stable_version(tmp_path: Path):
    repo = tmp_path / "repo"
    recipes = repo / "repos" / "desktop" / "packages" / "x11-apps" / "alacritty"
    recipes.mkdir(parents=True)
    for version in ("0.9.0", "0.17.0", "scm"):
        (recipes / f"alacritty-{version}.exheres-0").write_text("", encoding="utf-8")
    (repo / "repositories.json").write_text(
        '{"desktop": {"path": "' + str(repo / "repos" / "desktop") + '", "url": "https://example.invalid"}}',
        encoding="utf-8",
    )
    recipe = repositories.resolve_recipe("desktop", repo, "x11-apps/alacritty")
    assert recipe.name == "alacritty-0.17.0.exheres-0"


def test_package_local_exlib_contributes_static_metadata(tmp_path: Path):
    recipe_dir = tmp_path / "packages" / "x11-apps" / "demo"
    recipe_dir.mkdir(parents=True)
    (recipe_dir / "demo-1.exheres-0").write_text("require demo\n", encoding="utf-8")
    (recipe_dir / "demo.exlib").write_text(
        'SUMMARY="Demo app"\nDEPENDENCIES="run: dev-lang/python"\n', encoding="utf-8"
    )
    package = enrich(parse(recipe_dir / "demo-1.exheres-0"), [tmp_path])
    assert package.fields["SUMMARY"] == "Demo app"
    assert package.dependencies["RDEPENDENCIES"] == ["dev-lang/python"]
    assert package.loaded_exlibs == ["demo"]

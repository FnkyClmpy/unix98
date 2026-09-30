?

? (Paludis Integration for Fedora) is a porting assistant for bringing
Exherbo/Paludis packages to Fedora. It does not run Exheres files: they are
shell code, and executing them during a conversion would be both unsafe and
too distribution-specific.

Instead, ? reads the declarative subset of an .exheres-0 file, translates
known dependency atoms into Fedora BuildRequires, reports uncertain atoms, and
generates an RPM .spec scaffold for a maintainer to review.

Status

This is an intentionally conservative MVP. It supports common assignments
(SUMMARY, DESCRIPTION, HOMEPAGE, DOWNLOADS, LICENCES, SLOT) and
dependency variables (DEPENDENCIES, BUILD_DEPENDENCIES,
RDEPENDENCIES). Complex bash expansion, package choices, subslots, USE-like
conditionals, and custom phases are preserved as review notes rather than
guessed.

Run now (no pip required)

From this project folder, use the included launcher. It uses only Fedora's
system Python and the standard library:

./? inspect examples/hello.exheres-0
./? port examples/hello.exheres-0 --output-dir ./SPECS

To make ? available from any directory, run this once from the
project folder:

./install-user-command.sh

If ~/.local/bin is not already in your PATH, start a new terminal or run
export PATH="$HOME/.local/bin:$PATH" before using ?.

Search a repository and create a port

After you have a local checkout of an Exheres repository, search it without
executing any recipes:

? search ripgrep --repo /path/to/exheres-repository
? inspect /path/to/exheres-repository/category/pkg/pkg-1.0.exheres-0
? port /path/to/exheres-repository/category/pkg/pkg-1.0.exheres-0 --output-dir ./SPECS

? knows the official core repository, arbor, and can manage its own local
checkout. This does not install anything on your system:

? repo add arbor
? repo sync arbor
? repo list

The core desktop and x11 repositories are also built in. Desktop packages
such as Alacritty require the context supplied by arbor and x11, so sync
all three before attempting to port one:

? repo add x11
? repo sync x11
? repo add desktop
? repo sync desktop

The checkout is stored under ~/.local/share/?/repos/arbor. Search
that path, then pass the specific recipe returned by search to port.

For a package with exactly one recipe version, ? can resolve it by repository
and atom directly:

? port arbor app-admin/chrpath --output-dir ./SPECS

When a package has both stable and scm recipes, ? selects the newest stable
release by default. Select a specific version only when needed:

? info desktop x11-apps/alacritty --version 0.17.0

? understands Exheres' standard multi-line DEPENDENCIES block and retains
its build/run distinction. Conditionals, options, Exlibs, custom shell phases,
and multiple recipe versions are deliberately surfaced for review rather than
executed or guessed.

? also has an explicit, reviewed Exlib adapter registry. At present it
recognises autotools, cmake, and meson and adds their Fedora build tools;
it records phase translation as a review task. Unknown Exlibs are reported as
unresolved instead of being sourced as shell code.

Client workflow

Once one or more repositories are configured and synced, common operations do
not need filesystem paths:

? search chrpath
? info arbor app-admin/chrpath
? plan arbor app-admin/chrpath
? port arbor app-admin/chrpath --output-dir ./SPECS
? doctor

plan tells you whether ? has enough non-dynamic metadata and dependency
mappings to attempt an RPM build. doctor identifies whether git, dnf,
rpmbuild, and mock are installed. ? will not add an install command
until it can create an RPM and build it in an isolated environment; it must
never execute an Exheres recipe against the host system.

Optional Python installation
python -m pip install -e .
? inspect path/to/package.exheres-0
? port path/to/package.exheres-0 --output-dir ./rpmbuild/SPECS

? inspect produces a JSON report. ? port writes a spec scaffold and a
machine-readable review report beside it. Add project-local translations with
a JSON mapping file:

{
  "dev-lang/python": "python3-devel",
  "dev-util/cmake": "cmake"
}
? port pkg.exheres-0 --mapping fedora-map.json
Safety and scope

Generated specs are drafts, not shippable Fedora packages. Review licensing,
source URLs and hashes, dependency names, BuildRequires versus Requires,
scriptlets, tests, and Fedora Packaging Guidelines before building or
submitting anything.

? is not a replacement for dnf, rpmbuild, or Paludis. A future adapter
can invoke mock after a maintainer accepts the generated spec; keeping that
separate makes the conversion process auditable.

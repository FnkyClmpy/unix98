#!/usr/bin/env bash
# Install only a small symlink in the current user's local bin directory.
set -euo pipefail

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
user_bin="${HOME}/.local/bin"
mkdir -p "$user_bin"
ln -sfn "$project_dir/paludis-pie" "$user_bin/paludis-pie"
printf 'Installed %s\n' "$user_bin/paludis-pie"
printf 'Run: paludis-pie --help\n'

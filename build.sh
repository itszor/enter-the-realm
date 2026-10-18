#!/bin/sh
# Build Enter the Realm from your own copy of the discs:
#     ./build.sh "Enter the Realm (1991)(The Fourth Dimension)(Disk 1 of 3).adf" ... (all three)
# then: cd recomp && ./enterrealm
# The steps are recipe.json's "build", run by SuperSpider's tools/weave.py.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SUPERSPIDER="${SUPERSPIDER:-$HOME/stuff/superspider}"
[ $# -gt 0 ] || { echo "usage: $0 DISC1.adf DISC2.adf DISC3.adf | GAME.zip" >&2; exit 2; }
(cd "$SUPERSPIDER" && dune build)
WEAVE_RECIPES="$HERE" exec python3 -I "$SUPERSPIDER/tools/weave.py" build "$@"

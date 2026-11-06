#!/usr/bin/env bash
# Report hostcd release download counts (how many times the installer and the
# binaries were pulled from GitHub Releases — the authoritative download signal,
# since the product is served from github.com, not from the website).
#
#   ./scripts/download-stats.sh [owner/repo]   # default: Inblade/hostcd-dist
set -euo pipefail
REPO="${1:-Inblade/hostcd-dist}"
command -v gh >/dev/null || { echo "need the GitHub CLI (gh) authenticated"; exit 1; }
command -v jq >/dev/null || { echo "need jq"; exit 1; }

echo "# hostcd downloads — $REPO  ($(date -u +%FT%TZ))"
echo
printf '  %-14s %-34s %8s\n' "release" "asset" "count"
gh api "repos/$REPO/releases" --paginate \
  -q '.[] | .tag_name as $t | .assets[]? | "\($t)\t\(.name)\t\(.download_count)"' \
  | sort \
  | awk -F'\t' '
      { printf "  %-14s %-34s %8d\n", $1, $2, $3; grand+=$3; byname[$2]+=$3 }
      END {
        print  "\n# totals by asset"
        for (n in byname) printf "  %-34s %8d\n", n, byname[n]
        printf "\n# grand total: %d downloads\n", grand
      }'

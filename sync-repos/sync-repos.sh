#!/usr/bin/env bash
# Switch each NDF repo to its expected branch and fast-forward it, all repos in
# parallel. Never stashes, resets, cleans, or forces. Repos with tracked changes
# are not switched (but are still fast-forwarded if already on the right branch).
#
# Uses `git fetch` + `git merge --ff-only origin/<branch>` instead of `git pull`:
# pull merges whatever FETCH_HEAD lists, and a concurrent fetch (e.g. VS Code
# auto-fetch) can leave duplicate entries there -> "Cannot fast-forward to
# multiple branches". The remote-tracking ref is updated atomically, so it's safe.
#
# Usage: sync-repos.sh [repo:branch ...]   (defaults to the REPOS list below)
#
# Repos root: $SYNC_REPOS_ROOT if set, otherwise the folder containing
# .claude/skills/sync-repos/ (three levels above this script).

ROOT="${SYNC_REPOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"

REPOS=(
  "ndf-automationpj-etl-pipeline-db-migration:develop"
  "ndf-automationpj-etl-pipeline-file-conversion:develop"
  "ndf-automationpj-etl-service-file-validation:develop"
  "ndf-claude-code:master"
  "ndf-frontend:new-world-develop"
  "ndf-replacement-match-llm:develop"
  "ndf-s3explorer-etl-api:develop"
  "ndf-system-discontinued-db:develop"
  "ndf-xref-frontend-dashboard:develop"
)
[ "$#" -gt 0 ] && REPOS=("$@")

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Flatten git output so it fits in one table cell / report line.
clean() { local s="${1//$'\r'/}"; s="${s//$'\n'/ }"; printf '%s' "${s//|//}"; }

# Writes "status|detail|now_on|head|vs_origin|tree" to $tmp/<idx>.
sync_one() {
  local idx="$1" repo="$2" branch="$3" dir="$ROOT/$2"
  local status detail="" out before after now head vs tree n

  if [ ! -d "$dir/.git" ]; then
    printf 'skipped|not a git repo / missing: %s|-|-|-|-\n' "$dir" > "$tmp/$idx"
    return
  fi

  if ! out=$(git -C "$dir" fetch origin 2>&1); then
    status="FAILED"; detail="fetch: $(clean "$out")"
  else
    now=$(git -C "$dir" rev-parse --abbrev-ref HEAD)
    if [ "$now" != "$branch" ] && [ -n "$(git -C "$dir" status --porcelain --untracked-files=no)" ]; then
      status="skipped"; detail="tracked changes on $now, not switched to $branch"
    elif [ "$now" != "$branch" ] && ! out=$(git -C "$dir" checkout "$branch" 2>&1); then
      status="FAILED"; detail="checkout $branch: $(clean "$out")"
    else
      before=$(git -C "$dir" rev-parse --short HEAD)
      if ! out=$(git -C "$dir" merge --ff-only "origin/$branch" 2>&1); then
        status="FAILED"; detail="fast-forward to origin/$branch: $(clean "$out")"
      else
        after=$(git -C "$dir" rev-parse --short HEAD)
        if [ "$before" = "$after" ]; then status="up to date"; else status="updated $before→$after"; fi
      fi
    fi
  fi

  # Post-run state, collected even after a failure.
  now=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  head=$(git -C "$dir" rev-parse --short HEAD 2>/dev/null || echo "?")
  if [ "$now" = "$branch" ] && n=$(git -C "$dir" rev-list --left-right --count "HEAD...origin/$branch" 2>/dev/null); then
    read -r a b <<< "$n"
    if [ "$a" = 0 ] && [ "$b" = 0 ]; then vs="in sync"; else vs="↑$a ↓$b"; fi
  else
    vs="n/a"
  fi
  n=$(git -C "$dir" status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" = 0 ]; then tree="clean"; else tree="$n changed"; fi

  printf '%s|%s|%s|%s|%s|%s\n' "$status" "$detail" "$now" "$head" "$vs" "$tree" > "$tmp/$idx"
}

start=$SECONDS
for i in "${!REPOS[@]}"; do
  entry="${REPOS[$i]}"
  sync_one "$i" "${entry%%:*}" "${entry#*:}" &
done
wait

ok=0 skipped=0 failed=0
problems=()
echo "| # | Repo | Target | Now on | HEAD | vs origin | Working tree | Result |"
echo "|---|------|--------|--------|------|-----------|--------------|--------|"
for i in "${!REPOS[@]}"; do
  entry="${REPOS[$i]}"; repo="${entry%%:*}"; branch="${entry#*:}"
  if [ -s "$tmp/$i" ]; then
    IFS='|' read -r status detail now head vs tree < "$tmp/$i"
  else
    status="FAILED"; detail="no result written (job crashed)"; now="?"; head="?"; vs="?"; tree="?"
  fi
  [ "$now" != "$branch" ] && [ "$now" != "-" ] && now="$now ≠"
  case "$status" in
    FAILED)  result="❌ FAILED";  failed=$((failed + 1));   problems+=("❌ **$repo** — $detail") ;;
    skipped) result="⚠️ skipped"; skipped=$((skipped + 1)); problems+=("⚠️ **$repo** — $detail") ;;
    *)       result="✅ $status"; ok=$((ok + 1)) ;;
  esac
  echo "| $((i + 1)) | $repo | $branch | $now | $head | $vs | $tree | $result |"
done

echo
echo "**$ok ok, $skipped skipped, $failed failed** ($((SECONDS - start))s)"
if [ "${#problems[@]}" -gt 0 ]; then
  echo
  echo "### Problems"
  printf -- '- %s\n' "${problems[@]}"
fi

[ "${#problems[@]}" -eq 0 ]

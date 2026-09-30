---
name: sync-repos
description: Switch every NDF repo in the repos root folder to its expected branch (develop / master / new-world-develop) and fast-forward it, all repos in parallel, then report each repo's status. Use when asked to sync, update, or reset the repos to their working branches.
---

# Sync NDF repos

Run the sync script with the Bash tool:

```bash
bash "${CLAUDE_SKILL_DIR}/sync-repos.sh"
```

The repos root is the folder that contains `.claude/skills/sync-repos/`, i.e. the skill is meant to live in `<repos-root>/.claude/skills/sync-repos/` alongside the cloned repos. If the skill is installed elsewhere (e.g. `~/.claude/skills/`), set the root explicitly: `SYNC_REPOS_ROOT="/c/path/to/repos" bash "${CLAUDE_SKILL_DIR}/sync-repos.sh"`.

The script contains the repo → branch map. It processes all repos in parallel (one background job per repo). For each repo it runs `git fetch origin`, switches to the target branch if the repo is on a different one, then runs `git merge --ff-only origin/<branch>`.

It does not use `git pull`. A pull merges whatever `.git/FETCH_HEAD` lists, and a concurrent fetch (such as VS Code's `git.autofetch`) can leave duplicate entries there, which causes `Cannot fast-forward to multiple branches`. Merging the remote-tracking ref avoids this, so VS Code auto-fetch does not need to be turned off.

To sync only some repos, pass `repo:branch` arguments, e.g. `sync-repos.sh ndf-frontend:new-world-develop`.

After it finishes:
- Show the user the markdown report exactly as printed. It contains the per-repo table, the ok/skipped/failed summary, and a **Problems** section when anything went wrong.
- For every ⚠️ skipped or ❌ FAILED row, explain why it happened, based on the Problems entry. Common causes:
  - uncommitted tracked changes blocked a branch switch
  - a diverged branch (local commits, shown as `↑N`) blocked the fast-forward
  - an auth or network error
  - a lock-file error (`index.lock` / `*.lock exists`) from another git process running in that repo at the same time
- For AWS/SSO or git credential errors, suggest the user fix it themselves (e.g. `! git fetch` in that repo).
- Do NOT stash, reset, clean, force-checkout, or merge to work around a skipped or failed repo. Ask the user how they want to handle it. For a transient lock error, it's fine to offer to re-run the script for that one repo.

To change which branch a repo tracks, edit the `REPOS` array in `sync-repos.sh`.

# LeetCode → GitHub Sync

Automatically downloads all your solved LeetCode problems and publishes them as a live GitHub Pages website with a full LeetCode-style UI — problem descriptions, examples, constraints, hints, and your complete Python solutions.

This tool doesn't host your solutions itself — it creates and pushes to a **separate output repo** (named `leetcode-solutions` by default, configurable via `REPO_NAME` below) that holds your actual problems and serves the live site. Every `leetcode-solutions` mentioned in this README refers to that output repo, not this one.

**Live site:** `https://<your-username>.github.io/leetcode-solutions/` (available after enabling GitHub Pages)

---

## Why this exists

LeetCode is great for solving problems, but it's a poor long-term home for your work:

- **If LeetCode goes offline or your account is lost, your solutions are gone.** This repo keeps a permanent copy under your control.
- **LeetCode's submission history is hard to browse.** No search, no filtering by topic, no way to see your solution alongside the problem description.
- **You can't share your work easily.** A GitHub Pages site gives you a clean, public URL to point to.
- **No version history.** If you improve a solution, the old one disappears. Git preserves every version.
- **LeetCode premium problems are only accessible with a subscription.** Once scraped, your local copy of the problem + solution stays with you regardless.

---

## Usage

**Double-click `sync.command`** in this folder.

- First time: prompts for your GitHub token, saves it, then syncs
- Every time after: just syncs — no prompts, nothing to fill in

Make sure you're logged in to [leetcode.com](https://leetcode.com) in Chrome before running.

---

## How it works

Each sync is fully incremental — only does what's needed:

1. Reads your LeetCode cookies from Chrome automatically
2. Fetches your solved problem list from LeetCode
3. Scrapes any new problems not yet downloaded
4. Re-checks existing problems — if you resubmitted a better solution, it picks up the new code automatically
5. Regenerates the site
6. Compares each file's checksum with GitHub — only uploads changed files

So if you solved 1 new problem, it fetches that 1 problem and uploads ~4 files. If you improved an existing solution, only that solution + the site index gets uploaded. If nothing changed, it uploads 0 files.

---

## Configuration

Before first use, update these values in `auto_sync.py`:

| Field | Where | What to set |
|-------|-------|-------------|
| `GITHUB_USERNAME` | `auto_sync.py` line ~128 | Your GitHub username |
| `REPO_NAME` | `auto_sync.py` line ~129 | Name of the repo to push solutions to |
| `LIST_SLUG` | `auto_sync.py` line ~126 | Your LeetCode list ID (from the list URL) |

The `LIST_SLUG` is the random string at the end of your LeetCode list URL, e.g. `https://leetcode.com/list/n4zbe2xg/` → `n4zbe2xg`.

---

## Prerequisites (one-time install)

```bash
pip3 install requests pycookiecheat
```

---

## GitHub token

When prompted on first run, create a token at [github.com/settings/tokens/new](https://github.com/settings/tokens/new):
- Note: `leetcode-sync`
- Expiration: No expiration
- Scope: check **`repo`**

Saved to `~/.leetcode_sync` and reused automatically on every future run.

---

## Enabling GitHub Pages (one-time)

After the first sync:

1. Go to your `leetcode-solutions` repo on GitHub
2. **Settings** → **Pages** → Source: **Deploy from a branch** → branch: **main** → **/ (root)** → Save

Your site goes live at `https://<your-username>.github.io/leetcode-solutions/` in ~1 minute and stays live permanently.

---

## Adding problems that aren't on LeetCode

Company interview questions or other non-LeetCode problems won't show up via the scraper, but you can still get them onto the site and into the repo README.

Add a folder under `unknown/`, following the same shape as a scraped problem:

```
unknown/
  My-Problem-Name/
    README.md      ← first line must be "# N. Title" (N = any number you choose)
    solution.py
```

Every sync copies `unknown/` into `output/Unknown/` before the site is generated, so these problems get their own `index.html`, a badge/filter on the root site, and a "❓ Unknown" section in the repo README — regenerated safely alongside the scraped ones.

`unknown/` is gitignored, same as `output/` — it's local, personal staging, not committed to this tool repo. The permanent record ends up committed in your `leetcode-solutions` repo once synced, same as every scraped problem. (This also means: if you ever start fresh on a new machine, recopy any `unknown/` problems from your `leetcode-solutions` repo's `Unknown/` folder before your first sync there, or they'll fall out of future regenerations.)

---

## Troubleshooting

**`401 Unauthorized` from GitHub** — Token expired. Delete `~/.leetcode_sync` and re-run `sync.command` to enter a new one.

**`400 Bad Request` from LeetCode** — Session expired. Log out and back in to leetcode.com in Chrome, then re-run.

**`No accepted Python solution found`** — Only Python3 submissions are fetched. Other languages are skipped.

---

## Project structure

```
leetcode_to_github/
  sync.command         ← double-click to run
  auto_sync.py         ← automation script
  run.py               ← sync pipeline
  leetcode_scraper.py  ← fetches problems + solutions from LeetCode
  generate_site.py     ← builds the HTML site
  github_uploader.py   ← uploads only changed files to GitHub
  config.py            ← auto-generated, cleared after each run
  output/              ← downloaded problems + generated site
  unknown/             ← manually-authored, non-LeetCode problems (local only)
```

Each file has a single responsibility so the pipeline stays easy to debug and extend:

- **`sync.command`** is the entry point — a double-clickable shell script so no terminal is needed.
- **`auto_sync.py`** handles everything outside the core sync: reading Chrome cookies, loading the GitHub token, writing `config.py` with credentials, and clearing it afterwards so secrets never sit on disk.
- **`run.py`** is the pipeline runner — it validates config and calls each stage in order. Keeping it separate from `auto_sync.py` means you can run the pipeline directly if needed (e.g. for testing with a manually written `config.py`).
- **`leetcode_scraper.py`** owns all LeetCode API communication. Isolated so changes to LeetCode's GraphQL API only require edits here.
- **`generate_site.py`** owns all HTML generation. Isolated so you can redesign the site without touching scraping or upload logic.
- **`github_uploader.py`** owns all GitHub API communication. Contains the blob SHA diffing logic so only changed files are pushed.
- **`config.py`** is intentionally gitignored — it's written just before each sync and wiped immediately after, so credentials are never committed.
- **`output/`** is gitignored — it's local working storage. The uploader pushes its contents to the `leetcode-solutions` repo, not this one.
- **`unknown/`** is gitignored, same as `output/` — it's per-user local staging for problems the scraper can't find on its own. The permanent record lives in your `leetcode-solutions` repo once synced, not in this tool repo, so cloning this tool never leaks anyone's personal problem content.

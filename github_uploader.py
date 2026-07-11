"""
github_uploader.py
-------------------
Creates a GitHub repo (if it doesn't exist) and uploads all scraped
problem folders to it, preserving the exact folder structure.

Structure uploaded:
  Easy/
    0001-Two-Sum/
      README.md
      solution.py
  Medium/
    ...
  Hard/
    ...
  README.md   ← auto-generated index of all problems

Requirements:
  pip install requests pycookiecheat

Usage:
  Called automatically by run.py — no need to run directly.
"""

import os
import re
import base64
import time
import json
import hashlib
import requests
from typing import Optional


GITHUB_API = "https://api.github.com"


# ── GitHub session ────────────────────────────────────────────────────────────

def make_github_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "leetcode-to-github-uploader",
    })
    return s


# ── Repo creation ─────────────────────────────────────────────────────────────

def ensure_repo(session: requests.Session, username: str, repo_name: str, private: bool = False) -> str:
    """Create repo if it doesn't exist. Returns full_name (owner/repo)."""
    # check if exists
    r = session.get(f"{GITHUB_API}/repos/{username}/{repo_name}")
    if r.status_code == 200:
        print(f"✅ Repo already exists: https://github.com/{username}/{repo_name}")
        return r.json()["full_name"]

    # create it
    payload = {
        "name": repo_name,
        "description": "My LeetCode solutions — auto-synced",
        "private": private,
        "auto_init": True,
        "has_issues": False,
        "has_projects": False,
        "has_wiki": False,
    }
    r = session.post(f"{GITHUB_API}/user/repos", json=payload)
    r.raise_for_status()
    repo = r.json()
    print(f"🎉 Created repo: {repo['html_url']}")
    time.sleep(2)  # let GitHub initialize the default branch
    return repo["full_name"]


# ── File upload ───────────────────────────────────────────────────────────────

def get_file_sha(session: requests.Session, full_name: str, path: str) -> Optional[str]:
    """Return the blob SHA of an existing file, or None if it doesn't exist."""
    r = session.get(f"{GITHUB_API}/repos/{full_name}/contents/{path}")
    if r.status_code == 200:
        return r.json().get("sha")
    return None


def upload_file(
    session: requests.Session,
    full_name: str,
    repo_path: str,
    content,
    commit_message: str,
):
    """Create or update a file in the repo."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    encoded = base64.b64encode(content).decode("utf-8")

    sha = get_file_sha(session, full_name, repo_path)

    payload = {
        "message": commit_message,
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    r = session.put(
        f"{GITHUB_API}/repos/{full_name}/contents/{repo_path}",
        json=payload,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed ({r.status_code}): {r.text[:300]}")

    return r.json()


# ── Git blob SHA (matches GitHub's SHA for comparison) ────────────────────────

def git_blob_sha(content: bytes) -> str:
    """Compute the same SHA GitHub uses for blob comparison."""
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


# ── Fetch existing repo tree ──────────────────────────────────────────────────

def get_remote_tree(session: requests.Session, full_name: str) -> dict:
    """Return {repo_path: sha} for all files currently in the repo."""
    r = session.get(f"{GITHUB_API}/repos/{full_name}/git/trees/HEAD?recursive=1")
    if r.status_code != 200:
        return {}
    tree = r.json().get("tree", [])
    return {item["path"]: item["sha"] for item in tree if item["type"] == "blob"}


# ── Walk output dir and upload ─────────────────────────────────────────────────

def upload_all(
    github_token: str,
    github_username: str,
    repo_name: str,
    output_dir: str,
    private: bool = False,
):
    session = make_github_session(github_token)
    full_name = ensure_repo(session, github_username, repo_name, private)

    # Gather all local files
    all_files = []
    for root, dirs, files in os.walk(output_dir):
        dirs.sort()
        for fname in sorted(files):
            local_path = os.path.join(root, fname)
            repo_path = os.path.relpath(local_path, output_dir).replace("\\", "/")
            all_files.append((local_path, repo_path))

    # Fetch current remote state to skip unchanged files
    print("\n🔍 Checking for changes...")
    remote_tree = get_remote_tree(session, full_name)

    files_to_upload = []
    for local_path, repo_path in all_files:
        with open(local_path, "rb") as f:
            file_content = f.read()
        local_sha = git_blob_sha(file_content)
        if remote_tree.get(repo_path) != local_sha:
            files_to_upload.append((local_path, repo_path, file_content))

    skipped = len(all_files) - len(files_to_upload)
    if skipped:
        print(f"⏭️  {skipped} files unchanged — skipping.")

    if not files_to_upload:
        print("✅ Everything is up to date. Nothing to upload.")
        print(f"\n🔗 View your repo: https://github.com/{full_name}")
        return f"https://github.com/{full_name}"

    total = len(files_to_upload)
    print(f"📤 Uploading {total} changed file(s) to github.com/{full_name} ...\n")

    uploaded = 0
    errors = []

    for i, (local_path, repo_path, file_content) in enumerate(files_to_upload, 1):
        try:
            parts = repo_path.split("/")
            if len(parts) >= 2:
                msg = f"Add {parts[-2]}" if parts[-1] == "solution.py" else f"Update {repo_path}"
            else:
                msg = f"Update {repo_path}"

            upload_file(session, full_name, repo_path, file_content, msg)
            uploaded += 1
            print(f"  [{i}/{total}] ✅ {repo_path}")

        except Exception as e:
            errors.append((repo_path, str(e)))
            print(f"  [{i}/{total}] ❌ {repo_path} — {e}")

        time.sleep(0.4)

    print(f"\n{'='*60}")
    print(f"Uploaded {uploaded}/{total} changed files.")
    if errors:
        print("\nErrors:")
        for path, err in errors:
            print(f"  - {path}: {err}")

    print(f"\n🔗 View your repo: https://github.com/{full_name}")
    return f"https://github.com/{full_name}"


# ── Auto-generated repo README ────────────────────────────────────────────────

def build_repo_readme(output_dir: str, repo_url: str) -> str:
    """Walk the output dir and generate a nice index README.md."""
    lines = [
        "# 🧠 LeetCode Solutions",
        "",
        f"> 🌐 [View Live Site](https://debneilroy.github.io/leetcode-solutions/)",
        "",
        "## Progress",
        "",
    ]

    counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Unknown": 0}
    table_rows = {"Easy": [], "Medium": [], "Hard": [], "Unknown": []}

    for difficulty in ["Easy", "Medium", "Hard", "Unknown"]:
        diff_dir = os.path.join(output_dir, difficulty)
        if not os.path.isdir(diff_dir):
            continue
        for folder in sorted(os.listdir(diff_dir)):
            folder_path = os.path.join(diff_dir, folder)
            if not os.path.isdir(folder_path):
                continue
            # parse number and title from folder name like "0001-Two-Sum"
            m = re.match(r"(\d+)-(.*)", folder)
            if m:
                num = str(int(m.group(1)))
                title = m.group(2).replace("-", " ")
            else:
                # Unnumbered folders (e.g. manually-authored "Unknown" problems)
                # fall back to the README's "# N. Title" heading line
                num, title = "?", folder.replace("-", " ")
                readme_path = os.path.join(folder_path, "README.md")
                if os.path.isfile(readme_path):
                    with open(readme_path, "r", encoding="utf-8") as rf:
                        head_m = re.search(r"^# (\d+)\. (.+)$", rf.read(), re.MULTILINE)
                    if head_m:
                        num, title = head_m.group(1), head_m.group(2).strip()
            counts[difficulty] += 1
            table_rows[difficulty].append((num, title, folder))

    total = sum(counts.values())
    lines += [
        f"| Difficulty | Solved |",
        f"|------------|--------|",
        f"| 🟢 Easy    | {counts['Easy']} |",
        f"| 🟡 Medium  | {counts['Medium']} |",
        f"| 🔴 Hard    | {counts['Hard']} |",
        f"| ❓ Unknown | {counts['Unknown']} |",
        f"| **Total**  | **{total}** |",
        "",
    ]

    for difficulty, emoji in [("Easy", "🟢"), ("Medium", "🟡"), ("Hard", "🔴"), ("Unknown", "❓")]:
        rows = table_rows[difficulty]
        if not rows:
            continue
        lines += [
            f"## {emoji} {difficulty}",
            "",
            "| # | Title | Solution |",
            "|---|-------|----------|",
        ]
        for num, title, folder in rows:
            readme_link = f"{difficulty}/{folder}/README.md"
            sol_link = f"{difficulty}/{folder}/solution.py"
            lines.append(f"| {num} | [{title}]({readme_link}) | [Python]({sol_link}) |")
        lines.append("")

    return "\n".join(lines)

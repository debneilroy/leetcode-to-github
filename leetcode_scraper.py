"""
leetcode_scraper.py
--------------------
Fetches all solved problems from a LeetCode problem list and saves them locally
in full LeetCode format:

  output/
    Easy/
      0001-Two-Sum/
        README.md      ← problem statement, examples, constraints
        solution.py    ← your latest accepted Python solution (updated if you resubmit)
    Medium/
      ...
    Hard/
      ...

Requirements:
  pip install requests

Usage:
  Set LEETCODE_SESSION and CSRF_TOKEN in config.py, then run:
    python run.py
"""

import requests
import os
import re
import json
import time
from typing import Optional

# ── GraphQL helpers ──────────────────────────────────────────────────────────

BASE_URL = "https://leetcode.com"
GRAPHQL_URL = f"{BASE_URL}/graphql"


def make_session(leetcode_session: str, csrf_token: str) -> requests.Session:
    s = requests.Session()
    s.cookies.set("LEETCODE_SESSION", leetcode_session, domain="leetcode.com")
    s.cookies.set("csrftoken", csrf_token, domain="leetcode.com")
    s.headers.update({
        "Content-Type": "application/json",
        "Referer": BASE_URL,
        "x-csrftoken": csrf_token,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    })
    return s


def gql(session: requests.Session, query: str, variables: dict) -> dict:
    resp = session.post(GRAPHQL_URL, json={"query": query, "variables": variables})
    resp.raise_for_status()
    return resp.json()


# ── Fetch problem list ───────────────────────────────────────────────────────

PROBLEM_LIST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      frontendQuestionId: questionFrontendId
      title
      titleSlug
      difficulty
      status
    }
  }
}
"""

LIST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      frontendQuestionId: questionFrontendId
      title
      titleSlug
      difficulty
      status
    }
  }
}
"""


def get_problem_list(session: requests.Session, list_slug: str) -> list:
    """Fetch all problems from a custom LeetCode list using listId filter."""
    problems = []
    skip = 0
    limit = 50

    print(f"📋 Fetching problem list '{list_slug}'...")

    while True:
        data = gql(session, LIST_QUERY, {
            "categorySlug": "",
            "limit": limit,
            "skip": skip,
            "filters": {"listId": list_slug},
        })

        page = data.get("data", {}).get("problemsetQuestionList", {})
        questions = page.get("questions", [])
        total = page.get("total", 0)

        if not questions:
            break

        problems.extend(questions)
        skip += len(questions)

        print(f"  → fetched {skip}/{total} problems")

        if skip >= total:
            break
        time.sleep(0.5)

    # Filter to only solved problems
    solved = [p for p in problems if p.get("status") == "ac"]
    print(f"✅ Found {len(solved)} solved problems (out of {len(problems)} total)\n")
    return solved


# ── Fetch problem details ────────────────────────────────────────────────────

PROBLEM_DETAIL_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    topicTags {
      name
    }
    hints
    exampleTestcases
    sampleTestCase
    metaData
    codeSnippets {
      lang
      langSlug
      code
    }
    stats
    likes
    dislikes
    similarQuestions
  }
}
"""


def get_problem_detail(session: requests.Session, title_slug: str) -> dict:
    data = gql(session, PROBLEM_DETAIL_QUERY, {"titleSlug": title_slug})
    return data.get("data", {}).get("question", {})


# ── Fetch accepted solution ──────────────────────────────────────────────────

SUBMISSIONS_QUERY = """
query submissionList($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!, $lang: Int, $status: Int) {
  questionSubmissionList(
    offset: $offset
    limit: $limit
    lastKey: $lastKey
    questionSlug: $questionSlug
    lang: $lang
    status: $status
  ) {
    submissions {
      id
      statusDisplay
      lang
      runtime
      memory
      timestamp
      url
    }
  }
}
"""

SUBMISSION_DETAIL_QUERY = """
query submissionDetails($submissionId: Int!) {
  submissionDetails(submissionId: $submissionId) {
    code
    lang {
      name
      verboseName
    }
    runtimePercentile
    memoryPercentile
    runtime
    memory
  }
}
"""


def get_accepted_python_solution(session: requests.Session, title_slug: str) -> Optional[str]:
    """Return the code of the latest accepted Python3 (or Python) submission."""
    data = gql(session, SUBMISSIONS_QUERY, {
        "offset": 0,
        "limit": 20,
        "lastKey": None,
        "questionSlug": title_slug,
        "status": 10,  # Accepted
    })

    subs = (data.get("data", {})
               .get("questionSubmissionList", {})
               .get("submissions", []))

    # Prefer python3, fall back to python
    python_subs = [s for s in subs if s.get("lang") in ("python3", "python")]
    if not python_subs:
        return None

    sub_id = int(python_subs[0]["id"])
    detail = gql(session, SUBMISSION_DETAIL_QUERY, {"submissionId": sub_id})
    code = (detail.get("data", {})
                  .get("submissionDetails", {})
                  .get("code"))
    return code


# ── HTML → plain text ────────────────────────────────────────────────────────

def html_to_text(html: str) -> str:
    """Very lightweight HTML → readable text conversion."""
    if not html:
        return ""
    # replace common tags
    html = re.sub(r"<br\s*/?>", "\n", html)
    html = re.sub(r"<p>", "\n", html)
    html = re.sub(r"</p>", "\n", html)
    html = re.sub(r"<li>", "\n- ", html)
    html = re.sub(r"</li>", "", html)
    html = re.sub(r"<ul>|</ul>|<ol>|</ol>", "", html)
    html = re.sub(r"<strong>(.*?)</strong>", r"**\1**", html, flags=re.DOTALL)
    html = re.sub(r"<em>(.*?)</em>", r"*\1*", html, flags=re.DOTALL)
    html = re.sub(r"<code>(.*?)</code>", r"`\1`", html, flags=re.DOTALL)
    html = re.sub(r"<pre>(.*?)</pre>", r"\n```\n\1\n```\n", html, flags=re.DOTALL)
    html = re.sub(r"<[^>]+>", "", html)   # strip remaining tags
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"&#39;", "'", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


# ── Build README.md ──────────────────────────────────────────────────────────

def build_readme(detail: dict) -> str:
    num = detail.get("questionFrontendId", "?")
    title = detail.get("title", "Unknown")
    difficulty = detail.get("difficulty", "Unknown")
    tags = ", ".join(t["name"] for t in detail.get("topicTags", []))
    description = html_to_text(detail.get("content", ""))

    try:
        stats = json.loads(detail.get("stats", "{}"))
        accepted = stats.get("totalAccepted", "N/A")
        submissions = stats.get("totalSubmission", "N/A")
        rate = stats.get("acRate", "N/A")
    except Exception:
        accepted = submissions = rate = "N/A"

    hints = detail.get("hints", [])
    similar_raw = detail.get("similarQuestions", "[]")
    try:
        similar = json.loads(similar_raw)
    except Exception:
        similar = []

    difficulty_badge = {
        "Easy": "🟢 Easy",
        "Medium": "🟡 Medium",
        "Hard": "🔴 Hard",
    }.get(difficulty, difficulty)

    lines = [
        f"# {num}. {title}",
        "",
        f"**Difficulty:** {difficulty_badge}  ",
        f"**Tags:** {tags}  ",
        f"**Accepted:** {accepted} / {submissions} ({rate})",
        "",
        "---",
        "",
        "## Problem",
        "",
        description,
        "",
    ]

    if hints:
        lines += ["---", "", "## Hints", ""]
        for i, h in enumerate(hints, 1):
            lines.append(f"<details><summary>Hint {i}</summary>\n\n{html_to_text(h)}\n\n</details>")
            lines.append("")

    if similar:
        lines += ["---", "", "## Similar Problems", ""]
        for s in similar:
            lines.append(f"- [{s.get('title')}](https://leetcode.com/problems/{s.get('titleSlug')}/) — {s.get('difficulty')}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Solution",
        "",
        "See [solution.py](./solution.py)",
        "",
        f"*Problem link: https://leetcode.com/problems/{detail.get('titleSlug', '')}/*",
    ]

    return "\n".join(lines)


# ── Build solution.py ────────────────────────────────────────────────────────

def build_solution_py(detail: dict, code: str) -> str:
    num = detail.get("questionFrontendId", "?")
    title = detail.get("title", "Unknown")
    difficulty = detail.get("difficulty", "Unknown")
    slug = detail.get("titleSlug", "")

    header = f"""\
\"\"\"
LeetCode {num}. {title}
Difficulty: {difficulty}
URL: https://leetcode.com/problems/{slug}/
\"\"\"

"""
    return header + code


# ── Save to disk ─────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text


def save_problem(output_dir: str, detail: dict, code: str):
    num = detail.get("questionFrontendId", "0").zfill(4)
    title = detail.get("title", "Unknown")
    difficulty = detail.get("difficulty", "Unknown")

    folder_name = f"{num}-{slugify(title)}"
    folder_path = os.path.join(output_dir, difficulty, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    readme_path = os.path.join(folder_path, "README.md")
    solution_path = os.path.join(folder_path, "solution.py")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(build_readme(detail))

    with open(solution_path, "w", encoding="utf-8") as f:
        f.write(build_solution_py(detail, code))

    return folder_path


# ── Main scraper ─────────────────────────────────────────────────────────────

def scrape(
    leetcode_session: str,
    csrf_token: str,
    list_slug: str,
    output_dir: str,
):
    session = make_session(leetcode_session, csrf_token)
    problems = get_problem_list(session, list_slug)

    skipped = []
    saved = []

    new_problems = []
    existing_problems = []
    for p in problems:
        num = p.get("frontendQuestionId", "0").zfill(4)
        title = p["title"]
        difficulty = p.get("difficulty", "Unknown")
        folder_name = f"{num}-{slugify(title)}"
        folder_path = os.path.join(output_dir, difficulty, folder_name)
        solution_path = os.path.join(folder_path, "solution.py")
        if os.path.isfile(solution_path):
            p["_folder_path"] = folder_path
            p["_solution_path"] = solution_path
            existing_problems.append(p)
        else:
            new_problems.append(p)

    print(f"🆕 {len(new_problems)} new problems to fetch.")
    print(f"🔄 {len(existing_problems)} existing problems to check for updated solutions.\n")

    # ── Step 1: Scrape new problems ───────────────────────────────────────────
    for i, p in enumerate(new_problems, 1):
        slug = p["titleSlug"]
        title = p["title"]
        num = p.get("frontendQuestionId", "?")

        print(f"[new {i}/{len(new_problems)}] {num}. {title}")

        try:
            detail = get_problem_detail(session, slug)
            code = get_accepted_python_solution(session, slug)

            if not code:
                print(f"  ⚠️  No accepted Python solution found — skipping")
                skipped.append(f"{num}. {title}")
                continue

            path = save_problem(output_dir, detail, code)
            print(f"  ✅ Saved → {path}")
            saved.append(f"{num}. {title}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            skipped.append(f"{num}. {title} (error: {e})")

        time.sleep(0.8)

    # ── Step 2: Check existing problems for updated solutions ─────────────────
    updated = 0
    for i, p in enumerate(existing_problems, 1):
        slug = p["titleSlug"]
        title = p["title"]
        num = p.get("frontendQuestionId", "?")
        solution_path = p["_solution_path"]
        folder_path = p["_folder_path"]

        try:
            code = get_accepted_python_solution(session, slug)
            if not code:
                time.sleep(0.5)
                continue

            # Read existing solution, strip the header to compare just the code
            with open(solution_path, "r", encoding="utf-8") as f:
                existing = f.read()

            # Extract code portion (after the header block)
            header_end = existing.find('"""\n\n')
            existing_code = existing[header_end + 5:].strip() if header_end != -1 else existing.strip()

            if code.strip() != existing_code:
                detail = get_problem_detail(session, slug)
                save_problem(output_dir, detail, code)
                print(f"  🔄 Updated: {num}. {title}")
                saved.append(f"{num}. {title} (updated)")
                updated += 1
                time.sleep(0.8)
            else:
                time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Error checking {num}. {title}: {e}")

    if updated:
        print(f"\n🔄 {updated} solution(s) updated.")
    else:
        print(f"✅ All existing solutions are up to date.")

    print(f"\n{'='*60}")
    print(f"Done! Saved {len(saved)} problems, skipped {len(skipped)}.")
    if skipped:
        print("\nSkipped:")
        for s in skipped:
            print(f"  - {s}")

    return saved, skipped

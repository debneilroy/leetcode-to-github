"""
generate_site.py
-----------------
Generates a GitHub Pages site with full LeetCode-style UI from the
downloaded problem data in output/.

For each problem, creates an index.html with:
  - Left panel: problem description, examples, constraints, hints, similar problems
  - Right panel: full solution.py content (all variants) with syntax highlighting

Also generates a root index.html with the full problem list, difficulty filters,
and stats.

GitHub Pages setup (after uploading):
  Repo → Settings → Pages → Source: Deploy from branch → main → / (root)
"""

import os
import re
import html as html_lib
from datetime import datetime
from pathlib import Path


# ── Uncomment code variants ────────────────────────────────────────────────────

# Python keywords/builtins that signal a line is code, not prose
_CODE_STARTS = frozenset([
    'class', 'def', 'return', 'if', 'elif', 'else:', 'else', 'for', 'while',
    'import', 'from', 'with', 'try:', 'try', 'except', 'finally:', 'finally',
    'raise', 'yield', 'pass', 'break', 'continue', 'lambda', 'not', 'and',
    'or', 'True', 'False', 'None', 'self', 'super', 'print', 'len', 'range',
    'enumerate', 'zip', 'map', 'filter', 'sorted', 'list', 'dict', 'set',
    'tuple', 'int', 'str', 'float', 'bool', 'type', 'isinstance', 'assert',
    'del', 'global', 'nonlocal', 'async', 'await',
])


def _is_commented_code(line: str) -> bool:
    """Return True if this line is commented-out Python code (not a prose comment)."""
    if line == '#':
        return True                          # blank comment — part of a code block
    if not (line.startswith('# ') or line.startswith('#\t')):
        return False

    content = line[2:] if line.startswith('# ') else line[1:]

    if content.startswith((' ', '\t')):      # indented → inside a code block
        return True
    if content.startswith('#'):              # nested comment inside code
        return True
    if content.startswith(('"""', "'''")):   # docstring
        return True

    # Check first token against known Python keywords / builtins
    first = re.split(r'[\s\(:\[]', content)[0].rstrip(':')
    if first in _CODE_STARTS:
        return True

    # Assignment or function call:  result = 0  /  seen = {}  /  foo(
    if re.match(r'^[a-z_]\w*\s*[=\(\[]', content):
        return True

    return False


def uncomment_solution(code: str) -> str:
    """
    Strip the leading '# ' from commented-out code lines so all variants
    are fully visible. Leaves prose/explanatory comments untouched.
    """
    out = []
    for line in code.split('\n'):
        if _is_commented_code(line):
            # remove exactly the leading '# ' or '#\t' or lone '#'
            if line.startswith('# '):
                out.append(line[2:])
            elif line.startswith('#\t'):
                out.append(line[1:])
            else:                            # bare '#'
                out.append('')
        else:
            out.append(line)
    return '\n'.join(out)


# ── Difficulty styling ─────────────────────────────────────────────────────────

DIFF = {
    "Easy":    {"color": "#2cbb5d", "bg": "rgba(44,187,93,0.15)"},
    "Medium":  {"color": "#ffa116", "bg": "rgba(255,161,22,0.15)"},
    "Hard":    {"color": "#ef4743", "bg": "rgba(239,71,67,0.15)"},
    "Unknown": {"color": "#8b5cf6", "bg": "rgba(139,92,246,0.15)"},
}


# ── Markdown → HTML ────────────────────────────────────────────────────────────

def md_to_html(text: str) -> str:
    """Convert the subset of markdown used in our READMEs to HTML."""
    if not text:
        return ""

    # Markdown trigger characters (*, ^, [, ]) that survive inside already-
    # rendered code/link HTML get hidden behind these tokens so later regex
    # passes (bold/italic/superscript/bullets) can't reinterpret them.
    # Restored verbatim at the very end.
    _ESCAPES = {"*": "\x00AST\x00", "^": "\x00CAR\x00", "[": "\x00LBR\x00", "]": "\x00RBR\x00"}

    def _protect(s: str) -> str:
        for ch, token in _ESCAPES.items():
            s = s.replace(ch, token)
        return s

    def _restore(s: str) -> str:
        for ch, token in _ESCAPES.items():
            s = s.replace(token, ch)
        return s

    # fenced code blocks  ```\n...\n```
    text = re.sub(
        r"```\n?(.*?)\n?```",
        lambda m: f'<pre class="example-block"><code>{_protect(html_lib.escape(m.group(1)))}</code></pre>',
        text, flags=re.DOTALL
    )

    # inline code `...`
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_protect(html_lib.escape(m.group(1)))}</code>", text)

    # links  [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html_lib.escape(m.group(2))}" target="_blank">{html_lib.escape(m.group(1))}</a>',
        text
    )

    # bold ***...*** or **...**
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    text = re.sub(r"\*\*(.+?)\*\*",     r"<strong>\1</strong>", text)

    # italic *...*
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    # superscript  10^4, n^2  or  10<sup>4</sup>  (already html) — leave as is
    text = re.sub(r"(\w+)\^(\w+)", r"\1<sup>\2</sup>", text)

    # bullet lists
    lines = text.split("\n")
    output = []
    in_list = False
    for line in lines:
        if re.match(r"^\s*[-*]\s+(.+)", line):
            item = re.sub(r"^\s*[-*]\s+", "", line)
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{item}</li>")
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(line)
    if in_list:
        output.append("</ul>")
    text = "\n".join(output)

    # paragraphs: split on blank lines
    paras = re.split(r"\n{2,}", text.strip())
    result = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if p.startswith("<pre") or p.startswith("<ul") or p.startswith("<li"):
            result.append(p)
        else:
            # preserve single newlines as <br> inside paragraphs
            p = p.replace("\n", "<br>")
            result.append(f"<p>{p}</p>")
    return _restore("\n".join(result))


# ── Parse README.md ────────────────────────────────────────────────────────────

def parse_readme(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    data = {"number": "?", "title": "Unknown", "difficulty": "Medium",
            "tags": [], "stats": "", "description": "", "hints": [], "similar": []}

    m = re.search(r"^# (\d+)\. (.+)$", content, re.MULTILINE)
    if m:
        data["number"] = m.group(1)
        data["title"]  = m.group(2).strip()

    m = re.search(r"\*\*Difficulty:\*\* [🟢🟡🔴] (\w+)", content)
    if m:
        data["difficulty"] = m.group(1)

    m = re.search(r"\*\*Tags:\*\* (.+)", content)
    if m:
        data["tags"] = [t.strip() for t in m.group(1).split(",") if t.strip()]

    m = re.search(r"\*\*Accepted:\*\* (.+)", content)
    if m:
        data["stats"] = m.group(1).strip()

    m = re.search(r"## Problem\n\n(.*?)(?=\n---|\n## )", content, re.DOTALL)
    if m:
        data["description"] = m.group(1).strip()

    data["hints"] = re.findall(
        r"<details><summary>Hint \d+</summary>\n\n(.*?)\n\n</details>",
        content, re.DOTALL
    )

    sim_section = re.search(r"## Similar Problems\n\n(.*?)(?=\n---|\n## |$)", content, re.DOTALL)
    if sim_section:
        links = re.findall(r"- \[([^\]]+)\]\(([^\)]+)\) — (\w+)", sim_section.group(1))
        data["similar"] = [{"title": t, "url": u, "difficulty": d} for t, u, d in links]

    return data


# ── CSS shared across pages ────────────────────────────────────────────────────

SHARED_CSS = """
:root {
  --bg:        #ffffff;
  --surface:   #f7f8fa;
  --surface2:  #eff1f3;
  --border:    #e0e0e0;
  --text:      #1a1a1a;
  --muted:     #6b7280;
  --accent:    #ffa116;
  --easy:      #2cbb5d;
  --medium:    #ffa116;
  --hard:      #ef4743;
  --unknown:   #8b5cf6;
  --radius:    6px;
  --code-bg:   #f5f5f5;
  --code-panel:#f7f8fa;
  --code-border:#e0e0e0;
  --code-muted:#6b7280;
}
[data-theme="dark"] {
  --bg:        #1a1a1a;
  --surface:   #282828;
  --surface2:  #333;
  --border:    #3e3e3e;
  --text:      #eff2f6;
  --muted:     #8d99a6;
  --code-bg:   #1e1e1e;
  --code-panel:#2d2d2d;
  --code-border:#3e3e3e;
  --code-muted:#8d99a6;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.6; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code { font-family: 'Fira Code', 'Cascadia Code', Consolas, monospace;
       background: var(--surface2); color: #d63384; padding: 2px 5px;
       border-radius: 3px; font-size: 13px; }
pre.example-block { background: var(--surface2); border-radius: var(--radius);
  padding: 12px 16px; margin: 10px 0; overflow-x: auto; }
pre.example-block code { background: none; padding: 0; color: var(--text); font-size: 13px; }
p { margin-bottom: 10px; }
ul { padding-left: 20px; margin-bottom: 10px; }
li { margin-bottom: 4px; }
strong { font-weight: 600; }
h4 { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
sup { font-size: 10px; }

/* scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* header */
.header { display: flex; align-items: center; gap: 16px; padding: 0 16px;
  height: 44px; background: var(--surface); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 100; }
.logo { font-size: 15px; font-weight: 700; color: var(--accent); letter-spacing: -0.3px; }
.logo span { color: var(--text); font-weight: 400; }
.header-nav { display: flex; gap: 12px; font-size: 13px; color: var(--muted); }
.header-nav a { color: var(--muted); }
.header-nav a:hover { color: var(--text); text-decoration: none; }
.header-spacer { flex: 1; }
.theme-btn { background: none; border: 1px solid var(--border); color: var(--muted);
  padding: 4px 10px; border-radius: var(--radius); cursor: pointer; font-size: 13px;
  transition: color .15s, border-color .15s; }
.theme-btn:hover { color: var(--text); border-color: var(--muted); }

/* difficulty badge */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px;
  font-size: 12px; font-weight: 500; }
.badge-Easy    { color: var(--easy);    background: rgba(44,187,93,0.15); }
.badge-Medium  { color: var(--medium);  background: rgba(255,161,22,0.15); }
.badge-Hard    { color: var(--hard);    background: rgba(239,71,67,0.15); }
.badge-Unknown { color: var(--unknown); background: rgba(139,92,246,0.15); }

/* tag */
.tag { display: inline-block; padding: 3px 10px; border-radius: 20px;
  font-size: 12px; background: var(--surface2); color: var(--muted);
  margin: 2px; }
"""


# ── Problem page HTML ──────────────────────────────────────────────────────────

def build_problem_page(data: dict, code: str, prev_p, next_p, depth: int) -> str:
    root = "../" * depth
    num   = data["number"]
    title = data["title"]
    diff  = data["difficulty"]
    tags  = data["tags"]
    stats = data["stats"]
    desc  = md_to_html(data["description"])

    diff_color = DIFF.get(diff, DIFF["Medium"])["color"]

    # hints HTML
    hints_html = ""
    if data["hints"]:
        for i, h in enumerate(data["hints"], 1):
            hints_html += f"""
<details class="hint-block">
  <summary>Hint {i}</summary>
  <div class="hint-body">{md_to_html(h)}</div>
</details>"""
    else:
        hints_html = '<p class="empty-msg">No hints for this problem.</p>'

    # similar HTML
    similar_html = ""
    if data["similar"]:
        for s in data["similar"]:
            dc = DIFF.get(s["difficulty"], DIFF["Medium"])["color"]
            similar_html += f"""
<div class="similar-row">
  <a href="{html_lib.escape(s['url'])}" target="_blank">{html_lib.escape(s['title'])}</a>
  <span style="color:{dc}; font-size:12px;">{s['difficulty']}</span>
</div>"""
    else:
        similar_html = '<p class="empty-msg">No similar problems listed.</p>'

    # tags HTML
    tags_html = "".join(f'<span class="tag">{html_lib.escape(t)}</span>' for t in tags)

    # nav buttons
    prev_btn = ""
    next_btn = ""
    if prev_p:
        prev_slug = prev_p["slug"]
        prev_btn = f'<a class="nav-btn" href="{root}{prev_slug}/">&#8592; {prev_p["number"]}. {html_lib.escape(prev_p["title"])}</a>'
    if next_p:
        next_slug = next_p["slug"]
        next_btn = f'<a class="nav-btn" href="{root}{next_slug}/">{next_p["number"]}. {html_lib.escape(next_p["title"])} &#8594;</a>'

    # escape code for display in <pre> (Prism will highlight it)
    code_escaped = html_lib.escape(code)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{num}. {html_lib.escape(title)} - LeetCode Solutions</title>
<link rel="stylesheet" id="prism-theme" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css">
<style>
{SHARED_CSS}

/* layout */
.page {{ display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
.split {{ display: grid; grid-template-columns: 1fr 1fr; flex: 1; overflow: hidden; gap: 0; }}
.panel {{ display: flex; flex-direction: column; overflow: hidden; }}
.panel-left {{ border-right: 1px solid var(--border); }}

/* tabs */
.tabs {{ display: flex; border-bottom: 1px solid var(--code-border); background: var(--code-panel); flex-shrink: 0; }}
.tab {{ padding: 10px 16px; font-size: 13px; cursor: pointer; color: var(--muted);
  border-bottom: 2px solid transparent; transition: color .15s; user-select: none; }}
.tab:hover {{ color: var(--text); }}
.tab.active {{ color: var(--text); border-bottom-color: var(--accent); }}
.tab-content {{ display: none; padding: 20px; overflow-y: auto; flex: 1; }}
.tab-content.active {{ display: block; }}

/* problem header */
.prob-num-title {{ font-size: 17px; font-weight: 600; margin-bottom: 12px; }}
.prob-meta {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }}
.prob-stats {{ font-size: 12px; color: var(--muted); margin-bottom: 16px; }}
.prob-tags {{ margin-bottom: 20px; }}
.prob-desc {{ font-size: 14px; line-height: 1.7; }}

/* hint */
.hint-block {{ border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 10px; overflow: hidden; }}
.hint-block summary {{ padding: 10px 14px; cursor: pointer; font-size: 13px; color: var(--muted);
  background: var(--code-panel); user-select: none; }}
.hint-block summary:hover {{ color: var(--text); }}
.hint-body {{ padding: 12px 16px; font-size: 13px; border-top: 1px solid var(--border); }}

/* similar */
.similar-row {{ display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }}
.similar-row:last-child {{ border-bottom: none; }}
.empty-msg {{ color: var(--muted); font-size: 13px; }}

/* code panel */
.code-header {{ display: flex; align-items: center; justify-content: space-between;
  padding: 8px 14px; background: var(--code-panel); border-bottom: 1px solid var(--code-border); flex-shrink: 0; }}
.lang-pill {{ font-size: 12px; background: var(--surface2); color: var(--code-muted);
  padding: 3px 10px; border-radius: 20px; }}
.copy-btn {{ background: none; border: 1px solid var(--code-border); color: var(--code-muted);
  padding: 4px 10px; border-radius: var(--radius); cursor: pointer; font-size: 12px; }}
.copy-btn:hover {{ color: var(--text); border-color: var(--muted); }}
.code-scroll {{ flex: 1; overflow-y: auto; }}
.code-scroll pre[class*="language-"] {{ margin: 0 !important; border-radius: 0 !important;
  background: var(--code-bg) !important; min-height: 100%; font-size: 13px !important;
  padding: 20px !important; tab-size: 4; }}

/* bottom nav */
.bottom-nav {{ display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; background: var(--code-panel); border-top: 1px solid var(--code-border);
  flex-shrink: 0; font-size: 12px; }}
.nav-btn {{ color: var(--muted); padding: 5px 10px; border: 1px solid var(--border);
  border-radius: var(--radius); white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; max-width: 280px; }}
.nav-btn:hover {{ color: var(--text); border-color: var(--muted); text-decoration: none; }}
</style>
</head>
<body>
<div class="page">

  <header class="header">
    <a class="logo" href="{root}index.html">&#9889; <span>leetcode-solutions</span></a>
    <div class="header-nav">
      <a href="{root}index.html">All Problems</a>
    </div>
    <div class="header-spacer"></div>
    <span style="font-size:12px;color:var(--muted);">{num}. {html_lib.escape(title)}</span>
    <button class="theme-btn" id="theme-toggle" onclick="toggleTheme()">🌙</button>
  </header>

  <div class="split">

    <!-- LEFT PANEL -->
    <div class="panel panel-left">
      <div class="tabs">
        <div class="tab active" data-tab="desc">Description</div>
        <div class="tab" data-tab="hints">Hints ({len(data['hints'])})</div>
        <div class="tab" data-tab="similar">Similar ({len(data['similar'])})</div>
      </div>

      <div class="tab-content active" id="tab-desc">
        <div class="prob-num-title">{num}. {html_lib.escape(title)}</div>
        <div class="prob-meta">
          <span class="badge badge-{diff}">{diff}</span>
          {tags_html}
        </div>
        <div class="prob-stats">{html_lib.escape(stats)}</div>
        <div class="prob-desc">{desc}</div>
      </div>

      <div class="tab-content" id="tab-hints">
        {hints_html}
      </div>

      <div class="tab-content" id="tab-similar">
        {similar_html}
      </div>
    </div>

    <!-- RIGHT PANEL -->
    <div class="panel">
      <div class="code-header">
        <span class="lang-pill">Python3</span>
        <button class="copy-btn" id="copyBtn">Copy</button>
      </div>
      <div class="code-scroll">
        <pre class="language-python"><code class="language-python" id="solutionCode">{code_escaped}</code></pre>
      </div>
    </div>

  </div>

  <div class="bottom-nav">
    <div>{prev_btn}</div>
    <a href="{root}index.html" style="font-size:12px;color:var(--muted);">&#8801; All Problems</a>
    <div>{next_btn}</div>
  </div>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
<script>
// tabs
document.querySelectorAll('.tab').forEach(t => {{
  t.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('tab-' + t.dataset.tab).classList.add('active');
  }});
}});
// copy
document.getElementById('copyBtn').addEventListener('click', () => {{
  const code = document.getElementById('solutionCode').innerText;
  navigator.clipboard.writeText(code).then(() => {{
    const btn = document.getElementById('copyBtn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 1500);
  }});
}});
</script>
<script>
(function() {{
  var t = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', t);
  document.getElementById('theme-toggle').textContent = t === 'dark' ? '☀️' : '🌙';
  if (t === 'dark') document.getElementById('prism-theme').href = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css';
}})();
function toggleTheme() {{
  var t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('theme', t);
  document.getElementById('theme-toggle').textContent = t === 'dark' ? '☀️' : '🌙';
  document.getElementById('prism-theme').href = t === 'dark'
    ? 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css'
    : 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css';
}}
</script>
</body>
</html>"""


# ── Index page HTML ────────────────────────────────────────────────────────────

def build_index_page(problems: list) -> str:
    counts = {"Easy": 0, "Medium": 0, "Hard": 0, "Unknown": 0}
    for p in problems:
        counts[p.get("difficulty", "Medium")] = counts.get(p.get("difficulty", "Medium"), 0) + 1
    last_updated = datetime.now().strftime("%b %d, %Y at %I:%M %p")

    def _number_key(p):
        try:
            return int(p.get("number", 0))
        except (TypeError, ValueError):
            return float("inf")

    rows = ""
    for p in sorted(problems, key=_number_key):
        diff = p.get("difficulty", "Medium")
        tags_html = "".join(f'<span class="tag">{html_lib.escape(t)}</span>' for t in p.get("tags", [])[:4])
        rows += f"""
<tr class="prob-row" data-diff="{diff}">
  <td style="color:var(--muted);width:60px;">{p['number']}</td>
  <td><a href="{html_lib.escape(p['slug'])}/index.html">{html_lib.escape(p['title'])}</a></td>
  <td><span class="badge badge-{diff}">{diff}</span></td>
  <td class="hide-sm">{tags_html}</td>
  <td style="width:80px;text-align:center;">
    <a href="{html_lib.escape(p['slug'])}/index.html" class="sol-link">Python</a>
  </td>
</tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LeetCode Solutions</title>
<style>
{SHARED_CSS}

body {{ padding: 0; }}
.hero {{ padding: 32px 24px 20px; }}
.hero h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 6px; }}
.hero p {{ color: var(--muted); font-size: 14px; }}

.stats-bar {{ display: flex; gap: 16px; padding: 0 24px 24px; flex-wrap: wrap; }}
.stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
  padding: 14px 20px; min-width: 110px; }}
.stat-label {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; }}
.stat-val {{ font-size: 22px; font-weight: 700; }}

.filters {{ display: flex; gap: 8px; padding: 0 24px 16px; }}
.filter-btn {{ background: var(--surface); border: 1px solid var(--border); color: var(--muted);
  padding: 5px 14px; border-radius: 20px; cursor: pointer; font-size: 13px; }}
.filter-btn:hover, .filter-btn.active {{ color: var(--text); border-color: var(--muted); background: var(--surface2); }}
.filter-btn.all.active     {{ color: var(--accent);  border-color: var(--accent); }}
.filter-btn.easy.active    {{ color: var(--easy);    border-color: var(--easy); }}
.filter-btn.medium.active  {{ color: var(--medium);  border-color: var(--medium); }}
.filter-btn.hard.active    {{ color: var(--hard);    border-color: var(--hard); }}
.filter-btn.unknown.active {{ color: var(--unknown); border-color: var(--unknown); }}

.table-wrap {{ padding: 0 24px 40px; overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{ padding: 10px 12px; text-align: left; font-size: 12px; color: var(--muted);
  font-weight: 500; border-bottom: 1px solid var(--border); }}
tbody tr {{ border-bottom: 1px solid var(--border); transition: background .1s; }}
tbody tr:hover {{ background: var(--surface); }}
tbody td {{ padding: 12px 12px; font-size: 14px; vertical-align: middle; }}
.sol-link {{ font-size: 12px; background: rgba(255,161,22,0.15); color: var(--accent);
  padding: 3px 10px; border-radius: 20px; white-space: nowrap; }}
.sol-link:hover {{ background: rgba(255,161,22,0.25); text-decoration: none; }}
@media(max-width:600px) {{ .hide-sm {{ display: none; }} }}
</style>
</head>
<body>

<header class="header">
  <span class="logo">&#9889; <span>leetcode-solutions</span></span>
  <div class="header-spacer"></div>
  <button class="theme-btn" id="theme-toggle" onclick="toggleTheme()">🌙</button>
</header>

<div class="hero">
  <h1>My LeetCode Solutions</h1>
  <p>All problems solved in Python3, organized by difficulty.</p>
  <p style="color:var(--muted);font-size:12px;margin-top:6px;">Last updated: {last_updated}</p>
</div>

<div class="stats-bar">
  <div class="stat-card">
    <div class="stat-label">Total solved</div>
    <div class="stat-val">{len(problems)}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label" style="color:var(--easy);">Easy</div>
    <div class="stat-val" style="color:var(--easy);">{counts['Easy']}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label" style="color:var(--medium);">Medium</div>
    <div class="stat-val" style="color:var(--medium);">{counts['Medium']}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label" style="color:var(--hard);">Hard</div>
    <div class="stat-val" style="color:var(--hard);">{counts['Hard']}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label" style="color:var(--unknown);">Unknown</div>
    <div class="stat-val" style="color:var(--unknown);">{counts['Unknown']}</div>
  </div>
</div>

<div class="filters">
  <button class="filter-btn all active" onclick="filter('all', this)">All</button>
  <button class="filter-btn easy"   onclick="filter('Easy', this)">Easy</button>
  <button class="filter-btn medium" onclick="filter('Medium', this)">Medium</button>
  <button class="filter-btn hard"   onclick="filter('Hard', this)">Hard</button>
  <button class="filter-btn unknown" onclick="filter('Unknown', this)">Unknown</button>
</div>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>#</th><th>Title</th><th>Difficulty</th>
        <th class="hide-sm">Tags</th><th>Solution</th>
      </tr>
    </thead>
    <tbody id="probTable">
      {rows}
    </tbody>
  </table>
</div>

<script>
function filter(diff, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.prob-row').forEach(r => {{
    r.style.display = (diff === 'all' || r.dataset.diff === diff) ? '' : 'none';
  }});
}}
</script>
<script>
(function() {{
  var t = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', t);
  document.getElementById('theme-toggle').textContent = t === 'dark' ? '☀️' : '🌙';
}})();
function toggleTheme() {{
  var t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('theme', t);
  document.getElementById('theme-toggle').textContent = t === 'dark' ? '☀️' : '🌙';
}}
</script>
</body>
</html>"""


# ── Main site generator ────────────────────────────────────────────────────────

def generate_site(output_dir: str):
    output_dir = os.path.abspath(output_dir)

    # Collect all problems
    problems = []
    for diff in ["Easy", "Medium", "Hard", "Unknown"]:
        diff_dir = os.path.join(output_dir, diff)
        if not os.path.isdir(diff_dir):
            continue
        for folder in sorted(os.listdir(diff_dir)):
            folder_path = os.path.join(diff_dir, folder)
            readme = os.path.join(folder_path, "README.md")
            solution = os.path.join(folder_path, "solution.py")
            if not os.path.isfile(readme) or not os.path.isfile(solution):
                continue
            data = parse_readme(readme)
            # "Unknown" is a physical folder for problems not sourced from
            # LeetCode — it doesn't mean the difficulty is unknown. Trust the
            # README's own **Difficulty:** line when present; only fall back
            # to "Unknown" as a difficulty label if the README didn't specify.
            if diff == "Unknown":
                if data["difficulty"] not in ("Easy", "Medium", "Hard"):
                    data["difficulty"] = "Unknown"
            else:
                data["difficulty"] = diff
            data["slug"] = f"{diff}/{folder}"
            data["folder"] = folder_path
            problems.append(data)

    if not problems:
        print("⚠️  No problems found in output dir.")
        return

    print(f"\n🌐 Generating site for {len(problems)} problems...")

    # Sort by problem number for prev/next navigation. Unnumbered "Unknown"
    # problems (no "# N. Title" heading in their README) sort last.
    def _number_key(p):
        try:
            return int(p.get("number", 0))
        except (TypeError, ValueError):
            return float("inf")

    problems.sort(key=_number_key)

    # Generate per-problem pages
    for i, p in enumerate(problems):
        with open(os.path.join(p["folder"], "solution.py"), "r", encoding="utf-8") as f:
            code = uncomment_solution(f.read())

        prev_p = problems[i - 1] if i > 0 else None
        next_p = problems[i + 1] if i < len(problems) - 1 else None

        # depth = 2 (output/Difficulty/FolderName/)
        html = build_problem_page(p, code, prev_p, next_p, depth=2)
        out_path = os.path.join(p["folder"], "index.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✅ {p['number']:>4}. {p['title']}")

    # Generate index page
    index_html = build_index_page(problems)
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"\n  ✅ index.html → {index_path}")
    print(f"\n✅ Site generated — {len(problems) + 1} HTML files total.")
    print("\n📌 After uploading to GitHub:")
    print("   Repo → Settings → Pages → Source: Deploy from branch → main → / (root)")
    print(f"   Your site will be at: https://debneilroy.github.io/leetcode-solutions/\n")

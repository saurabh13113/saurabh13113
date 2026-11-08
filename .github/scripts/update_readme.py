#!/usr/bin/env python3
"""Refresh the auto-generated sections of README.md using the GitHub API.

Fills two marker blocks:
  RECENT_REPOS: the most recently pushed public, non-fork repos
  ACTIVITY:     the latest public events (pushes, PRs, new repos, stars)

Standard library only. Reads GITHUB_TOKEN and GITHUB_ACTOR / GH_USER from the env.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER") or os.environ.get("GITHUB_ACTOR") or "saurabh13113"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
MAX_REPOS = 5
MAX_EVENTS = 6
# Practice / coursework repos: real, but not "shipped" work.
HIDE = re.compile(r"neetcode|eco225|tut\d|tutorial|-testing$", re.I)


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-readme-updater",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def ago(iso):
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    secs = int((datetime.now(timezone.utc) - then).total_seconds())
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit} ago"
    return "just now"


def repo_link(name):
    return f"[{name.split('/')[-1]}](https://github.com/{name})"


def recent_repos():
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=30&type=owner")
    # Only repos with a description: an empty "What it is" column looks unfinished.
    repos = [
        r for r in repos
        if not r["fork"] and r["name"].lower() != USER.lower() and r["description"]
        and not HIDE.search(r["name"])
    ]
    lines = ["| Repo | What it is | Lang | Updated |", "|---|---|---|---|"]
    for r in repos[:MAX_REPOS]:
        desc = (r["description"] or "—").replace("|", "\\|")
        lines.append(
            f"| [{r['name']}]({r['html_url']}) | {desc} | {r['language'] or '—'} | {ago(r['pushed_at'])} |"
        )
    return "\n".join(lines)


def describe(ev):
    t, repo, p = ev["type"], ev["repo"]["name"], ev["payload"]
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits", [])) or 1
        return f"⬆️ Pushed {n} commit{'s' if n != 1 else ''} to {repo_link(repo)}"
    if t == "PullRequestEvent":
        pr = p["pull_request"]
        verb = "Merged" if pr.get("merged") else p["action"].capitalize()
        return f"🔀 {verb} PR [#{pr['number']}]({pr['html_url']}) in {repo_link(repo)}"
    if t == "CreateEvent" and p.get("ref_type") == "repository":
        return f"🆕 Created {repo_link(repo)}"
    if t == "WatchEvent":
        return f"⭐ Starred {repo_link(repo)}"
    if t == "IssuesEvent":
        i = p["issue"]
        return f"🐛 {p['action'].capitalize()} issue [#{i['number']}]({i['html_url']}) in {repo_link(repo)}"
    if t == "ReleaseEvent":
        return f"🚀 Released {p['release']['tag_name']} of {repo_link(repo)}"
    return None


def activity():
    events = api(f"/users/{USER}/events/public?per_page=100")
    items = {}  # insertion-ordered, newest first
    for ev in events:
        # skip noise from the profile repo itself (the bot's own README commits)
        if ev["repo"]["name"].lower() == f"{USER}/{USER}".lower() or HIDE.search(ev["repo"]["name"]):
            continue
        if ev["type"] == "PushEvent":
            # collapse many pushes to one repo into a single line with a total
            key = ("push", ev["repo"]["name"])
            n = ev["payload"].get("size") or len(ev["payload"].get("commits", [])) or 1
            if key in items:
                items[key]["n"] += n
            else:
                items[key] = {"repo": ev["repo"]["name"], "n": n, "time": ev["created_at"]}
            continue
        text = describe(ev)
        if text and ("other", text) not in items:
            items[("other", text)] = {"text": text, "time": ev["created_at"]}

    out = []
    for key, it in list(items.items())[:MAX_EVENTS]:
        if key[0] == "push":
            plural = "s" if it["n"] != 1 else ""
            text = f"⬆️ Pushed {it['n']} commit{plural} to {repo_link(it['repo'])}"
        else:
            text = it["text"]
        out.append(f"- {text} · <sub>{ago(it['time'])}</sub>")
    return "\n".join(out) or "_Nothing public lately, check back soon._"


def stats():
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner")
    repos = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in repos)

    totals = {}
    for r in repos[:40]:
        try:
            for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
                totals[lang] = totals.get(lang, 0) + n
        except Exception:
            continue  # one repo failing should not break the whole section

    since = user["created_at"][:4]
    lines = [
        "| 📦 Public repos | ⭐ Stars earned | 👥 Followers | 📅 On GitHub since |",
        "|:-:|:-:|:-:|:-:|",
        f"| {user['public_repos']} | {stars} | {user['followers']} | {since} |",
        "",
    ]
    total = sum(totals.values())
    if total:
        lines.append("```text")
        top = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
        width = max(len(lang) for lang, _ in top) + 2
        for lang, n in top:
            pct = 100 * n / total
            filled = round(pct / 5)
            lines.append(f"{lang:<{width}}{'█' * filled}{'░' * (20 - filled)}  {pct:5.1f}%")
        lines.append("```")
    return "\n".join(lines)


def replace_block(text, name, body):
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"Marker block {name} not found in {README}")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def main():
    with open(README, encoding="utf-8") as f:
        original = f.read()
    updated = replace_block(original, "STATS", stats())
    updated = replace_block(updated, "RECENT_REPOS", recent_repos())
    updated = replace_block(updated, "ACTIVITY", activity())
    if updated != original:
        with open(README, "w", encoding="utf-8") as f:
            f.write(updated)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()

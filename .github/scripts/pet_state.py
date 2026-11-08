#!/usr/bin/env python3
"""Click-to-pet logic for the profile README. Standard library only.

  python pet_state.py --pet USER   someone clicked the cat: count it, update README
  python pet_state.py --refresh    recompute the mood (happy / idle / sleepy) only

The README link opens a pre-filled "pet-me" issue; the workflow runs this script
with the issue author's login, commits the README, then replies and closes the
issue. The issue title and body are never read, only the author's login (which
is validated), so a hostile issue cannot inject anything.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

REPO = os.environ.get("GITHUB_REPOSITORY", "saurabh13113/saurabh13113")
README = os.environ.get("README_PATH", "README.md")
STATE_PATH = os.environ.get("PET_STATE_PATH", "pet/state.json")
MESSAGE_FILE = os.environ.get("PET_MESSAGE_FILE", "")

PET_NAME = "Pixel"
TZ = ZoneInfo("America/Toronto")      # decides when the cat is asleep
SLEEP_FROM, SLEEP_UNTIL = 23, 7       # local hours: asleep from 23:00 to 07:00
HAPPY_FOR = timedelta(hours=3)        # how long a pet keeps the cat happy
COOLDOWN = timedelta(hours=1)         # per-person limit, so one person cannot spam the count
MAX_RECENT = 5
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

PHRASES = {"happy": "purring 💙", "idle": "chilling", "sleepy": "asleep 💤"}


def now_utc():
    override = os.environ.get("PET_NOW")  # tests only
    if override:
        return datetime.fromisoformat(override.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def parse(ts):
    return datetime.fromisoformat(ts) if ts else None


def load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}
    state.setdefault("pets", 0)
    state.setdefault("last_pet", None)
    state.setdefault("recent", [])
    state.setdefault("last_by", {})
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def mood(state, now):
    last = parse(state["last_pet"])
    if last and now - last < HAPPY_FOR:
        return "happy"
    hour = now.astimezone(TZ).hour
    if hour >= SLEEP_FROM or hour < SLEEP_UNTIL:
        return "sleepy"
    return "idle"


def apply_pet(state, user, now):
    """Return the reply for the issue. Mutates state if the pet counts."""
    if not LOGIN_RE.match(user or ""):
        return "Pet not counted: that username looks invalid."
    last = parse(state["last_by"].get(user))
    if last and now - last < COOLDOWN:
        wait = int((COOLDOWN - (now - last)).total_seconds() // 60) + 1
        return (f"{PET_NAME} is already happy from your last pet, @{user}. "
                f"Give it about {wait} more minute{'s' if wait != 1 else ''}. 🐱")
    state["pets"] += 1
    state["last_pet"] = now.isoformat()
    state["last_by"][user] = now.isoformat()
    state["recent"] = [u for u in state["recent"] if u != user]
    state["recent"].insert(0, user)
    del state["recent"][MAX_RECENT:]
    return f"{PET_NAME} purrs. 💙 That's pet number {state['pets']}. Thanks, @{user}!"


def pet_url():
    body = ("Just petting the cat 🐱. There's nothing to write: "
            "click “Submit new issue” and the bot does the rest.")
    return f"https://github.com/{REPO}/issues/new?title=pet-me&body={quote(body)}"


def render(state, now):
    m = mood(state, now)
    n = state["pets"]
    times = "time" if n == 1 else "times"
    lines = [
        '<p align="center">',
        f'  <a href="{pet_url()}"><img src="pet/pixel-{m}.svg" width="320" '
        f'alt="{PET_NAME}, a pixel cat, is {m}. Click to pet." /></a><br>',
        f"  <b>{PET_NAME} is {PHRASES[m]}</b> · petted <b>{n}</b> {times}<br>",
        "  <sub>👆 Click the cat to pet it. It opens a pre-filled issue (you need to be "
        "signed in to GitHub) and a bot does the rest.</sub>",
        "</p>",
    ]
    if state["recent"]:
        people = ", ".join(f'<a href="https://github.com/{u}">@{u}</a>' for u in state["recent"])
        lines += ["", f'<p align="center"><sub>Recent petters: {people}</sub></p>']
    return "\n".join(lines)


def replace_block(text, name, body):
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    if not pattern.search(text):
        sys.exit(f"Marker block {name} not found in {README}")
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--pet", metavar="USER")
    group.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    now = now_utc()
    state = load_state()
    message = ""
    if args.pet is not None:
        message = apply_pet(state, args.pet, now)
        print(message)
    save_state(state)

    with open(README, encoding="utf-8") as f:
        original = f.read()
    updated = replace_block(original, "PET", render(state, now))
    if updated != original:
        with open(README, "w", encoding="utf-8") as f:
            f.write(updated)
        print("README updated")
    else:
        print("README unchanged")

    if MESSAGE_FILE and message:
        with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write(message + "\n")


if __name__ == "__main__":
    main()

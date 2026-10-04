#!/usr/bin/env python3
"""Convert legacy persona YAML definitions to JSON for the new app (BAS-04).

One-off converter, kept for traceability. After conversion the JSON files in
app/js/review/personas/ are the hand-maintained source of truth; this script is
NOT re-run after CLN-02 removes the legacy personas/ folder.

    python3 tools/personas-to-json.py           # write <id>.json + index.json
    python3 tools/personas-to-json.py --verify  # re-read YAML and JSON, assert deep equality

Each personas/definitions/<id>.yaml becomes app/js/review/personas/<id>.json with
identical fields (key order kept, UTF-8, indent 2). index.json lists the ids in
sorted order. Needs PyYAML (pip install pyyaml); writes nothing outside the
output folder.
"""

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "personas" / "definitions"
OUT_DIR = REPO_ROOT / "app" / "js" / "review" / "personas"


def load_sources():
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(SRC_DIR.glob("*.yaml"))}


def convert():
    sources = load_sources()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for pid, data in sources.items():
        (OUT_DIR / f"{pid}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "index.json").write_text(json.dumps(sorted(sources), indent=2) + "\n", encoding="utf-8")
    print(f"personas-to-json: wrote {len(sources)} persona file(s) + index.json")


def verify():
    sources = load_sources()
    problems = []
    index = json.loads((OUT_DIR / "index.json").read_text(encoding="utf-8"))
    if index != sorted(sources):
        problems.append(f"index.json {index} != {sorted(sources)}")
    json_ids = sorted(p.stem for p in OUT_DIR.glob("*.json") if p.name != "index.json")
    if json_ids != sorted(sources):
        problems.append(f"JSON files {json_ids} != YAML files {sorted(sources)}")
    for pid, data in sources.items():
        path = OUT_DIR / f"{pid}.json"
        if not path.exists():
            continue
        if json.loads(path.read_text(encoding="utf-8")) != data:
            problems.append(f"{pid}.json differs from {pid}.yaml")
    for p in problems:
        print(f"personas-to-json --verify: {p}", file=sys.stderr)
    print(f"personas-to-json --verify: {len(sources)} persona(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(verify() if "--verify" in sys.argv[1:] else convert())

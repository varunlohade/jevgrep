#!/usr/bin/env python3
"""Score jevgrep on an answer key. Hit = the needle's line falls inside a returned range.
usage: score.py <repo> <questions.json>
questions.json: [{"id", "kind": "keyword"|"behaviour", "question", "file", "start", "end", "needle"}]"""
import json, os, subprocess, sys, time
root, qfile = os.path.abspath(sys.argv[1]), sys.argv[2]
JEVGREP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "jevgrep")
rows = []
for q in json.load(open(qfile)):
    t = time.time()
    res = json.loads(subprocess.run([JEVGREP, q["question"], root, "--json"], capture_output=True, text=True, check=True).stdout)
    secs = time.time() - t
    lines = open(os.path.join(root, q["file"]), errors="replace").read().splitlines()
    needle = [i + 1 for i, l in enumerate(lines) if q["needle"] in l and q["start"] <= i + 1 <= q["end"]]
    rank, read = None, 0
    for i, h in enumerate(res["hits"]):
        read += h["end"] - h["start"] + 1
        if h["file"] == q["file"] and any(h["start"] <= n <= h["end"] for n in needle):
            rank = i + 1; break
    rows.append({"id": q["id"], "kind": q["kind"], "rank": rank, "read_lines": read if rank else None, "seconds": round(secs, 2)})
    print(f"#{q['id']} {q['kind']:9} rank={rank} {secs:.2f}s")
for kind in sorted({x["kind"] for x in rows}) + [None]:
    r = [x for x in rows if kind is None or x["kind"] == kind]
    found = sorted(x["read_lines"] for x in r if x["rank"])
    print(f"{kind or 'all':9}: first {sum(x['rank'] == 1 for x in r)}/{len(r)} · top3 {sum(bool(x['rank']) and x['rank'] <= 3 for x in r)}/{len(r)} "
          f"· found {len(found)}/{len(r)} · median read {found[len(found)//2] if found else '-'} lines · avg {sum(x['seconds'] for x in r)/len(r):.2f}s")

from pathlib import Path
reps = {"\u2014":"--", "\u2013":"-", "\u2018":"'", "\u2019":"'", "\u201c":'"', "\u201d":'"', "\u00a0":" "}
root = Path("tasks/cross-shard-journal-reconcile")
for f in root.rglob("*"):
    if not f.is_file():
        continue
    if f.suffix.lower() in {".jnl", ".sqlite", ".pyc"}:
        continue
    try:
        text = f.read_text(encoding="utf-8")
    except Exception:
        continue
    orig = text
    for a,b in reps.items():
        text = text.replace(a,b)
    if text != orig:
        f.write_text(text, encoding="utf-8", newline="\n")
        print("fixed", f)
for f in root.rglob("*"):
    if f.suffix in {".md",".toml",".py",".sh",".txt"} and f.is_file():
        bad = [i for i,x in enumerate(f.read_bytes()) if x >= 128]
        print(("STILL" if bad else "ok"), f, len(bad) if bad else 0)

import csv, re, os
from pathlib import Path

STRAIN_IMG_DIR = "assets/img/strain"
SEEDS_CSV      = "assets/data/seeds.csv"

# Words to strip when normalizing for matching
STRIP_WORDS = {
    "auto","automatic","autoflowering","feminized","feminised","fem","regular","reg",
    "cbd","cbg","fast","fast version","xxl","xl","plus","seeds","seed","x","f1","f2",
    "1pk","2pk","3pk","4pk","5pk","6pk","7pk","8pk","9pk","10pk","12pk","25pk",
    "1 pack","2 pack","3 pack","4 pack","5 pack","6 pack","10 pack","12 pack","25 pack",
    "pack","single","photo","photoperiod","high","strain","version","v2","v3",
}

def normalize(s):
    s = s.lower().strip()
    s = re.sub(r"[_\-]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # strip trailing noise words repeatedly
    changed = True
    while changed:
        changed = False
        parts = s.split()
        while parts and parts[-1] in STRIP_WORDS:
            parts.pop()
            changed = True
        # also strip leading noise
        while parts and parts[0] in STRIP_WORDS:
            parts.pop(0)
            changed = True
        s = " ".join(parts)
    return s

# Build lookup: normalized_name -> original_basename
img_lookup = {}
for f in Path(STRAIN_IMG_DIR).iterdir():
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        base = f.stem  # e.g. "Blue_Dream"
        key  = normalize(base)
        img_lookup[key] = base

def find_group(strain_name):
    norm = normalize(strain_name)
    if not norm:
        return ""
    # 1. exact match
    if norm in img_lookup:
        return img_lookup[norm]
    # 2. progressively drop last word
    parts = norm.split()
    for i in range(len(parts) - 1, 0, -1):
        candidate = " ".join(parts[:i])
        if candidate in img_lookup:
            return img_lookup[candidate]
    return ""

# Read seeds.csv
with open(SEEDS_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows   = list(reader)

# Add strain_group column if not present
if "strain_group" not in fields:
    fields = list(fields) + ["strain_group"]

matched = 0
for row in rows:
    group = find_group(row.get("strain_name", ""))
    row["strain_group"] = group
    if group:
        matched += 1

# Count groups with more than one row
from collections import Counter
group_counts = Counter(r["strain_group"] for r in rows if r["strain_group"])
multi = sum(1 for v in group_counts.values() if v > 1)
single = sum(1 for v in group_counts.values() if v == 1)

# Leave all matched groups intact — singles with a real image are fine

with open(SEEDS_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

print(f"Total rows:          {len(rows)}")
print(f"Matched to image:    {matched}")
print(f"Unique groups:       {len(group_counts)}")
print(f"Rows with group:     {sum(1 for r in rows if r['strain_group'])}")
print(f"Rows without group:  {sum(1 for r in rows if not r['strain_group'])}")

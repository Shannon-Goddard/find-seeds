import csv
from pathlib import Path

SEEDS_CSV     = "assets/data/seeds.csv"
STRAIN_IMG_DIR = Path("assets/img/strain")

# Build lookup: basename -> relative path with correct extension
img_lookup = {}
for f in STRAIN_IMG_DIR.iterdir():
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        img_lookup[f.stem] = f"assets/img/strain/{f.name}"

with open(SEEDS_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = list(reader.fieldnames)
    rows   = list(reader)

if "img_path" not in fields:
    fields.append("img_path")

matched = 0
for row in rows:
    group = row.get("strain_group", "")
    path  = img_lookup.get(group, "")
    row["img_path"] = path
    if path:
        matched += 1

with open(SEEDS_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

print(f"Total rows:      {len(rows)}")
print(f"Paths resolved:  {matched}")
print(f"Missing:         {len(rows) - matched}")

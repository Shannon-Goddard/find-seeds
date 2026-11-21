import csv, hashlib

SEEDS_CSV = "assets/data/seeds.csv"
NUM_DEFAULTS = 15

def default_img(strain_name):
    h = int(hashlib.md5(strain_name.lower().strip().encode()).hexdigest(), 16)
    return f"default-{(h % NUM_DEFAULTS) + 1}"

with open(SEEDS_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = list(reader.fieldnames)
    rows   = list(reader)

assigned = 0
for row in rows:
    if not row.get("strain_group"):
        row["strain_group"] = default_img(row.get("strain_name", ""))
        assigned += 1

with open(SEEDS_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

from collections import Counter
dist = Counter(r["strain_group"] for r in rows if r["strain_group"].startswith("default"))
print(f"Assigned defaults: {assigned}")
for k in sorted(dist, key=lambda x: int(x.split('-')[1])):
    print(f"  {k}: {dist[k]}")

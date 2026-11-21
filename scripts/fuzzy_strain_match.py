import csv, re
from pathlib import Path
from rapidfuzz import fuzz

STRAIN_IMG_DIR = "assets/img/strain"
SEEDS_CSV      = "assets/data/seeds.csv"
THRESHOLD      = 90
MAX_LEN_DIFF   = 3

STRIP_WORDS = {
    "auto","automatic","autoflowering","feminized","feminised","fem","regular","reg",
    "cbd","cbg","fast","xxl","xl","plus","seeds","seed","f1","f2",
    "pack","single","photo","photoperiod","strain","version","v2","v3",
}

def normalize(s):
    s = s.lower().strip()
    s = re.sub(r"[_\-]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    changed = True
    while changed:
        changed = False
        parts = s.split()
        while parts and parts[-1] in STRIP_WORDS:
            parts.pop(); changed = True
        while parts and parts[0] in STRIP_WORDS:
            parts.pop(0); changed = True
        s = " ".join(parts)
    return s

# Load seeds
with open(SEEDS_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = list(reader.fieldnames)
    rows   = list(reader)

# All images
all_images = {
    f.stem: normalize(f.stem)
    for f in Path(STRAIN_IMG_DIR).iterdir()
    if f.suffix.lower() in (".jpg",".jpeg",".png",".webp")
    and "default" not in f.name
}

# Already used groups
used = {r["strain_group"] for r in rows if r.get("strain_group")}

# Unused images only
unused_images = {base: norm for base, norm in all_images.items() if base not in used}
print(f"Unused images to match against: {len(unused_images)}")

# Unique unmatched strain names
unmatched_strains = {
    r["strain_name"]: normalize(r["strain_name"])
    for r in rows
    if not r.get("strain_group") and r.get("strain_name")
}
print(f"Unique unmatched strain names:  {len(unmatched_strains)}")

# Fuzzy match
strain_to_group = {}
unused_norms = list(unused_images.items())  # (base, norm)

for strain_name, strain_norm in unmatched_strains.items():
    if not strain_norm:
        continue
    best_score = 0
    best_base  = None
    for img_base, img_norm in unused_norms:
        # Length guard
        if abs(len(strain_norm) - len(img_norm)) > MAX_LEN_DIFF:
            continue
        score = fuzz.token_sort_ratio(strain_norm, img_norm)
        if score > best_score:
            best_score = score
            best_base  = img_base
    if best_score >= THRESHOLD:
        strain_to_group[strain_name] = (best_base, best_score)

REJECT = {
    "Cherry Slimeade", "Cackleberry", "Rankenstein", "SFV OG", "sfv og",
    "Sherbert Glue", "Glue Sherbert", "Maple Sherbet", "Alien Glue",
    "Pure Jack", "the Purps", "Nevils Haze", "Diesel OG", "Citrus Rush",
    "White Candy", "Purple Juice", "Sugar Stack", "Boss HOG",
    "Bogo Purple Alien", "Hammer Head CBG",
}
strain_to_group = {k: v for k, v in strain_to_group.items() if k not in REJECT}

print(f"\nFuzzy matches after rejects: {len(strain_to_group)}")

# Apply to seeds.csv
with open(SEEDS_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fields = list(reader.fieldnames)
    rows   = list(reader)

new_assignments = 0
for row in rows:
    if not row.get("strain_group") and row.get("strain_name") in strain_to_group:
        row["strain_group"] = strain_to_group[row["strain_name"]][0]
        new_assignments += 1

with open(SEEDS_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

print(f"New rows assigned:   {new_assignments}")
print(f"Total with group:    {sum(1 for r in rows if r.get('strain_group'))}")
print(f"Unique groups:       {len(set(r['strain_group'] for r in rows if r.get('strain_group')))}")
print(f"Rows without group:  {sum(1 for r in rows if not r.get('strain_group'))}")

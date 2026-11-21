import csv
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

# affiliate_code from affiliate-programs.csv
# Format: (vendor_domain, affiliate_param, affiliate_url)
# affiliate_param = query string to append to product_url (e.g. ?af=329747)
# affiliate_url   = full redirect URL for vendors that don't use simple param appending
AFFILIATES = {
    "2fast4buds.com":              ("?af=329747",                                                                    ""),
    "alchimiaweb.com":             ("",                                                                              "https://www.alchimiaweb.com/en/seeds_selector.php?aff=B629EF277A86A59A24269BC9AA256704FC7481CE"),
    "amsterdamseedcenter.com":     ("?affiliate_code=F8ezyFcOGg&referring_service=link",                            ""),
    "canukseeds.com":              ("?a_id=bi0c19wc2xc8u",                                                          ""),
    "freeworldseedvault.com":      ("?coupon=Loyal9",                                                               ""),
    "herbiesheadshop.com":         ("?utm_source=loyal9&utm_medium=people&utm_campaign=loyal9_partner&a_aid=loyal9&a_bid=83818890", ""),
    "homegrowncannabis.com":       ("?a_aid=loyal9",                                                                ""),
    "ilgm.com":                    ("?aff=8128",                                                                    ""),
    "mass-hydro.com":              ("?sca_ref=11547740.l5DDc4X4smj",                                                ""),
    "nirvanashop.com":             ("?ref=LOYAL9",                                                                  ""),
    "originalsensible.com":        ("?acc=XEZBsayl4vfGi~tHw4H4",                                                   ""),
    "paradise-seeds.com":          ("?ref=loyal9",                                                                  ""),
    "royalqueenseeds.com":         ("?utm_source=postaffiliatepro&utm_medium=affiliate&utm_campaign=test&a_aid=36694750", ""),
    "seedsman.com":                ("?a_aid=6675f1c3ce128",                                                         ""),
    "truenorthseedbank.com":       ("?a_id=bi0c19wc2xc8u",                                                         ""),
    "growerschoiceseeds.us":       ("",                                                                             "https://www.growerschoiceseeds.us/ref/697/"),
    "bcbuddepot.com":              ("?a_aid=loyal9llc",                                                             ""),
    "seedsupreme.com":             ("?a_aid=loyal9",                                                                ""),
    "420-seeds.com":               ("?LOYAL9",                                                                      ""),
    "msnlseeds.com":               ("?aw_affiliate=eyJjYW1wYWlnbl9pZCI6IjYiLCJ0cmFmZmljX3NvdXJjZSI6IndlYnNpdGUiLCJhY2NvdW50X2lkIjozNTB9", ""),
}

VENDOR_INFO = "assets/data/vendor_info.csv"
NEW1        = "assets/data/new_vendors.csv"
NEW2        = "assets/data/new_vendors2.csv"
SEEDS       = "assets/data/seeds.csv"

# ── 1. Update vendor_info.csv with affiliate columns ─────────────────────────
with open(VENDOR_INFO, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for row in rows:
    domain = row["vendor_domain"]
    # match on domain suffix (vendor_domain may be bare domain)
    match = next((v for k, v in AFFILIATES.items() if domain.endswith(k) or k.endswith(domain)), ("", ""))
    row["affiliate_param"] = match[0]
    row["affiliate_url"]   = match[1]

fieldnames = list(rows[0].keys())
with open(VENDOR_INFO, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)

print(f"vendor_info.csv updated — {len(rows)} vendors")

# ── 2. Build vendor_info lookup ───────────────────────────────────────────────
with open(VENDOR_INFO, newline="", encoding="utf-8") as f:
    vi_rows = list(csv.DictReader(f))

vi_lookup = {}
for row in vi_rows:
    vi_lookup[row["vendor_domain"]] = row

def domain_of(url):
    h = urlparse(url).netloc or url
    return h.replace("www.", "")

# ── 3. Read seeds.csv headers ─────────────────────────────────────────────────
with open(SEEDS, newline="", encoding="utf-8") as f:
    seeds_reader = csv.DictReader(f)
    seeds_fields = seeds_reader.fieldnames
    seeds_rows   = list(seeds_reader)

print(f"seeds.csv loaded — {len(seeds_rows)} rows")

# ── 4. Merge new_vendors.csv + new_vendors2.csv ───────────────────────────────
VI_COLS = ["payment_methods","germ_guarantee","shipping_regions",
           "stealth_shipping","loyalty_program","breeder_type","vendor_status",
           "affiliate_param","affiliate_url"]

new_rows = []
for path in [NEW1, NEW2]:
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = domain_of(row.get("vendor_url",""))
            vi = vi_lookup.get(d, {})
            merged = {col: row.get(col, "") for col in seeds_fields}
            for col in VI_COLS:
                merged[col] = vi.get(col, "")
            new_rows.append(merged)

print(f"New rows to append: {len(new_rows)}")

# ── 5. Write updated seeds.csv ────────────────────────────────────────────────
# Ensure affiliate columns exist in seeds_fields
out_fields = list(seeds_fields)
for col in ["affiliate_param", "affiliate_url"]:
    if col not in out_fields:
        out_fields.append(col)

# Backfill affiliate columns on existing seeds rows
for row in seeds_rows:
    d = domain_of(row.get("vendor_url",""))
    vi = vi_lookup.get(d, {})
    row.setdefault("affiliate_param", vi.get("affiliate_param",""))
    row.setdefault("affiliate_url",   vi.get("affiliate_url",""))

all_rows = seeds_rows + new_rows
with open(SEEDS, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=out_fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(all_rows)

print(f"seeds.csv written — {len(all_rows)} total rows")

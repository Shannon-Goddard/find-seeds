# Find Seeds

**Live site:** [find-seeds.poweredbyci.live](https://find-seeds.poweredbyci.live)

A cannabis strain and seed bank search tool. Search 42,000+ strain listings across 137+ seed banks. Filter by type, shipping region, payment method, germination guarantee, and more.

Built by [Shannon Goddard](https://github.com/Shannon-Goddard) / [Loyal9 LLC](https://loyal9.com).

---

## The Real Story Behind This Project

This project has an honest origin story worth telling.

Shannon spent **over a month** manually cleaning a cannabis seed bank dataset — cross-referencing vendor URLs, normalizing strain names, standardizing columns, resolving duplicates. It was painstaking work. When the dataset was finally "done," it turned out the source data was **fundamentally corrupted** — structural issues that made the entire cleaned file unreliable as a foundation.

A month of work, gone.

At that point, [Amazon Q Developer](https://aws.amazon.com/q/developer/) (AWS's AI coding assistant, built on Claude) was brought in. Within a **couple of hours**, Q had:

- Diagnosed exactly why the original dataset was unrecoverable
- Rebuilt the entire data pipeline from scratch using Python scripts
- Scraped, parsed, and merged data from **137+ seed banks**
- Produced a clean `seeds.csv` with **42,372 rows and 21 columns**
- More than **doubled** the original dataset size in the process

That's not a flex on the human — Shannon did the hard work of sourcing vendors, understanding the domain, and making every product decision. But it is an honest acknowledgment that AI did the heavy lifting on the data engineering side, and it would be dishonest to pretend otherwise.

Shannon is transparent about AI use. This README reflects that.

---

## What It Does

- **Strain search** — fuzzy-friendly autocomplete across 42,372 listings
- **Vendor accordion** — click a strain, see every seed bank that carries it
- **SKU detail modal** — pack size, price range, shipping regions, payment methods, germination guarantee, stealth shipping, loyalty program
- **Affiliate links** — where applicable, links include affiliate parameters. Disclosed on every page.
- **Quick filters** — Ships USA, Crypto, Germ Guarantee, Stealth
- **Type filters** — Feminized, Auto, Regular, CBD
- **Shipping filters** — USA, International, EU, UK
- **Deep links** — shareable URLs with `?strain=` parameter
- **PWA-ready** — web manifest, full favicon set, OG image

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Vanilla HTML / CSS / JS — no framework |
| Data parsing | [PapaParse](https://www.papaparse.com/) 5.4.1 |
| Icons | [Font Awesome](https://fontawesome.com/) 6.5.0 |
| Analytics | Google Tag Manager (`GTM-NX38C59R`) |
| Hosting | GitHub Pages + custom domain |
| Data pipeline | Python 3 (scripts in `/scripts`) |

No build step. No bundler. No dependencies to install. Open `index.html` and it works.

---

## Data Pipeline

The pipeline runs in order. Each script is independent and idempotent.

```
scrape_new_vendors.py        # Scrape vendor product pages → raw CSVs
scrape_blocked_vendors.py    # Handle vendors that block standard scrapers
parse_partners_html.py       # Parse saved HTML from partner pages
merge_and_affiliate.py       # Merge all sources → seeds.csv, add affiliate params
build_strain_groups.py       # Group strains by name → strain_group column
fuzzy_strain_match.py        # Fuzzy match strain names → consolidate near-duplicates
assign_defaults.py           # Assign default-1 through default-15 to unmatched strains
build_img_paths.py           # Build img_path column with correct extensions
update_pages_head.py         # Keep <head> consistent across all 9 pages
```

### `seeds.csv` schema

| Column | Description |
|---|---|
| `vendor_name` | Seed bank name |
| `vendor_url` | Seed bank homepage |
| `platform` | e.g. Shopify, WooCommerce |
| `strain_name` | Product listing name |
| `breeder` | Breeder name if known |
| `product_type` | feminized / auto / regular / cbd |
| `pack_size` | e.g. "5 seeds", "10 seeds" |
| `product_url` | Direct product page URL |
| `strain_slug` | URL-safe strain identifier |
| `price_min` | Lowest price found |
| `price_max` | Highest price found |
| `currency_type` | USD, EUR, GBP, etc. |
| `in_stock` | yes / no |
| `payment_methods` | Pipe-delimited: `credit card\|crypto\|cash` |
| `germ_guarantee` | yes / no |
| `shipping_regions` | Pipe-delimited: `usa\|intl\|eu\|uk` |
| `stealth_shipping` | yes / no |
| `loyalty_program` | Program name or "no" |
| `breeder_type` | indie / commercial / etc. |
| `vendor_status` | active / inactive |
| `affiliate_param` | Query string to append to product_url |
| `affiliate_url` | Full redirect URL (used instead of affiliate_param when set) |
| `strain_group` | Named group key or `default-N` |
| `img_path` | Relative path to strain image |

---

## Images

- **Strain images:** 2,895 total (2,803 `.jpg`, 92 `.png`) in `assets/img/strain/`
- **Company logos:** 989 files in `assets/img/company/`
- **Named strain groups:** 1,490 matched to real strain photos
- **Default images:** 15 rotating defaults (`default-1.png` through `default-15.png`) assigned via MD5 hash for consistent per-strain fallback
- Strain images sourced from [WikiLeaf](https://www.wikileaf.com) — attribution on [Attributions page](https://find-seeds.poweredbyci.live/pages/attributions.html)

---

## Pages

| Page | Path |
|---|---|
| Strain Search | `/index.html` |
| About | `/pages/about.html` |
| Get Listed | `/pages/get-listed.html` |
| Submit a Bank | `/pages/submit-bank.html` |
| Contact | `/pages/contact.html` |
| Privacy Policy | `/pages/privacy.html` |
| Terms of Service | `/pages/terms.html` |
| Affiliate Disclosure | `/pages/disclosure.html` |
| Attributions | `/pages/attributions.html` |

---

## Affiliate Disclosure

Some vendor links are affiliate links. Commissions are earned at no cost to the user. Full disclosure at [/pages/disclosure.html](https://find-seeds.poweredbyci.live/pages/disclosure.html).

Affiliate logic in `app.js`:
- If `affiliate_url` is set → use it directly (full redirect URL)
- Else if `affiliate_param` is set → append to `product_url`
- Else → use `product_url` as-is

---

## Running Locally

No server required for the frontend. Just open `index.html` in a browser.

PapaParse fetches `assets/data/seeds.csv` via XHR — if your browser blocks local file XHR, serve it with any static server:

```bash
npx serve .
# or
python -m http.server 8000
```

For the data pipeline scripts:

```bash
cd scripts
pip install requests beautifulsoup4 pandas fuzzywuzzy python-levenshtein
python merge_and_affiliate.py
# etc.
```

---

## AI Credit

This project used **Amazon Q Developer** extensively and transparently.

Q wrote or co-wrote:
- The entire data pipeline (10 Python scripts)
- The complete frontend rewrite (`app.js`, `style.css`, `index.html`)
- All 9 pages including nav, footer, and head consistency
- `sitemap.xml`, `robots.txt`, `site.webmanifest`
- This README

The human (Shannon) provided:
- Domain expertise — knowing what seed bank customers actually need
- Vendor sourcing — finding and vetting 137+ seed banks
- Product decisions — every UX and feature call
- Data review — ongoing manual QA of 42,372 rows
- The original vision

The honest summary: Shannon had the idea, the domain knowledge, and the taste. Q had the engineering horsepower. Neither would have shipped this alone in any reasonable timeframe.

---

## License

© 2026 [Loyal9 LLC](https://loyal9.com). All rights reserved.

Data is provided for informational purposes. Prices are approximate and may be stale. Always verify on the vendor's site before purchasing.

import sys, csv, re, requests, time
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; find-seeds-bot/1.0)'}
TIMEOUT = 10

# ── Sitemap fetchers ──────────────────────────────────────────────────────────

def fetch_urls(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200: return []
        root = ET.fromstring(r.content)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [u.text for u in root.findall('sm:url/sm:loc', ns)]
    except: return []

# ── URL slug parser (same logic as build_clean_catalog.py) ───────────────────

AUTO_WORDS = {'auto', 'autoflower', 'autoflowering', 'automatic', 'automatica'}
FEM_WORDS  = {'fem', 'feminized', 'feminised', 'feminisiert'}
REG_WORDS  = {'reg', 'regular'}
CBD_WORDS  = {'cbd'}
TYPE_WORDS = AUTO_WORDS | FEM_WORDS | REG_WORDS | CBD_WORDS

NOISE = {'seeds', 'seed', 'strain', 'pack', 'pk', 'cannabis', 'marijuana',
         'weed', 'strains', 'shop', 'online', 'buy', 'order', 'fast', 'version',
         'flowering', 'flower', 'herbies', 'pre', 'roll', 'thca'}

_NO_UPPER = {'the', 'to', 'of', 'in', 'at', 'by', 'for', 'and', 'or', 'a', 'an', 'x'}

def last_slug(url):
    parts = [p for p in urlparse(url).path.rstrip('/').split('/') if p]
    return parts[-1] if parts else ''

def path_parts(url):
    return [p for p in urlparse(url).path.rstrip('/').split('/') if p]

def slug_words(slug):
    return [w for w in re.split(r'[-_]', slug) if w]

def detect_type(wlist):
    lw = [w.lower() for w in wlist]
    is_auto = any(w in AUTO_WORDS for w in lw)
    is_fem  = any(w in FEM_WORDS  for w in lw)
    is_reg  = any(w in REG_WORDS  for w in lw)
    is_cbd  = any(w in CBD_WORDS  for w in lw)
    if is_auto and is_fem: return 'auto fem'
    if is_auto:  return 'auto'
    if is_fem:   return 'feminized'
    if is_reg:   return 'regular'
    if is_cbd:   return 'cbd'
    return ''

def detect_pack(wlist):
    drop = set()
    pack = ''
    for i, w in enumerate(wlist):
        if not w.isdigit(): continue
        nxt = wlist[i+1].lower() if i+1 < len(wlist) else ''
        prv = wlist[i-1].lower() if i > 0 else ''
        if nxt in ('seeds','seed','pack','pk'):
            pack = w; drop.update([i, i+1]); break
        if prv in ('pack','pk'):
            pack = w; drop.update([i-1, i]); break
    return pack, [w for j,w in enumerate(wlist) if j not in drop]

def to_name(wlist):
    out = []
    for w in wlist:
        lw = w.lower()
        if lw in NOISE: continue
        if lw in _NO_UPPER: out.append(lw)
        elif not w.isalpha(): out.append(w)
        elif len(w) <= 3: out.append(w.upper())
        else: out.append(w.capitalize())
    return ' '.join(out).strip()

def parse_slug(slug, type_hint=''):
    wlist = slug_words(slug)
    pack, wlist = detect_pack(wlist)
    ptype = detect_type(wlist) or type_hint
    wlist = [w for w in wlist if w.lower() not in TYPE_WORDS]
    strain = to_name(wlist)
    return strain, ptype, pack

# ── Vendor configs ────────────────────────────────────────────────────────────
# Each entry: (vendor_name, vendor_url, [(sitemap_url, filter_fn, type_hint), ...])

def keep_all(url): return True
def is_seed_product(url): return '/cannabis-seeds/' in url and url.count('/') >= 5
def not_clothes(url): return '/clothes/' not in url and '/thca' not in url.lower() and url != 'https://blimburnseeds.com/shop-online/'
def is_kannabia_seed(url): return '/seeds/' in url and '/headshop/' not in url and '/en/' in url

VENDORS = [
    (
        'FreeWorld Genetics', 'https://freeworldseedvault.com', 'woocommerce',
        [('https://freeworldseedvault.com/sitemap-1.xml',
          lambda u: '/product/' in u, '')]
    ),
    (
        'Herbies Seeds', 'https://herbiesheadshop.com', 'custom',
        [('https://herbiesheadshop.com/sitemaps/en.xml',
          lambda u: u.startswith('https://herbiesheadshop.com/cannabis-seeds/') and u.count('/') == 4, '')]
    ),
    (
        'Growers Choice Seeds', 'https://www.growerschoiceseeds.us', 'woocommerce',
        [('https://growerschoiceseeds.us/product-sitemap1.xml', keep_all, ''),
         ('https://growerschoiceseeds.us/product-sitemap2.xml', keep_all, '')]
    ),
    (
        'BC Bud Depot', 'https://bcbuddepot.com', 'woocommerce',
        [('https://bcbuddepot.com/product-sitemap.xml',
          lambda u: '/marijuana-seeds/' in u and u.count('/') >= 6, '')]
    ),
    (
        'Elev8 Seeds', 'https://elev8seeds.com', 'woocommerce',
        [('https://elev8seeds.com/product-sitemap.xml',
          lambda u: '/strains/' in u and 'gift-card' not in u and 'bundle' not in u, '')]
    ),
    (
        'North Atlantic Seed Co', 'https://www.northatlanticseed.com', 'woocommerce',
        [('https://www.northatlanticseed.com/wp-sitemap-posts-product-1.xml', keep_all, ''),
         ('https://www.northatlanticseed.com/wp-sitemap-posts-product-2.xml', keep_all, '')]
    ),
    (
        'Blimburn Seeds', 'https://blimburnseeds.com', 'woocommerce',
        [('https://blimburnseeds.com/product-sitemap.xml',
          lambda u: not_clothes(u) and 'thca' not in u.lower() and 'pre-roll' not in u.lower() and '/nutrients' not in u.lower() and '/tee-' not in u.lower(), ''),
         ('https://blimburnseeds.com/product-sitemap2.xml',
          lambda u: not_clothes(u) and 'thca' not in u.lower() and 'pre-roll' not in u.lower() and '/nutrients' not in u.lower() and '/tee-' not in u.lower(), '')]
    ),
    # Kannabia product sitemap is headshop gear only — skip for now
]

# ── Per-vendor slug parsers ───────────────────────────────────────────────────

def parse_url(url, vendor_name):
    parts = path_parts(url)
    slug  = last_slug(url)

    # BC Bud Depot: /marijuana-seeds/{type}/{slug}/ — type in path
    if 'bcbuddepot' in url:
        type_map = {'feminized': 'feminized', 'autoflowering': 'auto',
                    'regular': 'regular', 'cbd': 'cbd'}
        type_hint = type_map.get(parts[-2].lower(), '') if len(parts) >= 2 else ''
        strain, ptype, pack = parse_slug(slug, type_hint)
        return strain, ptype or type_hint, pack

    # Growers Choice: /{strain}-auto-flowering-feminized-cannabis-seeds/
    if 'growerschoiceseeds' in url:
        slug = re.sub(r'-(cannabis-)?seeds?$', '', slug)
        strain, ptype, pack = parse_slug(slug)
        return strain, ptype, pack

    # Herbies: /cannabis-seeds/{strain}-{type}
    if 'herbiesheadshop' in url:
        strain, ptype, pack = parse_slug(slug)
        return strain, ptype, pack

    # Blimburn: /{slug}/ — just strain name, type sometimes in slug
    if 'blimburnseeds' in url:
        strain, ptype, pack = parse_slug(slug)
        return strain, ptype, pack

    # Kannabia: /en/seeds/{slug}
    if 'kannabia' in url:
        strain, ptype, pack = parse_slug(slug)
        return strain, ptype, pack

    # Default: /product/{slug}/ or /strains/{slug}/
    strain, ptype, pack = parse_slug(slug)
    return strain, ptype, pack

# ── Main ──────────────────────────────────────────────────────────────────────

OUT_FIELDS = [
    'vendor_name', 'vendor_url', 'platform',
    'strain_name', 'breeder', 'product_type', 'pack_size',
    'product_url', 'strain_slug',
    'price_min', 'price_max', 'currency_type', 'in_stock',
]

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

rows = []
for vendor_name, vendor_url, platform, sitemap_configs in VENDORS:
    vendor_rows = []
    for sitemap_url, filter_fn, type_hint in sitemap_configs:
        urls = fetch_urls(sitemap_url)
        product_urls = [u for u in urls if filter_fn(u)]
        print(f"{vendor_name}: {sitemap_url.split('/')[-1]} → {len(product_urls)} products")
        for url in product_urls:
            strain, ptype, pack = parse_url(url, vendor_name)
            if not strain:
                continue
            vendor_rows.append({
                'vendor_name':   vendor_name,
                'vendor_url':    vendor_url,
                'platform':      platform,
                'strain_name':   strain,
                'breeder':       '',
                'product_type':  ptype,
                'pack_size':     pack,
                'product_url':   url,
                'strain_slug':   slugify(strain),
                'price_min':     '',
                'price_max':     '',
                'currency_type': '',
                'in_stock':      '',
            })
        time.sleep(0.5)

    # dedupe by product_url
    seen = set()
    for r in vendor_rows:
        if r['product_url'] not in seen:
            seen.add(r['product_url'])
            rows.append(r)

with open('assets/data/new_vendors.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
    w.writeheader()
    w.writerows(rows)

print(f"\nTotal rows written: {len(rows)}")
print("Output: assets/data/new_vendors.csv")

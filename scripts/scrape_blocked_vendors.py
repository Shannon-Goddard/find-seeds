import sys, csv, re, requests, time
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; find-seeds-bot/1.0)'}
TIMEOUT = 12

# ── Sitemap fetcher ───────────────────────────────────────────────────────────

def fetch_urls(url, delay=0.5):
    time.sleep(delay)
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200: return []
        root = ET.fromstring(r.content)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [u.text for u in root.findall('sm:url/sm:loc', ns)]
    except: return []

# ── Slug parser ───────────────────────────────────────────────────────────────

AUTO_WORDS = {'auto', 'autoflower', 'autoflowering', 'automatic', 'automatica',
              'automaticas', 'autoflowering'}
FEM_WORDS  = {'fem', 'feminized', 'feminised', 'feminizadas', 'feminisiert', 'feminized'}
REG_WORDS  = {'reg', 'regular', 'regulares'}
CBD_WORDS  = {'cbd'}
TYPE_WORDS = AUTO_WORDS | FEM_WORDS | REG_WORDS | CBD_WORDS

NOISE = {'seeds', 'seed', 'strain', 'pack', 'pk', 'cannabis', 'marijuana',
         'weed', 'strains', 'shop', 'online', 'buy', 'order', 'fast', 'version',
         'flowering', 'flower', 'herbies', 'pre', 'roll', 'thca', 'product',
         'feminizadas', 'automaticas', 'regulares'}

_NO_UPPER = {'the', 'to', 'of', 'in', 'at', 'by', 'for', 'and', 'or', 'a', 'an', 'x', 'man', 'van', 'de', 'la', 'le'}

def last_slug(url):
    parts = [p for p in urlparse(url).path.rstrip('/').split('/') if p]
    return parts[-1] if parts else ''

def slug_words(slug):
    # strip trailing -product-NNN or -NNN
    slug = re.sub(r'-product-\d+\.php$', '', slug)
    slug = re.sub(r'\.php$', '', slug)
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

def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

# ── Per-vendor URL parsers ────────────────────────────────────────────────────

def parse_alchimia(url):
    # /{strain}-{type}-product-{id}.php
    # type hint from path: feminizadas/automaticas/regulares
    slug = last_slug(url)
    slug = re.sub(r'-product-\d+\.php$', '', slug)
    type_hint = ''
    if 'feminizadas' in slug:   type_hint = 'feminized'
    elif 'automaticas' in slug: type_hint = 'auto'
    elif 'regulares' in slug:   type_hint = 'regular'
    return parse_slug(slug, type_hint)

def parse_homegrown(url):
    # /products/{strain}-{type}-marijuana-seeds
    slug = last_slug(url)
    slug = re.sub(r'-marijuana-seeds?$', '', slug)
    return parse_slug(slug)

def parse_ilgm(url):
    # /products/{strain}-{type}-seeds or /products/{strain}-seeds
    slug = last_slug(url)
    return parse_slug(slug)

def parse_seedsman(url):
    # /us-en/{strain}-{type}-seeds-{sku}
    slug = last_slug(url)
    # strip trailing SKU like -18-mrnmm
    slug = re.sub(r'-\d+-[a-z0-9]+$', '', slug)
    return parse_slug(slug)

def parse_dutch_passion(url):
    # /en/cannabis-seeds/{slug}
    slug = last_slug(url)
    return parse_slug(slug)

# ── Vendor configs ────────────────────────────────────────────────────────────

VENDORS = [
    {
        'name': 'Alchimia',
        'url':  'https://www.alchimiaweb.com',
        'platform': 'custom',
        'sitemaps': ['https://www.alchimiaweb.com/sitemap-products.xml'],
        'filter': lambda u: (
            'seed' in u.lower() or 'semilla' in u.lower() or
            'feminizadas' in u or 'automaticas' in u or 'regulares' in u
        ) and u.endswith('.php'),
        'parser': parse_alchimia,
    },
    {
        'name': 'Homegrown Cannabis Co',
        'url':  'https://homegrowncannabis.com',
        'platform': 'custom',
        'sitemaps': ['https://homegrowncannabis.com/media/sitemap/sitemap.xml'],
        'filter': lambda u: '/products/' in u and u != 'https://homegrowncannabis.com/products',
        'parser': parse_homegrown,
    },
    {
        'name': 'ILGM',
        'url':  'https://ilgm.com',
        'platform': 'custom',
        'sitemaps': ['https://ilgm.com/media/sitemap/sitemap.xml'],
        'filter': lambda u: '/products/' in u and 'seeds' in u,
        'parser': parse_ilgm,
    },
    {
        'name': 'Seedsman',
        'url':  'https://www.seedsman.com',
        'platform': 'custom',
        'sitemaps': ['https://www.seedsman.com/sitemaps/seedsman_usa_site_map_live.xml'],
        'filter': lambda u: '/us-en/' in u and '-seeds' in u and '/cannabis-seeds/' not in u,
        'parser': parse_seedsman,
    },
    {
        'name': 'Dutch Passion',
        'url':  'https://dutch-passion.com',
        'platform': 'custom',
        'sitemaps': ['https://dutch-passion.com/1_en_0_sitemap.xml'],
        'filter': lambda u: '/en/cannabis-seeds/' in u,
        'parser': parse_dutch_passion,
    },
]

OUT_FIELDS = [
    'vendor_name', 'vendor_url', 'platform',
    'strain_name', 'breeder', 'product_type', 'pack_size',
    'product_url', 'strain_slug',
    'price_min', 'price_max', 'currency_type', 'in_stock',
]

rows = []
for v in VENDORS:
    vendor_rows = []
    for sitemap_url in v['sitemaps']:
        delay = 2 if 'dutch-passion' in sitemap_url else 0.5
        urls = fetch_urls(sitemap_url, delay=delay)
        product_urls = [u for u in urls if v['filter'](u)]
        print(f"{v['name']}: {len(product_urls)} products from {sitemap_url.split('/')[-1]}")

        for url in product_urls:
            strain, ptype, pack = v['parser'](url)
            if not strain:
                continue
            vendor_rows.append({
                'vendor_name':   v['name'],
                'vendor_url':    v['url'],
                'platform':      v['platform'],
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

    seen = set()
    for r in vendor_rows:
        if r['product_url'] not in seen:
            seen.add(r['product_url'])
            rows.append(r)

with open('assets/data/new_vendors2.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
    w.writeheader()
    w.writerows(rows)

print(f"\nTotal rows: {len(rows)}")
print("Output: assets/data/new_vendors2.csv")

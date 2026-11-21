import csv
import re
import sys
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding='utf-8')

# ── Vendors to exclude entirely ──────────────────────────────────────────────
TRASH_VENDORS = {
    '3rd coast genetics',
    'adk grass',
    'jersey seedbank',
    'offensive selections',
    'rebel grown',
    'maui jane seed co.',
    'uruz seeds',
    'sunleafseed co',
    'muha meds',
    'solfire gardens',
}

# ── Type / noise word sets ────────────────────────────────────────────────────
AUTO_WORDS = {'auto', 'autoflower', 'autoflowering', 'automatic', 'automatica', 'automaticas'}
FEM_WORDS  = {'fem', 'feminized', 'feminised', 'feminizadas', 'feminisiert'}
REG_WORDS  = {'reg', 'regular', 'regulares'}
CBD_WORDS  = {'cbd'}
TYPE_WORDS = AUTO_WORDS | FEM_WORDS | REG_WORDS | CBD_WORDS

NOISE = {
    'seeds', 'seed', 'strain', 'seedpack', 'pack', 'pk',
    'copy', 'limited', 'edition', 'new', 'pre-sale', 'presale',
    'retired', 'collab', 'half', 'souvenir', 'bulk', 'wholesale',
    'en', 'de', 'fr', 'es', 'eng',
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def last_slug(url):
    parts = [p for p in urlparse(url).path.rstrip('/').split('/') if p]
    return parts[-1] if parts else ''

def path_parts(url):
    return [p for p in urlparse(url).path.rstrip('/').split('/') if p]

def words(slug):
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

def strip_type(wlist):
    return [w for w in wlist if w.lower() not in TYPE_WORDS]

def detect_pack(wlist):
    """Return (pack_str, remaining_words). Looks for N-seeds, N-pack, N-pk, pack-N."""
    drop = set()
    pack = ''
    for i, w in enumerate(wlist):
        if not w.isdigit():
            continue
        nxt = wlist[i+1].lower() if i+1 < len(wlist) else ''
        prv = wlist[i-1].lower() if i > 0 else ''
        if nxt in ('seeds', 'seed', 'pack', 'pk'):
            pack = w; drop.update([i, i+1]); break
        if prv in ('pack', 'pk'):
            pack = w; drop.update([i-1, i]); break
    return pack, [w for j, w in enumerate(wlist) if j not in drop]

# Short words that should NOT be uppercased
_NO_UPPER = {'the', 'to', 'of', 'in', 'at', 'by', 'for', 'and', 'or', 'a', 'an'}

def to_name(wlist):
    out = []
    for w in wlist:
        lw = w.lower()
        if lw in NOISE:
            continue
        if lw in _NO_UPPER:
            out.append(lw)
        # digits+letters like 3rd, 2nd stay as-is
        elif not w.isalpha():
            out.append(w)
        # short pure-alpha tokens → uppercase (OG, AK, XXL, IBL…)
        elif len(w) <= 3:
            out.append(w.upper())
        else:
            out.append(w.capitalize())
    return ' '.join(out).strip()

def strip_prefix(slug, prefix):
    """Remove 'prefix-' from start of slug if present."""
    if slug.startswith(prefix + '-'):
        return slug[len(prefix)+1:]
    return slug

def strip_suffix(slug, suffix):
    """Remove '-suffix' from end of slug if present."""
    if slug.endswith('-' + suffix):
        return slug[:-(len(suffix)+1)]
    return slug

# ── Per-vendor parse functions ────────────────────────────────────────────────
# Each returns (strain, product_type, pack_size, breeder)
# Return None to fall back to existing catalog values unchanged.

def parse_default(url, row):
    """Most vendors: /product/{strain-slug}/ — slug IS the strain name."""
    slug = last_slug(url)
    if not slug:
        return None
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    pack, wlist = detect_pack(wlist)
    strain = to_name(wlist)
    return strain, ptype, pack, ''

def parse_nirvana(url, row):
    # /products/{strain}-{type}-{pack}-seeds
    slug = last_slug(url)
    wlist = words(slug)
    pack, wlist = detect_pack(wlist)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, pack, 'Nirvana Seeds'

def parse_00seeds(url, row):
    # type from category path: /automaticas/ or /feminizadas/
    parts = path_parts(url)
    slug = last_slug(url)
    # strip vendor suffix from slug
    slug = strip_suffix(slug, '00-seeds')
    wlist = words(slug)
    # type from path category
    cat = parts[1].lower() if len(parts) > 1 else ''
    if 'automaticas' in cat:
        ptype = 'auto'
    elif 'feminizadas' in cat:
        ptype = 'feminized'
    else:
        ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    _, wlist = detect_pack(wlist)
    return to_name(wlist), ptype, '', '00 Seeds'

def parse_advanced_seeds(url, row):
    # same pattern as 00seeds
    parts = path_parts(url)
    slug = last_slug(url)
    wlist = words(slug)
    cat = parts[1].lower() if len(parts) > 1 else ''
    if 'automaticas' in cat:
        ptype = 'auto'
    elif 'feminizadas' in cat:
        ptype = 'feminized'
    else:
        ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    _, wlist = detect_pack(wlist)
    return to_name(wlist), ptype, '', 'Advanced Seeds'

def parse_seedcellar(url, row):
    # /shop/cannabis-breeders/{breeder-slug}/{breeder-slug}-{strain}-{type}-{pack}-pk-{rev}/
    parts = path_parts(url)
    if len(parts) < 4:
        return None
    breeder_slug = parts[2]
    breeder = breeder_slug.replace('-', ' ').title()
    slug = last_slug(url)
    slug = strip_prefix(slug, breeder_slug)
    slug = re.sub(r'-\d+$', '', slug)   # strip trailing revision number
    wlist = words(slug)
    pack, wlist = detect_pack(wlist)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, pack, breeder

def parse_amsterdam(url, row):
    # /en/{strain}-{N}-pack-{breeder} or /en/{strain}-{N}pack-{breeder}
    slug = last_slug(url)
    m = re.search(r'-(\d+)-?pack-(.+)$', slug)
    if m:
        pack = m.group(1)
        breeder = m.group(2).replace('-', ' ').title()
        slug = slug[:m.start()]
    else:
        pack = ''
        # breeder is last word(s) ending in -seeds or -genetics etc.
        m2 = re.search(r'-([a-z][a-z-]+(?:seeds?|genetics|farms?|co))$', slug)
        if m2:
            breeder = m2.group(1).replace('-', ' ').title()
            slug = slug[:m2.start()]
        else:
            breeder = ''
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, pack, breeder

def parse_multiverse(url, row):
    # /product/{breeder}-{strain}-{type}-{pack}-pack/
    slug = last_slug(url)
    slug = re.sub(r'-strain$', '', slug)
    # known breeder prefixes for multiverse
    BREEDERS = [
        'ethos-genetics', 'humboldt-seed-co', '3rdshiftgenetics',
        '3rd-shift-genetics', 'cali-connection', 'fast-buds',
        'tastebudz-genetics', 'bloom-seed-co', 'ace-seeds',
        'anesia-seeds', 'compound-genetics', 'paradise-seeds',
    ]
    breeder = ''
    for b in sorted(BREEDERS, key=len, reverse=True):
        if slug.startswith(b + '-'):
            breeder = b.replace('-', ' ').title()
            slug = slug[len(b)+1:]
            break
    wlist = words(slug)
    pack, wlist = detect_pack(wlist)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, pack, breeder

def parse_seedslocker(url, row):
    # /product/{breeder}-{strain}-{type}-{pack}-pack/
    return parse_multiverse(url, row)

def parse_socal(url, row):
    # /product/{breeder}-{strain}-{type}-seeds/
    slug = last_slug(url)
    BREEDERS = [
        'ace-seeds', 'fast-buds', 'humboldt-seed-co', 'anesia-seeds',
        'compound-genetics', 'paradise-seeds', 'barneys-farm',
        'dutch-passion', 'royal-queen-seeds', 'dinafem',
    ]
    breeder = ''
    for b in sorted(BREEDERS, key=len, reverse=True):
        if slug.startswith(b + '-'):
            breeder = b.replace('-', ' ').title()
            slug = slug[len(b)+1:]
            break
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    _, wlist = detect_pack(wlist)
    return to_name(wlist), ptype, '', breeder

def parse_dc_seed_exchange(url, row):
    # /product/{breeder}-{strain}-{pack}-{type}-seeds/
    # pack appears as trailing number before type word, e.g. dream-f3-10-feminized
    slug = last_slug(url)
    BREEDERS = [
        'humboldt-seed-co', 'humboldt-seed', 'humboldt',
        'ed-rosenthals', 'fast-buds', 'ace-seeds',
    ]
    breeder = ''
    for b in sorted(BREEDERS, key=len, reverse=True):
        if slug.startswith(b + '-'):
            breeder = b.replace('-', ' ').title()
            # normalize humboldt variants
            if 'humboldt' in breeder.lower():
                breeder = 'Humboldt Seed Co'
            slug = slug[len(b)+1:]
            break
    wlist = words(slug)
    # strip trailing number that precedes type word (pack size)
    pack = ''
    if len(wlist) >= 2 and wlist[-2].isdigit() and wlist[-1].lower() in TYPE_WORDS | {'seeds','seed','autoflowering'}:
        pack = wlist[-2]
        wlist = wlist[:-2] + wlist[-1:]
    elif len(wlist) >= 1 and wlist[-1].isdigit():
        pack = wlist[-1]
        wlist = wlist[:-1]
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    _, wlist = detect_pack(wlist)
    return to_name(wlist), ptype, pack, breeder

def parse_walipini(url, row):
    # /product/{breeder}-{strain}-{type}-{pack}-pack/
    return parse_multiverse(url, row)

def parse_brownbag(url, row):
    # /product/{breeder}-{strain}/
    slug = last_slug(url)
    BREEDERS = [
        'bloom-seed-co', 'boston-roots', 'compound-genetics',
        'archive-seed-bank', 'ethos-genetics',
    ]
    breeder = ''
    for b in sorted(BREEDERS, key=len, reverse=True):
        if slug.startswith(b + '-'):
            breeder = b.replace('-', ' ').title()
            slug = slug[len(b)+1:]
            break
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, '', breeder

def parse_darkstar(url, row):
    # /product/{breeder}-{strain}/
    slug = last_slug(url)
    parts = slug.split('-')
    # breeder is first 2-3 words before known strain words
    # heuristic: if first word matches a known breeder start, grab up to 3 words
    BREEDERS = [
        '3rd-coast-genetics', 'fast-buds', 'humboldt-seed-co',
        'ace-seeds', 'compound-genetics', 'ethos-genetics',
        'archive-seed-bank', 'barneys-farm',
    ]
    breeder = ''
    for b in sorted(BREEDERS, key=len, reverse=True):
        if slug.startswith(b + '-'):
            breeder = b.replace('-', ' ').title()
            slug = slug[len(b)+1:]
            break
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, '', breeder

def parse_freedom_of_seeds(url, row):
    # /product/{strain}-{type}-seeds-{pack}/  (trailing number = pack)
    slug = last_slug(url)
    slug = re.sub(r'-\d+$', '', slug)   # strip trailing pack number
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    _, wlist = detect_pack(wlist)
    return to_name(wlist), ptype, '', ''

def parse_terpy(url, row):
    # /product/{breeder}-{strain}/  breeder is first 2 words
    slug = last_slug(url)
    BREEDERS = [
        '3rd-coast', 'fast-buds', 'humboldt-seed-co', 'ace-seeds',
    ]
    breeder = ''
    for b in sorted(BREEDERS, key=len, reverse=True):
        if slug.startswith(b + '-'):
            breeder = b.replace('-', ' ').title()
            slug = slug[len(b)+1:]
            break
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, '', breeder

def parse_aloha(url, row):
    # /products/hawaiian-pakalolo/{strain}-{numeric-id}
    slug = last_slug(url)
    slug = re.sub(r'-\d+$', '', slug)   # strip trailing numeric ID
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, '', 'Aloha Embassy'

def parse_swami(url, row):
    # /products/{strain}-{numeric-id}
    slug = last_slug(url)
    slug = re.sub(r'-p\d+$', '', slug)  # strip -p552470159 style IDs
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, '', 'Swami Organic Seed'

def parse_homegrown(url, row):
    # /product/{strain}/{numeric-id}/
    parts = path_parts(url)
    slug = parts[-2] if len(parts) >= 2 and parts[-1].isdigit() else last_slug(url)
    wlist = words(slug)
    ptype = detect_type(wlist)
    wlist = strip_type(wlist)
    return to_name(wlist), ptype, '', ''

def parse_berserk(url, row):
    # /products/{cross-description}  — strain_name from catalog is cleaner
    # just extract type from slug
    slug = last_slug(url)
    wlist = words(slug)
    ptype = detect_type(wlist)
    existing = row.get('strain_name', '').strip().title()
    return existing, ptype, '', ''

# ── Vendor dispatch table ─────────────────────────────────────────────────────
VENDOR_PARSERS = {
    'nirvana seeds':                    parse_nirvana,
    '00 seeds':                         parse_00seeds,
    'advanced seeds':                   parse_advanced_seeds,
    'seed cellar':                      parse_seedcellar,
    'amsterdam seed center':            parse_amsterdam,
    'multiverse genetics':              parse_multiverse,
    'seeds locker':                     parse_seedslocker,
    'socal seed vault':                 parse_socal,
    'dc seed exchange':                 parse_dc_seed_exchange,
    'walipini seeds':                   parse_walipini,
    'brown bag farm goods':             parse_brownbag,
    'darkstar genetics seed bank':      parse_darkstar,
    'freedom of seeds':                 parse_freedom_of_seeds,
    'terpy seeds':                      parse_terpy,
    'aloha embassy':                    parse_aloha,
    'swami organic seed':               parse_swami,
    'homegrown genetics':               parse_homegrown,
    'berserk genetics':                 parse_berserk,
}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    in_path  = 'assets/data/catalog_data.csv'
    out_path = 'assets/data/clean_catalog.csv'

    out_fields = [
        'vendor_name', 'vendor_url', 'platform',
        'strain_name', 'breeder', 'product_type', 'pack_size',
        'product_url', 'price_min', 'price_max', 'currency_type',
        'in_stock', 'tags', 'payment_methods', 'germ_guarantee',
        'shipping_regions', 'delivery', 'stealth_shipping',
        'min_order', 'loyalty_program', 'breeder_exclusive',
        'vendor_status', 'strain_slug', 'url_match',
    ]

    kept = skipped = 0

    with open(in_path, encoding='utf-8') as fin, \
         open(out_path, 'w', newline='', encoding='utf-8') as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        writer.writeheader()

        for row in reader:
            vendor = row['vendor_name'].strip().lower()

            if vendor in TRASH_VENDORS:
                skipped += 1
                continue

            kept += 1
            url    = row['product_url']
            parser = VENDOR_PARSERS.get(vendor, parse_default)
            result = parser(url, row)

            if result is None:
                strain  = row.get('strain_name', '').strip()
                ptype   = row.get('product_type', '').strip()
                pack    = ''
                breeder = row.get('breeder', '').strip()
            else:
                strain, ptype, pack, breeder = result
                if not strain:
                    strain = row.get('strain_name', '').strip()
                if not ptype:
                    ptype = row.get('product_type', '').strip()
                if not breeder:
                    breeder = row.get('breeder', '').strip()

            # clean pipe-separated types from original data
            if '|' in ptype:
                ptype = ptype.split('|')[0].strip()

            writer.writerow({
                'vendor_name':       row['vendor_name'],
                'vendor_url':        row['vendor_url'],
                'platform':          row['platform'],
                'strain_name':       strain,
                'breeder':           breeder,
                'product_type':      ptype,
                'pack_size':         pack,
                'product_url':       url,
                'price_min':         row['price_min'],
                'price_max':         row['price_max'],
                'currency_type':     row['currency_type'],
                'in_stock':          row['in_stock'],
                'tags':              row['tags'],
                'payment_methods':   row['payment_methods'],
                'germ_guarantee':    row['germ_guarantee'],
                'shipping_regions':  row['shipping_regions'],
                'delivery':          row['delivery'],
                'stealth_shipping':  row['stealth_shipping'],
                'min_order':         row['min_order'],
                'loyalty_program':   row['loyalty_program'],
                'breeder_exclusive': row['breeder_exclusive'],
                'vendor_status':     row['vendor_status'],
                'strain_slug':       row['strain_slug'],
                'url_match':         row['url_match'],
            })

    print(f"Kept:    {kept}")
    print(f"Trashed: {skipped}")
    print(f"Output:  {out_path}")

if __name__ == '__main__':
    main()

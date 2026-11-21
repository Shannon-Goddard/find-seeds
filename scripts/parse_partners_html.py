import sys, csv, re
sys.stdout.reconfigure(encoding='utf-8')

BTN_MAP = {
    'bcbd':     'bcbuddepot.com',
    'gc seeds': 'growerschoiceseeds.us',
    'hcc':      'homegrowncannabis.com',
    'asc':      'amsterdamseedcenter.com',
    'nasc':     'northatlanticseed.com',
}

DOMAIN_MAP = {
    '42 fast buds':            '2fast4buds.com',
    '420 seeds':               '420-seeds.com',
    'alchimia':                'alchimiaweb.com',
    'amsterdam seed center':   'amsterdamseedcenter.com',
    "barney's farm":           'barneysfarm.com',
    'bc bud depot':            'bcbuddepot.com',
    'blasted genetics':        'blastedgenetics.com',
    'blimburn':                'blimburnseeds.com',
    'canuk seeds':             'canukseeds.com',
    'dutch passion':           'dutch-passion.com',
    'elev8 seeds':             'elev8seeds.com',
    'freeworld genetics':      'freeworldseedvault.com',
    'growers choice':          'growerschoiceseeds.us',
    'herbies seeds':           'herbiesheadshop.com',
    'homegrown cannabis':      'homegrowncannabis.com',
    'ilgm':                    'ilgm.com',
    'kannabia':                'kannabia.com',
    'mass hydro':              'mass-hydro.com',
    'mavericks seeds':         'mavericksgenetics.com',
    'mephisto genetics':       'mephistogenetics.com',
    'msnl seeds':              'msnlseeds.com',
    'nirvana':                 'nirvanashop.com',
    'nasc':                    'northatlanticseed.com',
    'original sensible seeds': 'originalsensible.com',
    'paradise seeds':          'paradise-seeds.com',
    'royal queen seeds':       'royalqueenseeds.com',
    'seedsman':                'seedsman.com',
    'sensi seeds':             'sensiseeds.com',
    'true north':              'truenorthseedbank.com',
}

PAYMENT_MAP = {
    'credit/debit': 'credit card',
    'bitcoin':      'crypto',
    'bank transfer':'bank transfer',
    'cash':         'cash / money order',
    'check':        'cash / money order',
    'money orders': 'cash / money order',
    'zelle':        'digital wallet',
    'venmo':        'digital wallet',
    'cash app':     'digital wallet',
    'apple pay':    'digital wallet',
    'google pay':   'digital wallet',
    'paypal':       'digital wallet',
}

html = open('partners.html', encoding='utf-8').read()

# Each partner is preceded by an HTML comment: <!-- Partner Name -->
blocks = re.findall(
    r'<!--\s*([^-\n]+?)\s*-->\s*<div class="partner-row"([^>]*)>(.*?)</div>\s*</div>\s*</div>',
    html, re.DOTALL
)

rows = []
for comment_name, attrs, block in blocks:
    type_m = re.search(r'data-type="([^"]+)"', attrs)
    ship_m = re.search(r'data-shipping="([^"]+)"', attrs)
    if not type_m: continue
    ptype    = type_m.group(1)
    shipping = ship_m.group(1) if ship_m else ''
    if ptype == 'app': continue

    name   = comment_name.strip().lower()
    domain = DOMAIN_MAP.get(name, '') or BTN_MAP.get(name, '')
    if not domain:
        for k, v in DOMAIN_MAP.items():
            if k in name or name in k:
                domain = v
                break

    # Payment methods from icon titles
    titles  = re.findall(r'title="([^"]+)"', block)
    methods = set()
    for t in titles:
        tl = t.lower()
        for key, val in PAYMENT_MAP.items():
            if key in tl:
                methods.add(val)
                break
    payment = ' | '.join(sorted(methods))

    # Germination guarantee
    germ = 'no'
    shield_m = re.search(r'fa-shield-halved.*?<span>(.*?)</span>', block, re.DOTALL)
    if shield_m:
        g = shield_m.group(1).strip().lower()
        if any(x in g for x in ['germination', '90%', '95%', '100%', '85%', 'delivery & germ']):
            germ = 'yes'

    # Shipping
    region_map = {'usa': 'usa', 'intl': 'international', 'both': 'usa + international'}
    regions = region_map.get(shipping, '')

    rows.append({
        'vendor_domain':    domain,
        'partner_name':     name,
        'payment_methods':  payment,
        'germ_guarantee':   germ,
        'shipping_regions': regions,
        'stealth_shipping': 'yes',
        'loyalty_program':  'no',
        'breeder_type':     'own' if ptype == 'breeder' else 'multi',
        'vendor_status':    'active',
    })

# Write to vendor_info.csv — merge with existing, partners.html takes priority
OUT_FIELDS = ['vendor_domain','payment_methods','germ_guarantee','shipping_regions',
              'stealth_shipping','loyalty_program','breeder_type','vendor_status']

# Load existing vendor_info
existing = {}
with open('assets/data/vendor_info.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        existing[row['vendor_domain']] = row

# Merge: partners.html data overwrites existing for matched domains
for r in rows:
    if not r['vendor_domain']: continue
    existing[r['vendor_domain']] = {
        'vendor_domain':    r['vendor_domain'],
        'payment_methods':  r['payment_methods'],
        'germ_guarantee':   r['germ_guarantee'],
        'shipping_regions': r['shipping_regions'],
        'stealth_shipping': r['stealth_shipping'],
        'loyalty_program':  r['loyalty_program'],
        'breeder_type':     r['breeder_type'],
        'vendor_status':    r['vendor_status'],
    }

with open('assets/data/vendor_info.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
    w.writeheader()
    w.writerows(existing.values())

print(f"\nvendor_info.csv updated: {len(existing)} vendors")
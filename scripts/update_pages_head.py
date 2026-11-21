import os, re

PAGES_DIR = "pages"

OLD_FAVICON = '<link rel="icon" href="../assets/img/favicon.png" />'
NEW_FAVICON = '''  <link rel="icon" type="image/png" sizes="32x32" href="../assets/img/favicon-32.png" />
  <link rel="icon" type="image/png" sizes="16x16" href="../assets/img/favicon-16.png" />
  <link rel="apple-touch-icon" href="../assets/img/apple-touch.png" />
  <link rel="manifest" href="../site.webmanifest" />'''

GTM_BLOCK = '''  <!-- Google Tag Manager -->
  <script async src="https://www.googletagmanager.com/gtm.js?id=GTM-NX38C59R"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
  </script>'''

for fname in os.listdir(PAGES_DIR):
    if not fname.endswith(".html"):
        continue
    path = os.path.join(PAGES_DIR, fname)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    # Replace favicon
    html = html.replace(OLD_FAVICON, NEW_FAVICON)

    # Inject GTM after <body> if not already present
    if "GTM-NX38C59R" not in html:
        html = html.replace("<body>", f"<body>\n{GTM_BLOCK}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated {fname}")

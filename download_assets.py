"""
Download all the external static files in the `static/ext/` directory.
"""
from pathlib import Path
from posixpath import basename

import requests

# Create the output folder
base_path = Path("static/ext")
base_path.mkdir(parents=True, exist_ok=True)

# Fetch the latest Sentry SDK version to get the bundle
resp = requests.get("https://registry.npmjs.org/@sentry/browser/latest")
resp.raise_for_status()
data = resp.json()

urls = [
    f"https://browser.sentry-cdn.com/{data['version']}/bundle.tracing.replay.min.js",
    "https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js",
    "https://cdn.jsdelivr.net/npm/alpinejs-i18n@2/dist/cdn.min.js",
    "https://cdn.jsdelivr.net/npm/eruda@3/eruda.min.js",
    "https://cdn.jsdelivr.net/npm/jszip@3/dist/jszip.min.js",
    "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml-full.js",
    "https://cdn.jsdelivr.net/npm/sql.js@1/dist/sql-wasm.js",
    "https://cdn.jsdelivr.net/npm/sql.js@1/dist/sql-wasm.wasm",
    "https://cdn.jsdelivr.net/npm/tablesort@5/dist/tablesort.min.js",
]
# Save some files with better filenames
mappings = {
    "alpinejs-i18n": "i18n.min.js",
    "mathjax": "mathjax.min.js",
}

for url in urls:
    print(f"Downloading {url} ... ", end="")

    name = basename(url)
    for item, repl in mappings.items():
        if item in url:
            name = repl
            break

    output = base_path / name
    with output.open("wb") as f:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    print("OK")

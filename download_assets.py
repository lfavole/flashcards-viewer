from pathlib import Path
from posixpath import basename

import requests

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
    "https://cdn.jsdelivr.net/npm/sql.js@1/dist/sql-wasm.js",
    "https://cdn.jsdelivr.net/npm/sql.js@1/dist/sql-wasm.wasm",
    "https://cdn.jsdelivr.net/npm/tablesort@5/dist/tablesort.min.js",
]

for url in urls:
    print(f"Downloading {url}... ", end="")
    output = base_path / basename(url)
    with output.open("wb") as f:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        for chunk in resp.iter_content(65536):
            f.write(chunk)
    print("OK")

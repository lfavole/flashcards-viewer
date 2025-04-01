"""
Download all the external static files in the `static/ext/` directory.
"""
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path
from posixpath import basename

def check_response(response):
    if response.status != 200:
        raise Exception(f"Failed to download {response.url}: {response.status}")

# Create the output folder
base_path = Path("static/ext")
base_path.mkdir(parents=True, exist_ok=True)

# Fetch the latest Sentry SDK version to get the bundle
print("Fetching latest Sentry SDK version... ", end="")
with urllib.request.urlopen("https://registry.npmjs.org/@sentry/browser/latest") as response:
    check_response(response)
    data = json.load(response)
    sentry_version = data["version"]

print(f"OK ({sentry_version})")

# Download MathJax and extract it to base_path / "mathjax"
print("Fetching MathJax URL... ", end="")
with urllib.request.urlopen("https://registry.npmjs.org/mathjax/latest") as response:
    check_response(response)
    data = json.load(response)
    url = data["dist"]["tarball"]

print(f"OK ({url})")

print(f"Downloading MathJax from '{url}'... ", end="")
with urllib.request.urlopen(url) as response:
    check_response(response)
    buffer = io.BytesIO()
    shutil.copyfileobj(response, buffer)

print("OK")

PREFIX = "package/es5/"

# Extract everything to the base_path / "mathjax" directory
print("Extracting MathJax... ", end="")

mathjax_path = base_path / "mathjax"
if mathjax_path.exists():
    shutil.rmtree(mathjax_path)
mathjax_path.mkdir(parents=True)

extracted_files = 0
buffer.seek(0)
with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
    for member in tar.getmembers():
        if not member.name.startswith(PREFIX):
            continue
        member.name = member.name.removeprefix(PREFIX)
        # it it's in a nested directory that is not "output", don't copy it
        if not member.name.startswith("output/") and Path(member.name).name != member.name:
            continue
        tar.extract(member, path=mathjax_path)
        extracted_files += 1

print(f"OK ({extracted_files} files extracted)")

urls = [
    f"https://browser.sentry-cdn.com/{sentry_version}/bundle.tracing.replay.min.js",
    "https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js",
    "https://cdn.jsdelivr.net/npm/alpinejs-i18n@2/dist/cdn.min.js",
    "https://cdn.jsdelivr.net/npm/eruda@3/eruda.min.js",
    "https://cdn.jsdelivr.net/npm/jszip@3/dist/jszip.min.js",
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
    print(f"Downloading '{url}'... ", end="")

    name = basename(url)
    for item, repl in mappings.items():
        if item in url:
            name = repl
            break

    output = base_path / name
    with output.open("wb") as f, urllib.request.urlopen(url) as response:
        check_response(response)
        shutil.copyfileobj(response, f)

    print("OK")

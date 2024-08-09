import subprocess as sp
from pathlib import Path

files_to_edit = [*Path("site/static").iterdir(), Path("site/index.html")]

for file in files_to_edit:
    if file.suffix == ".html":
        print(f"Minifying {file} with html-minifier")
        sp.run(["html-minifier", "--collapse-whitespace", "--remove-comments", "--remove-optional-tags", "--remove-redundant-attributes", "--remove-script-type-attributes", "--remove-tag-whitespace", "--use-short-doctype", "--minify-css", "true", "--minify-js", "true", str(file), "--output", str(file)], check=True)

    elif file.suffix == ".css":
        print(f"Minifying {file} with csso")
        sp.run(["csso", str(file), "--source-map", "file", "--output", str(file)], check=True)

    elif file.suffix == ".js":
        print(f"Minifying {file} with uglifyjs")
        sp.run(["uglifyjs", str(file), "--source-map", "--output", str(file)], check=True)

    else:
        print(f"Skipping minification of {file}, no minifier available")

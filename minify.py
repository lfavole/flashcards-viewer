from pathlib import Path
import re
import subprocess as sp

import minify_html


def minify_with_prefix(code, prefix, file: str | Path = "snippet"):
    try:
        return minify_html.minify(
            prefix + code,
            do_not_minify_doctype=True,
            minify_css=True,
            minify_js=True,
        ).removeprefix(prefix)
    except BaseException as exc:
        print(
            f"::warning title=Minification of {file} failed"
            + (", skipping file" if file != "snippet" else "")
            + f"::{type(exc).__qualname__}: {exc}"
        )
        return code


def minify_js(js):
    try:
        return (
            sp.run(
                ["uglifyjs", "--beautify", "beautify=false", "quote_style=3"],
                stdout=sp.PIPE,
                input=js,
                text=True,
                encoding="utf-8",
                check=True,
            )
            .stdout.rstrip()
            .rstrip(";")
        )
    except sp.CalledProcessError as exc:
        print(f"::warning title=Minification of snippet failed::{type(exc).__qualname__}: {exc}")
        return js


files_to_edit = [*Path("site/static").glob("**/*"), Path("site/index.html")]

for file in files_to_edit:
    if file.is_dir():
        continue

    if file.suffix == ".js":
        print(f"Minifying {file} with UglifyJS")
        try:
            sp.run(["uglifyjs", str(file), "--source-map", "--output", str(file)], check=True)
        except sp.CalledProcessError as exc:
            print(f"::warning title=Minification of {file} failed, skipping file::{type(exc).__qualname__}: {exc}")
        continue

    prefix = {".html": "", ".css": "<style>", ".js": "<script>"}.get(file.suffix)

    if prefix is not None:
        print(f"Minifying {file}")

        data = file.read_text("utf-8")
        if file.suffix == ".html":
            # Minify JavaScript attributes (Alpine.js)
            data = re.sub(
                r"=([\"'])(.*?)\1",
                lambda match: "=" + match[1] + minify_js(match[2]) + match[1],
                data,
            )

        data = minify_with_prefix(data, prefix, file)

        file.write_text(data, "utf-8")

    else:
        print(f"Skipping minification of {file}, no minifier available")

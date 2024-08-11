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


def _minify_js(js, quote=None):
    quote_style = []
    if quote is not None:
        # 1 = single quotes = to use when there are double quotes
        # 2 = double quotes = to use when there are single quotes
        # https://github.com/mishoo/UglifyJS#command-line-options
        quote_style = ["--beautify", "beautify=false,quote_style=" + ("1" if quote == '"' else "2")]

    try:
        return (
            sp.run(
                ["uglifyjs", "--compress", "--module", *quote_style],
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
        print(f"::warning title=Minification of snippet '{js}' failed::{type(exc).__qualname__}: {exc}")
        return js


def minify_js(js, quote=None, recursive=False):
    ret = sorted([_minify_js(js, quote), _minify_js("x=" + js, quote).removeprefix("x=")], key=len)[0]
    if " " not in ret and ('"' in ret or "'" in ret) and not recursive:
        # if there are no spaces but there are quotes, re-minify with the optimal quotes
        return minify_js(js, recursive=True)
    return ret


def minify_attribute(match):
    name, quote, value = match.groups()
    if not any(name.startswith(prefix) for prefix in (":", "@", "x-", "on")):
        return match[0]
    return f"{name}={quote}{minify_js(value, quote)}{quote}"


files_to_edit = [*Path("site/static").glob("**/*"), Path("site/index.html")]

for file in files_to_edit:
    file = file.resolve()
    if file.is_dir():
        continue

    if file.suffix == ".css":
        print(f"Minifying {file} with LightningCSS")
        try:
            sp.run(
                [
                    "lightningcss",
                    "--minify",
                    "--bundle",
                    "--targets",
                    ">= 0.5%",
                    "--sourcemap",
                    str(file),
                    "--output-file",
                    str(file),
                ],
                cwd=Path("site"),
                check=True,
            )
        except sp.CalledProcessError as exc:
            print(f"::warning title=Minification of {file} failed, skipping file::{type(exc).__qualname__}: {exc}")
        continue

    if file.suffix == ".js":
        print(f"Minifying {file} with UglifyJS")
        try:
            sp.run(["uglifyjs", str(file), "--compress", "--source-map", "--output", str(file)], cwd=Path("site"), check=True)
        except sp.CalledProcessError as exc:
            print(f"::warning title=Minification of {file} failed, skipping file::{type(exc).__qualname__}: {exc}")
        continue

    prefix = {".html": "", ".css": "<style>", ".js": "<script>"}.get(file.suffix)

    if prefix is not None:
        print(f"Minifying {file}")

        data = file.read_text("utf-8")
        if file.suffix == ".html":
            # Minify JavaScript attributes (Alpine.js)
            # https://html.spec.whatwg.org/multipage/syntax.html#syntax-attribute-name
            data = re.sub(r"([^\s\"'>/=]+)=([\"'])(.*?)\2", minify_attribute, data)

        data = minify_with_prefix(data, prefix, file)

        file.write_text(data, "utf-8")

    else:
        print(f"Skipping minification of {file}, no minifier available")

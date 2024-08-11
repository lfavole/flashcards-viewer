from pathlib import Path
import re
import subprocess as sp

import minify_html


def _minify_js(js, quote=None, expression=False, recursive=False):
    expression_opt = ["--expression"] if expression else []
    quote_style = []
    if quote is not None:
        # 1 = single quotes = to use when there are double quotes
        # 2 = double quotes = to use when there are single quotes
        # https://github.com/mishoo/UglifyJS#command-line-options
        quote_style = ["--beautify", "beautify=false,quote_style=" + ("1" if quote == '"' else "2")]

    if recursive:
        js = "(async()=>{" + js + "})()"

    try:
        DOUBLE_QUOTE = '"'
        print(
            f"::debug::Minifying {js}"
            + (" in expression mode" if expression else "")
            + (f" with {'double' if quote == DOUBLE_QUOTE else 'single'} quotes" if quote is not None else "")
        )
        ret = (
            sp.run(
                ["uglifyjs", "--compress", "--module", *expression_opt, *quote_style],
                stdout=sp.PIPE,
                input=js,
                text=True,
                encoding="utf-8",
                check=True,
            )
            .stdout.rstrip()
            .rstrip(";")
        )
        print(f"::debug::Output: {ret}")
        if recursive:
            ret = ret.removeprefix("(async()=>").removeprefix("{").removesuffix(")()").removesuffix("}")
        return ret
    except sp.CalledProcessError as exc:
        print(f"::warning title=Minification of snippet '{js}' failed::{type(exc).__qualname__}: {exc}")
        if not recursive:
            return _minify_js(js, quote, expression, recursive=True)
        return js


def minify_js_with_quotes(js, quote=None, expression=False, recursive=False):
    ret = _minify_js(js, quote, expression)
    if " " not in ret and ('"' in ret or "'" in ret) and not recursive:
        # if there are no spaces but there are quotes, re-minify with the optimal quotes
        # (because minify-html will remove the quotes)
        print("::debug::Re-minifying with the optimal quotes")
        return minify_js_with_quotes(js, expression=expression, recursive=True)
    return quote or "", ret


def minify_attribute(match):
    name, quote, value = match.groups()
    if not any(name.startswith(prefix) for prefix in (":", "@", "x-", "on")):
        return match[0]
    # Use expression mode only for some attributes
    # e.g. a&&"b" in non-expression mode evaluates to a (because "b" is truthy)
    expression = name.startswith("x-") and name not in {"x-init", "x-effect"} or name[0] == ":"
    # Get the new quote to use
    # Don't reuse the original quotes because we may end up with:
    # <a b="c" d="e="f""> which minifies to: <a b=c d=e= f""> (invalid HTML)
    quote, value = minify_js_with_quotes(value, quote, expression)
    return f"{name}={quote}{value}{quote}"


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
            sp.run(
                ["uglifyjs", str(file), "--compress", "--source-map", "--output", str(file)],
                cwd=Path("site"),
                check=True,
            )
        except sp.CalledProcessError as exc:
            print(f"::warning title=Minification of {file} failed, skipping file::{type(exc).__qualname__}: {exc}")
        continue

    if file.suffix == ".html":
        print(f"Minifying {file} with minify-html")

        data = file.read_text("utf-8")
        if file.suffix == ".html":
            # Minify JavaScript attributes (Alpine.js)
            # https://html.spec.whatwg.org/multipage/syntax.html#syntax-attribute-name
            data = re.sub(r"(?<=[\"'\s])([^\s\"'>/=]+?)=([\"'])(.*?)\2", minify_attribute, data)

        try:
            data = minify_html.minify(
                data,
                do_not_minify_doctype=True,
                minify_css=True,
                minify_js=True,
            )
        except BaseException as exc:
            print(f"::warning title=Minification of {file} failed::{type(exc).__qualname__}: {exc}")

        file.write_text(data, "utf-8")

    else:
        print(f"Skipping minification of {file}, no minifier available")

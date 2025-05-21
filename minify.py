"""
Minify all the files in the `site/` directory with minify-html, LightningCSS or UglifyJS.
"""

import re
import subprocess as sp
from pathlib import Path
from threading import Thread

import minify_html


def _minify_js(js: str, quote: str | None = None, expression=False, try_async=False) -> str:
    """
    Return a minified version of the given JavaScript code.

    The function handles forcing a specific quote, expression mode and `async` expressions.
    """
    expression_opt = ["--expression"] if expression else []
    quote_style = []
    if quote is not None:
        # 1 = single quotes = to use when there are double quotes
        # 2 = double quotes = to use when there are single quotes
        # https://github.com/mishoo/UglifyJS#command-line-options
        quote_style = ["--beautify", "beautify=false,quote_style=" + ("1" if quote == '"' else "2")]

    if try_async:
        js = "(async()=>{" + js + "})()"

    try:
        DOUBLE_QUOTE = '"'
        replace_newlines = lambda text: text.replace('\n', '\\n')
        print(
            f"::debug::Minifying {replace_newlines(js)}"
            + (" in expression mode" if expression else "")
            + (f" with {'double' if quote == DOUBLE_QUOTE else 'single'} quotes" if quote is not None else "")
        )
        ret = (
            sp.run(
                ["uglifyjs", "--compress", "--mangle", "--module", *expression_opt, *quote_style],
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
        if try_async:
            # Remove in two steps because { and } may have been stripped
            # e.g. (async () => { {a: "b"} })()
            ret = ret.removeprefix("(async()=>{").removesuffix("})()")
        return ret
    except sp.CalledProcessError as exc:
        print(f"::warning title=Minification of snippet '{js}' failed::{type(exc).__qualname__}: {exc}")
        if not try_async:
            return _minify_js(js, quote, expression, try_async=True)
        return js


def minify_js_with_quotes(js: str, expression=False):
    """
    Return a minified JavaScript attribute with its quotes.

    The function tries with single, double and no quotes to get the shortest output.
    """
    js, quote = sorted(
        [
            # Put double quotes first to select them if the length is the same
            (_minify_js(js, '"', expression), '"'),
            (_minify_js(js, "'", expression), "'"),
        ],
        key=lambda item: len(item[0]),
    )[0]
    if " " not in js and ('"' in js or "'" in js):
        # If there are no spaces but there are quotes, re-minify with the optimal quotes
        # (because minify-html will remove the quotes)
        print("::debug::Re-minifying with the optimal quotes")
        return _minify_js(js, expression=expression), ""
    return js, quote


def minify_attribute(match: re.Match[str]):
    """
    Given a `re.Match` object with (name, quote, value) groups,
    return the minified attribute (by minifying JS and optionally removing quotes).
    """
    name, quote, value = match.groups()
    if not any(name.startswith(prefix) for prefix in (":", "@", "x-", "on")):
        return match[0]

    # Use expression mode only for some attributes
    # (Alpine.js directives except x-init, x-effect and attributes)
    # e.g. a&&"b" in non-expression mode evaluates to a (because "b" is truthy)
    expression = name.startswith("x-") and name not in {"x-init", "x-effect"} or name[0] == ":"

    # Get the quote to use
    # Don't reuse the original quotes because we may end up with:
    # <a b="c" d="e="f""> which minifies to: <a b=c d=e= f""> (invalid HTML)
    value, quote = minify_js_with_quotes(value, expression)
    # Keep spacing before and after "in" (used in x-for)
    value = re.sub(r"\s*\bin\b\s*", " in ", value)
    return f"{name}={quote}{value}{quote}"


files_to_edit = [*Path("site/static").glob("**/*"), Path("site/index.html")]


def run_minify_html(file: Path):
    print(f"Minifying {file} with minify-html")

    data = file.read_text("utf-8")
    if file.suffix == ".html":
        # Minify JavaScript attributes (Alpine.js)
        # https://html.spec.whatwg.org/multipage/syntax.html#syntax-attribute-name
        data = re.sub(r"(?s)(?<=[\"'\s])([^\s\"'>/=]+?)=([\"'])(.*?)\2", minify_attribute, data)

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


def run_minify_css(file: Path):
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
    else:
        data = file.read_text("utf-8")
        data = re.sub(r"# sourceMappingURL=.*/([^/\s]*)\b", r"# sourceMappingURL=\1", data)
        file.write_text(data, "utf-8")


def run_minify_js(file: Path):
    print(f"Minifying {file} with UglifyJS")
    try:
        sp.run(
            ["uglifyjs", str(file), "--compress", "--mangle", "--source-map", "--output", str(file)],
            cwd=Path("site"),
            check=True,
        )
    except sp.CalledProcessError as exc:
        print(f"::warning title=Minification of {file} failed, skipping file::{type(exc).__qualname__}: {exc}")


for file in files_to_edit:
    # Resolve the path to avoid source map paths errors
    file = file.resolve()
    # Skip directories
    if file.is_dir():
        continue

    if file.suffix == ".html":
        Thread(target=run_minify_html, args=[file]).start()
        continue

    if file.suffix == ".css":
        Thread(target=run_minify_css, args=[file]).start()
        continue

    if file.suffix == ".js":
        Thread(target=run_minify_js, args=[file]).start()
        continue

    print(f"Skipping minification of {file}, no minifier available")

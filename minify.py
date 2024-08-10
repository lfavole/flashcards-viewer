from pathlib import Path

import minify_html

files_to_edit = [*Path("site/static").glob("**/*"), Path("site/index.html")]

for file in files_to_edit:
    if file.is_dir():
        continue

    prefix = {".html": "", ".css": "<style>", ".js": "<script>"}.get(file.suffix)

    if prefix is not None:
        print(f"Minifying {file}")

        data = file.read_text("utf-8")
        try:
            data = minify_html.minify(
                prefix + data,
                do_not_minify_doctype=True,
                minify_css=True,
                minify_js=True,
            ).removeprefix(prefix)
        except BaseException as exc:
            print(
                f"::warning title=Minification of {file} failed, skipping file::{type(exc).__qualname__}: {exc}"
            )
        else:
            file.write_text(data, "utf-8")

    else:
        print(f"Skipping minification of {file}, no minifier available")

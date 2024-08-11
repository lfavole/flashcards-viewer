import os
from pathlib import Path

index_file = Path("site/index.html")
sentry_file = Path("site/static/sentry.js")
index_data = index_file.read_text("utf-8")
sentry_data = sentry_file.read_text("utf-8")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    print("Adding Sentry script in head")
    index_data = index_data.replace(
        "</head>",
        '    <script src="static/sentry.js" async></script></script>\n</head>',
    )
    index_file.write_text(index_data, "utf-8")

    print("Adding Sentry DSN in script")
    sentry_data = sentry_data.replace('SENTRY_DSN = ""', f'SENTRY_DSN = "{SENTRY_DSN}"')
    sentry_file.write_text(sentry_data, "utf-8")
else:
    print("::warning title=No Sentry DSN available::Skipping Sentry DSN injection")

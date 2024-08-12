"""
Add the `SENTRY_DSN` environment variable to the `site/static/sentry.js` file
and add the `site/static/sentry.js` file to the index page (`site/index.html`).
"""
import os
from pathlib import Path

# Index page
index_file = Path("site/index.html")
# Sentry script
sentry_file = Path("site/static/sentry.js")

# Read the contents of the above files
index_data = index_file.read_text("utf-8")
sentry_data = sentry_file.read_text("utf-8")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    # Add the script in the <head> tag
    print("Adding Sentry script in head")
    index_data = index_data.replace(
        "</head>",
        '    <script src="static/sentry.js" async></script></script>\n</head>',
    )
    index_file.write_text(index_data, "utf-8")

    # Add the Sentry DSN in the Sentry script
    print("Adding Sentry DSN in script")
    sentry_data = sentry_data.replace('SENTRY_DSN = ""', f'SENTRY_DSN = "{SENTRY_DSN}"')
    sentry_file.write_text(sentry_data, "utf-8")
else:
    # Warn if the Sentry DSN wasn't provided
    # (in this case, the script shouldn't execute)
    print("::warning title=No Sentry DSN available::Skipping Sentry DSN injection")

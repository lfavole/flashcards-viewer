import os
import re
from pathlib import Path

file = Path("site/index.html")
data = file.read_text("utf-8")

match = re.match(r"^https?://(?:(\w+)@)?\w+\.ingest(?:\.([a-z]+))?\.sentry\.io/\d+", os.environ.get("SENTRY_DSN", ""))
if match:
    script_url = f"https://js{'-' + match[2] if match[2] else ''}.sentry-cdn.com/{match[1]}.min.js"
    data = data.replace(
        "</head>",
        f'    <script src="{script_url}" crossorigin="anonymous" defer></script>\n</head>',
    )
    file.write_text(data, "utf-8")
else:
    print("::warning title=Sentry DSN error::Could not extract the ID from the Sentry DSN")

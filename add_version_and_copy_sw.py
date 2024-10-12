"""
Add the current tag or commit in the `sw.js` file
to prevent old pages being served by the service worker
and copy the file to the website root.
"""
import shutil
import subprocess as sp
from pathlib import Path

# Get the current tag or commit
tag_or_commit = sp.check_output(["git", "describe", "HEAD", "--always"], text=True).rstrip("\n")

# Inject it into sw.js
sw = Path("sw.js")
data = sw.read_text("utf-8")
# Do only one replacement (don't edit comments)
data = data.replace("dev", tag_or_commit, 1)
sw.write_text(data, "utf-8")

# Copy the file
shutil.copy(sw, "site")

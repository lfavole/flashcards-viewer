"""
Add a partial MD5 hash at the end of filenames in the `site/static/` directory
and edit files accordingly.
"""
import hashlib
from pathlib import Path
import shutil


def relative(path: Path):
    """
    Return the path relative to the `site/` directory with forward slashes.
    """
    return str(path.relative_to("site")).replace("\\", "/")


repls = {}

# Hash only the static files
files_to_hash = [*Path("site/static").glob("**/*")]
# Edit all the files
files_to_edit = [*Path("site").glob("**/*")]

for file in files_to_hash:
    # Skip directories
    if file.is_dir():
        continue

    # Get the MD5 hash of the file
    hash = hashlib.md5()
    with file.open("rb") as f:
        while (chunk := f.read(65536)) != b"":
            hash.update(chunk)

    # Copy the file to the new destination
    file2 = file.with_suffix("." + hash.hexdigest()[0:8] + file.suffix)
    print(f"Copying {file} to {file2}")
    shutil.copy(file, file2)

    # Save the replacement for later
    repls[relative(file)] = relative(file2)

for file in files_to_edit:
    # Skip directories
    if file.is_dir():
        continue

    try:
        data = file.read_text("utf-8")
    except UnicodeDecodeError:
        continue

    # Make the replacements
    print(f"Editing {file}")
    for a, b in repls.items():
        data = data.replace(a, b)
    file.write_text(data, "utf-8")

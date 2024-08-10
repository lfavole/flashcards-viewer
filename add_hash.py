import hashlib
from pathlib import Path
import shutil


def relative(path):
    return str(path.relative_to("site")).replace("\\", "/")


repls = {}

files_to_hash = [*Path("site/static").glob("**/*")]
files_to_edit = [*files_to_hash, Path("site/index.html")]

for file in files_to_hash:
    if file.is_dir():
        continue

    hash = hashlib.md5()
    with file.open("rb") as f:
        while (chunk := f.read(65536)) != b"":
            hash.update(chunk)
    file2 = file.with_suffix("." + hash.hexdigest()[0:8] + file.suffix)
    print(f"Copying {file} to {file2}")
    shutil.copy(file, file2)
    repls[relative(file)] = relative(file2)

for file in files_to_edit:
    if file.is_dir():
        continue

    try:
        data = file.read_text("utf-8")
    except UnicodeDecodeError:
        continue
    print(f"Editing {file}")
    for a, b in repls.items():
        data = data.replace(a, b)
    file.write_text(data, "utf-8")

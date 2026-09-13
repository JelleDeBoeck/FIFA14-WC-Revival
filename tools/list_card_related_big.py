from pathlib import Path
import sys

sys.path.insert(0, str(Path("tools").resolve()))
from _chunkzip_reference import read_entries

archive = Path(
    r"backups\worldcup-gamehub-test\patch.big.before_wc_test"
)

data = archive.read_bytes()

terms = (
    "card",
    "player",
    "database",
    "db",
    "ion",
)

for index, offset, size, name in read_entries(data):
    if any(term in name.lower() for term in terms):
        print(
            f"{index:5}  "
            f"offset=0x{offset:08X}  "
            f"size={size:8}  "
            f"{name}"
        )
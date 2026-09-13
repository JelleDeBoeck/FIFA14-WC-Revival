from pathlib import Path
import re


ROOT = Path.cwd()

FILES = [
    ROOT / "extracted" / "fcc_login2" / "fcc_login2.apt",
    ROOT / "extracted" / "fcc_login2" / "fcc_login2.const",
]

OUT = ROOT / "fcc-login2-strings.txt"


def printable_strings(data: bytes, minimum: int = 4):
    pattern = rb"[\x20-\x7e]{" + str(minimum).encode() + rb",}"

    for match in re.finditer(pattern, data):
        yield match.start(), match.group().decode(
            "ascii",
            "replace",
        )


with OUT.open(
    "w",
    encoding="utf-8",
) as f:
    for path in FILES:
        data = path.read_bytes()

        f.write("=" * 80 + "\n")
        f.write(f"FILE: {path}\n")
        f.write(f"SIZE: {len(data)}\n")
        f.write("=" * 80 + "\n\n")

        for offset, text in printable_strings(data):
            f.write(
                f"0x{offset:08X}  {text}\n"
            )

        f.write("\n\n")


print(f"KLAAR: {OUT}")
from pathlib import Path

dll = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

needles = [
    b"GetPlayerCardInfo",
    b"GetUserCardInfo",
    b"TEAM_ASSET_ID",
    b"CONFEDERATION_ASSET_ID",
    b"NATIONALITY_ASSET_ID",
    b"CARD_TOTW",
    b"ION_Card",
]

data = dll.read_bytes()

for needle in needles:
    print(f"\n=== {needle.decode()} ===")
    start = 0
    found = False

    while True:
        pos = data.find(needle, start)
        if pos < 0:
            break

        found = True
        print(f"file offset: 0x{pos:08X}")

        before = max(0, pos - 64)
        after = min(len(data), pos + len(needle) + 64)
        chunk = data[before:after]

        printable = "".join(
            chr(b) if 32 <= b < 127 else "."
            for b in chunk
        )
        print(printable)

        start = pos + 1

    if not found:
        print("NOT FOUND")
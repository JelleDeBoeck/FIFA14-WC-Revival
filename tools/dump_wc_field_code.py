from pathlib import Path
import struct

dll = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")
data = dll.read_bytes()

# PE mapping voor deze DLL:
TEXT_RVA = 0x1000
TEXT_RAW = 0x400

targets = {
    "NATIONALITY_ASSET_ID": 0x24C57,
    "CONFEDERATION_ASSET_ID": 0x24CFA,
    "TEAM_ASSET_ID": 0x24D11,
}

def rva_to_file(rva):
    return TEXT_RAW + (rva - TEXT_RVA)

for name, rva in targets.items():
    off = rva_to_file(rva)

    # 48 bytes ervoor + 96 erna
    start = off - 48
    end = off + 96
    chunk = data[start:end]

    print()
    print("=" * 70)
    print(name)
    print(f"target RVA : 0x{rva:08X}")
    print(f"file off   : 0x{off:08X}")
    print(f"range RVA  : 0x{rva - 48:08X} - 0x{rva + 96:08X}")
    print("=" * 70)

    for i in range(0, len(chunk), 16):
        row = chunk[i:i+16]
        row_rva = (rva - 48) + i
        print(
            f"{row_rva:08X}  "
            + " ".join(f"{b:02X}" for b in row)
        )
from pathlib import Path
import struct

DLL = Path(r"C:\Program Files\EA Games\FIFA 14\Game\CardsDLLzf.dll")

TARGETS = [
    b"GetPlayerCardInfo",
    b"GetUserCardInfo",
    b"TEAM_ASSET_ID",
    b"CONFEDERATION_ASSET_ID",
    b"NATIONALITY_ASSET_ID",
    b"CARD_TOTW",
    b"ION_Card",
]

data = DLL.read_bytes()


def u16(off):
    return struct.unpack_from("<H", data, off)[0]


def u32(off):
    return struct.unpack_from("<I", data, off)[0]


# ----- Parse PE headers -----

if data[:2] != b"MZ":
    raise RuntimeError("Not an MZ executable")

pe_off = u32(0x3C)

if data[pe_off:pe_off + 4] != b"PE\0\0":
    raise RuntimeError("Not a PE file")

coff = pe_off + 4

number_of_sections = u16(coff + 2)
size_of_optional_header = u16(coff + 16)

optional = coff + 20
magic = u16(optional)

if magic == 0x10B:
    image_base = u32(optional + 28)
elif magic == 0x20B:
    image_base = struct.unpack_from("<Q", data, optional + 24)[0]
else:
    raise RuntimeError(f"Unknown PE optional-header magic: 0x{magic:X}")

section_table = optional + size_of_optional_header

sections = []

for i in range(number_of_sections):
    off = section_table + i * 40

    name = data[off:off + 8].split(b"\0", 1)[0].decode("ascii", errors="replace")
    virtual_size = u32(off + 8)
    virtual_address = u32(off + 12)
    raw_size = u32(off + 16)
    raw_pointer = u32(off + 20)

    sections.append({
        "name": name,
        "virtual_size": virtual_size,
        "rva": virtual_address,
        "raw_size": raw_size,
        "raw": raw_pointer,
    })


def file_to_rva(file_off):
    for s in sections:
        start = s["raw"]
        end = start + s["raw_size"]

        if start <= file_off < end:
            return s["rva"] + (file_off - start)

    return None


def section_for_file(file_off):
    for s in sections:
        if s["raw"] <= file_off < s["raw"] + s["raw_size"]:
            return s["name"]

    return "?"


print(f"DLL: {DLL}")
print(f"ImageBase: 0x{image_base:08X}")
print()

print("Sections:")
for s in sections:
    print(
        f"  {s['name']:8} "
        f"RVA=0x{s['rva']:08X} "
        f"RAW=0x{s['raw']:08X} "
        f"RAWSIZE=0x{s['raw_size']:08X}"
    )


# ----- Find strings + native xrefs -----

for needle in TARGETS:
    print()
    print("=" * 70)
    print(needle.decode("ascii"))
    print("=" * 70)

    string_positions = []
    start = 0

    while True:
        pos = data.find(needle, start)

        if pos < 0:
            break

        string_positions.append(pos)
        start = pos + 1

    if not string_positions:
        print("STRING NOT FOUND")
        continue

    for string_off in string_positions:
        string_rva = file_to_rva(string_off)

        if string_rva is None:
            print(f"String file offset 0x{string_off:08X}: no RVA")
            continue

        string_va = image_base + string_rva

        print(
            f"\nString:"
            f"\n  file offset = 0x{string_off:08X}"
            f"\n  section     = {section_for_file(string_off)}"
            f"\n  RVA         = 0x{string_rva:08X}"
            f"\n  VA          = 0x{string_va:08X}"
        )

        # x86 DLL: native tables and PUSH/MOV immediates commonly contain
        # the preferred-image absolute VA in little endian.
        patterns = [
            ("VA32", struct.pack("<I", string_va & 0xFFFFFFFF)),
            ("RVA32", struct.pack("<I", string_rva & 0xFFFFFFFF)),
        ]

        seen = set()

        for kind, pattern in patterns:
            xref_start = 0

            while True:
                xref = data.find(pattern, xref_start)

                if xref < 0:
                    break

                xref_start = xref + 1

                if xref == string_off:
                    continue

                key = (kind, xref)

                if key in seen:
                    continue

                seen.add(key)

                xref_rva = file_to_rva(xref)

                before = max(0, xref - 24)
                after = min(len(data), xref + 28)
                chunk = data[before:after]

                print(
                    f"\n  XREF {kind}:"
                    f"\n    file    = 0x{xref:08X}"
                    f"\n    section = {section_for_file(xref)}"
                    f"\n    RVA     = "
                    + (
                        f"0x{xref_rva:08X}"
                        if xref_rva is not None
                        else "?"
                    )
                )

                print("    bytes   =", chunk.hex(" "))
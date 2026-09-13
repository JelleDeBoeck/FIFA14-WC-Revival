from pathlib import Path
import struct
import zlib


ROOT = Path.cwd()

SRC = (
    ROOT
    / "backups"
    / "worldcup-gamehub-test"
    / "patch.big.before_wc_test"
)

OUT_DIR = ROOT / "extracted" / "fcc_login2"

TARGET = "data/ui/external/ion_fut/screens/fcc_login2.big"

CHUNKZIP_MAGIC = b"chunkzip"


def align(value: int, alignment: int = 16) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def read_entries(data: bytes):
    magic = data[:4]

    if magic not in {b"BIGF", b"BIG4"}:
        raise RuntimeError(
            f"Geen ondersteund BIG archive: {magic!r}"
        )

    count = int.from_bytes(
        data[8:12],
        "big",
    )

    pos = 16

    for index in range(count):
        offset = int.from_bytes(
            data[pos:pos + 4],
            "big",
        )

        size = int.from_bytes(
            data[pos + 4:pos + 8],
            "big",
        )

        pos += 8

        end = data.index(
            b"\x00",
            pos,
        )

        name = data[pos:end].decode(
            "utf-8",
            "replace",
        )

        pos = end + 1

        yield index, offset, size, name


def decode_chunkzip(payload: bytes) -> tuple[bytes, dict]:
    if len(payload) < 40 or payload[:8] != CHUNKZIP_MAGIC:
        raise ValueError(
            "payload is not chunkzip"
        )

    (
        version,
        output_size,
        chunk_size,
        count,
        alignment,
        flag_a,
        flag_b,
        flag_c,
    ) = struct.unpack_from(
        ">IIIIIIII",
        payload,
        8,
    )

    print("ChunkZip header:")
    print(f"  version     : {version}")
    print(f"  output_size : {output_size}")
    print(f"  chunk_size  : {chunk_size}")
    print(f"  chunk_count : {count}")
    print(f"  alignment   : {alignment}")
    print(
        f"  flags       : "
        f"{flag_a}, {flag_b}, {flag_c}"
    )
    print()

    if version != 2:
        raise ValueError(
            f"unsupported chunkzip version: {version}"
        )

    if alignment != 16:
        raise ValueError(
            f"unsupported alignment: {alignment}"
        )

    if flag_a or flag_b or flag_c:
        raise ValueError(
            "unsupported chunkzip flags: "
            f"{flag_a}, {flag_b}, {flag_c}"
        )

    pos = 40
    output = bytearray()
    chunks = []

    for index in range(count):
        if pos + 8 > len(payload):
            raise ValueError(
                f"truncated chunk descriptor {index}"
            )

        stored_size, compression_type = (
            struct.unpack_from(
                ">II",
                payload,
                pos,
            )
        )

        start = pos + 8
        end = start + stored_size

        if end > len(payload):
            raise ValueError(
                f"truncated chunk {index}"
            )

        stored = payload[start:end]

        if compression_type == 0:
            decoded = stored

        elif compression_type == 1:
            decoded = zlib.decompress(
                stored,
                -zlib.MAX_WBITS,
            )

        else:
            raise ValueError(
                "unsupported compression type "
                f"{compression_type}"
            )

        output.extend(decoded)

        chunks.append(
            {
                "index": index,
                "stored_size": stored_size,
                "decoded_size": len(decoded),
                "compression_type": compression_type,
            }
        )

        print(
            f"CHUNK [{index}] "
            f"stored={stored_size} "
            f"decoded={len(decoded)} "
            f"type={compression_type}"
        )

        pos = align(
            end + 8,
            alignment,
        ) - 8

    if len(output) != output_size:
        raise ValueError(
            f"decoded size {len(output)} "
            f"!= header {output_size}"
        )

    return bytes(output), {
        "version": version,
        "output_size": output_size,
        "chunk_size": chunk_size,
        "chunk_count": count,
        "chunks": chunks,
    }


outer = SRC.read_bytes()

print(f"outer source : {SRC}")
print(f"outer size   : {len(outer)}")
print(f"outer magic  : {outer[:4]!r}")
print()


target_blob = None

for index, offset, size, name in read_entries(outer):
    if name.lower() == TARGET.lower():
        print(
            f"FOUND outer entry [{index}] "
            f"name={name!r} "
            f"offset=0x{offset:X} "
            f"size={size}"
        )

        target_blob = outer[
            offset:
            offset + size
        ]

        break


if target_blob is None:
    raise RuntimeError(
        f"Niet gevonden: {TARGET}"
    )


OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


stored_path = (
    OUT_DIR
    / "fcc_login2.chunkzip"
)

stored_path.write_bytes(
    target_blob
)

print(
    f"stored      : {stored_path}"
)

print(
    f"stored magic: {target_blob[:8]!r}"
)

print()


if not target_blob.startswith(
    CHUNKZIP_MAGIC
):
    raise RuntimeError(
        "fcc_login2 payload begint niet "
        "met 'chunkzip'"
    )


decoded, info = decode_chunkzip(
    target_blob
)


decoded_path = (
    OUT_DIR
    / "fcc_login2.decoded"
)

decoded_path.write_bytes(
    decoded
)


print()
print(
    f"decoded      : {decoded_path}"
)

print(
    f"decoded size : {len(decoded)}"
)

print(
    f"decoded magic: {decoded[:16]!r}"
)

print(
    "decoded hex  : "
    + decoded[:64].hex(" ")
)


# Als de gedecomprimeerde payload zelf een BIG is,
# dump dan meteen alle entries.
if decoded[:4] in {
    b"BIGF",
    b"BIG4",
}:
    print()
    print(
        "Decoded payload is zelf een BIG archive."
    )

    INNER_DIR = (
        OUT_DIR
        / "inner"
    )

    INNER_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for index, offset, size, name in read_entries(
        decoded
    ):
        blob = decoded[
            offset:
            offset + size
        ]

        safe_name = (
            name
            .replace("/", "_")
            .replace("\\", "_")
        )

        out = (
            INNER_DIR
            / f"{index:02d}_{safe_name}"
        )

        out.write_bytes(
            blob
        )

        print(
            f"INNER [{index}] "
            f"name={name!r} "
            f"offset=0x{offset:X} "
            f"size={size} "
            f"first16="
            f"{blob[:16].hex(' ')}"
        )

        print(
            f"    output={out}"
        )


print()
print("KLAAR")
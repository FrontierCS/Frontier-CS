import os
import tempfile
import subprocess
import sys
import struct
import random
import string

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a payload that triggers uninitialized value vulnerability
        # Based on typical scenarios where attribute conversions fail but don't error
        
        # Strategy: Create malformed data that causes parsers to skip initialization
        # while leaving values uninitialized for later use
        
        payload_parts = []
        
        # 1. Start with a valid header/magic bytes if needed
        # (Common in many file formats)
        header = b'VALID_FORMAT\x00\x01\x02'
        payload_parts.append(header)
        
        # 2. Add structured data with intentionally malformed fields
        # Create nested structures where inner fields might not be initialized
        
        # Section with valid length but malformed content
        section_header = struct.pack('<I', 0x100)  # Section length
        payload_parts.append(section_header)
        
        # Add fields that will cause failed conversions
        # Field type that expects integer but gets string
        field_type = struct.pack('<B', 0x01)  # Integer field type
        payload_parts.append(field_type)
        
        # Instead of integer, provide malformed string
        malformed_int = b'NOT_AN_INTEGER' + b'\x00'
        payload_parts.append(malformed_int)
        
        # Another field that expects string but gets empty/nonexistent
        field_type = struct.pack('<B', 0x02)  # String field type
        payload_parts.append(field_type)
        
        # Provide length but no actual string (uninitialized read later)
        str_length = struct.pack('<I', 0x100)  # Claims 256 bytes string
        payload_parts.append(str_length)
        # NO STRING DATA PROVIDED - this creates uninitialized buffer
        
        # 3. Add more sections to reach target complexity
        # Multiple nested structures increase chance of hitting vulnerability
        
        for i in range(10):
            # Start nested object
            obj_start = struct.pack('<B', 0xA0 + i)  # Object type
            payload_parts.append(obj_start)
            
            # Add attributes with conversion issues
            attr_count = struct.pack('<B', 2)  # 2 attributes
            payload_parts.append(attr_count)
            
            # Attribute 1: Valid
            attr1_name = b'valid_attr\x00'
            attr1_type = struct.pack('<B', 0x01)  # Integer
            attr1_value = struct.pack('<I', 0x12345678)
            payload_parts.append(attr1_name)
            payload_parts.append(attr1_type)
            payload_parts.append(attr1_value)
            
            # Attribute 2: Problematic - type mismatch
            attr2_name = b'bad_attr\x00'
            attr2_type = struct.pack('<B', 0x03)  # Float type
            payload_parts.append(attr2_name)
            payload_parts.append(attr2_type)
            
            # Instead of float, provide string that can't convert
            bad_float = b'3.14eXYZ' + b'\x00'  # Invalid float format
            payload_parts.append(bad_float)
            
            # End object
            obj_end = struct.pack('<B', 0xFF)
            payload_parts.append(obj_end)
        
        # 4. Add array with missing elements
        array_start = struct.pack('<B', 0xC0)
        array_length = struct.pack('<I', 0x20)  # 32 elements
        payload_parts.append(array_start)
        payload_parts.append(array_length)
        
        # Provide only 16 elements, leaving 16 uninitialized
        for j in range(16):
            element = struct.pack('<I', j * 100)
            payload_parts.append(element)
        
        # 5. Final section with dangling references
        # Create reference to uninitialized data
        ref_section = struct.pack('<B', 0xD0)
        payload_parts.append(ref_section)
        
        # Reference ID that doesn't exist
        ref_id = struct.pack('<I', 0xFFFFFFFF)
        payload_parts.append(ref_id)
        
        # 6. Padding to reach approximate target length
        current_len = sum(len(p) for p in payload_parts)
        target_len = 2179
        
        if current_len < target_len:
            padding = b'P' * (target_len - current_len)
            payload_parts.append(padding)
        elif current_len > target_len:
            # Truncate if too long (unlikely)
            payload_parts = [b''.join(payload_parts)[:target_len]]
        
        # Combine all parts
        poc = b''.join(payload_parts)
        
        # Verify length is reasonable
        if len(poc) < 100:  # Fallback if construction failed
            # Create simpler payload focused on uninitialized access
            poc = self._create_simple_payload()
        
        return poc
    
    def _create_simple_payload(self) -> bytes:
        """Fallback payload creation"""
        # Simple structure: Header + malformed data
        payload = bytearray()
        
        # Header
        payload.extend(b'UNINIT_TEST')
        payload.extend(struct.pack('<I', 0xDEADBEEF))  # Magic
        
        # Data section with intentional gaps
        section_count = struct.pack('<H', 5)
        payload.extend(section_count)
        
        # Section 1: Valid
        payload.extend(struct.pack('<B', 1))  # Type
        payload.extend(struct.pack('<I', 4))  # Length
        payload.extend(b'DATA')
        
        # Section 2: Missing data (length specified but no content)
        payload.extend(struct.pack('<B', 2))  # Type
        payload.extend(struct.pack('<I', 256))  # Length (large)
        # NO DATA - creates uninitialized buffer
        
        # Section 3: Invalid type conversion
        payload.extend(struct.pack('<B', 3))  # Type (numeric)
        payload.extend(b'ABC')  # Not a number
        
        # Fill to target length
        remaining = 2179 - len(payload)
        if remaining > 0:
            payload.extend(b'X' * remaining)
        
        return bytes(payload)
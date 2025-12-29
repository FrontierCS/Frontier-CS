import os
import re
import tarfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        def read_text_from_tar(tar, member):
            f = tar.extractfile(member)
            if not f:
                return ""
            try:
                return f.read().decode('latin-1', errors='ignore')
            except Exception:
                return ""

        def detect_format_from_code(texts):
            has_newline_split = False
            has_nul_split = False
            has_lenpair = False

            for txt in texts:
                low = txt.lower()

                # Detect newline-based split
                if re.search(r'memchr\s*\([^,]+,\s*\'\\n\'\s*,', txt):
                    has_newline_split = True
                if re.search(r'\.find\(\s*\'\\n\'\s*\)|\.find\(\s*\"\\n\"\s*\)', txt):
                    has_newline_split = True
                if 'std::getline' in txt:
                    has_newline_split = True

                # Detect NUL-based split
                if re.search(r"memchr\s*\([^,]+,\s*0\s*,", txt) or re.search(r"memchr\s*\([^,]+,\s*'\\0'\s*,", txt):
                    has_nul_split = True

                # Detect 32-bit length-prefixed (pattern, subject)
                # Heuristics: looking for reading 4 bytes at a time and incrementing pointer
                if re.search(r'\*\s*\(\s*(?:const\s*)?(?:u?int32_t|size_t)\s*\*\)\s*\(?\s*(?:data|Data)', txt):
                    if re.search(r'(?:data|Data)\s*\+=\s*4', txt) and re.search(r'(?:size|Size)\s*<\s*8', txt):
                        has_lenpair = True
                if re.search(r'(?:size|Size)\s*>=\s*8', txt) and ('Data +=' in txt or 'data +=' in txt):
                    has_lenpair = True
                if re.search(r'(?:read|consume).*4.*bytes', low):
                    has_lenpair = True

            # Prioritize explicit length-pair detection for this task
            if has_lenpair:
                return 'lenpair'
            if has_newline_split:
                return 'newline'
            if has_nul_split:
                return 'nul'
            # Default guess: lenpair (common for regex fuzzers; aligns with 8-byte ground-truth PoC)
            return 'lenpair'

        texts = []
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if name_lower.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx', '.txt')):
                        content = read_text_from_tar(tar, m)
                        if content:
                            texts.append(content)
        except Exception:
            # If tar can't be read, fallback to a robust default
            return struct.pack('<II', 0, 0)

        fmt = detect_format_from_code(texts)

        if fmt == 'lenpair':
            # Pattern length = 0, Subject length = 0
            return struct.pack('<II', 0, 0)
        elif fmt == 'newline':
            # Pattern: "a" (no capturing parentheses), Subject: "a"
            return b"a\na"
        elif fmt == 'nul':
            # Pattern: "a", Subject: "a" separated by NUL
            return b"a\x00a"
        else:
            # Fallback to lenpair zero lengths
            return struct.pack('<II', 0, 0)
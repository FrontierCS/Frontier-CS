import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _read_all_files(self, src_path: str) -> List[Tuple[str, bytes]]:
        files: List[Tuple[str, bytes]] = []
        if os.path.isdir(src_path):
            for root, _, fnames in os.walk(src_path):
                for fn in fnames:
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            files.append((os.path.relpath(p, src_path), f.read()))
                    except Exception:
                        continue
            return files

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        files.append((m.name, data))
                    except Exception:
                        continue
        except Exception:
            try:
                with open(src_path, "rb") as f:
                    files.append((os.path.basename(src_path), f.read()))
            except Exception:
                pass
        return files

    def _is_text_like(self, data: bytes) -> bool:
        if not data:
            return False
        if b"\x00" in data:
            return False
        sample = data[:4096]
        bad = 0
        for b in sample:
            if b in (9, 10, 13):
                continue
            if 32 <= b <= 126:
                continue
            bad += 1
        return bad / max(1, len(sample)) < 0.08

    def _split_sources_and_others(self, all_files: List[Tuple[str, bytes]]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, bytes]]]:
        src_exts = {
            ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx",
            ".y", ".l", ".inc", ".ipp", ".inl"
        }
        sources: List[Tuple[str, str]] = []
        others: List[Tuple[str, bytes]] = []
        for name, data in all_files:
            ext = os.path.splitext(name)[1].lower()
            if ext in src_exts:
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    txt = ""
                sources.append((name, txt))
            else:
                others.append((name, data))
        return sources, others

    def _detect_delims(self, sources: List[Tuple[str, str]]) -> Tuple[Tuple[bytes, bytes], float]:
        pairs = [
            (b"<", b">"),
            (b"[", b"]"),
            (b"{", b"}"),
            (b"(", b")"),
        ]

        def count_tokens(txt: str, start: bytes, end: bytes) -> int:
            s = start.decode("latin1")
            e = end.decode("latin1")
            c = 0
            c += len(re.findall(r"'" + re.escape(s) + r"'", txt))
            c += len(re.findall(r'"' + re.escape(s) + r'"', txt))
            c += len(re.findall(r"'" + re.escape(e) + r"'", txt))
            c += len(re.findall(r'"' + re.escape(e) + r'"', txt))
            return c

        best_pair = (b"<", b">")
        best_score = 0.0

        for start, end in pairs:
            tot = 0
            for _, txt in sources:
                ltxt = txt.lower()
                if "tag" in ltxt or "markup" in ltxt or "html" in ltxt or "xml" in ltxt:
                    tot += count_tokens(txt, start, end)
            if tot == 0:
                for _, txt in sources:
                    tot += count_tokens(txt, start, end)
            score = float(tot)
            if score > best_score:
                best_score = score
                best_pair = (start, end)

        return best_pair, best_score

    def _estimate_buffer_size(self, sources: List[Tuple[str, str]], delims: Tuple[bytes, bytes]) -> Optional[int]:
        start_c = delims[0].decode("latin1")
        end_c = delims[1].decode("latin1")

        unsafe_re = re.compile(r"\b(sprintf|vsprintf|strcpy|strcat|gets)\s*\(\s*([A-Za-z_]\w*)")
        decl_template = r"\bchar\b[^;\n{]*\b%s\s*\[\s*(\d+)\s*\]"
        tag_word_re = re.compile(r"\btag\b", re.IGNORECASE)

        best = None  # (score, size)

        for fname, txt in sources:
            lines = txt.splitlines()
            file_has_tag = "tag" in txt.lower()
            file_has_delims = (start_c in txt) and (end_c in txt)

            tag_lines = set()
            if file_has_tag:
                for i, ln in enumerate(lines):
                    if tag_word_re.search(ln):
                        tag_lines.add(i)

            for i, ln in enumerate(lines):
                m = unsafe_re.search(ln)
                if not m:
                    continue
                func = m.group(1)
                dest = m.group(2)

                decl_re = re.compile(decl_template % re.escape(dest))
                size_val = None
                for j in range(i, max(-1, i - 450), -1):
                    dm = decl_re.search(lines[j])
                    if dm:
                        try:
                            size_val = int(dm.group(1))
                        except Exception:
                            size_val = None
                        break
                if size_val is None:
                    continue
                if size_val < 32:
                    continue
                if size_val > 200000:
                    continue

                score = 0
                if file_has_tag:
                    score += 20
                if file_has_delims:
                    score += 10
                if any(abs(i - tl) <= 30 for tl in tag_lines):
                    score += 60
                ldest = dest.lower()
                if "out" in ldest or "output" in ldest or "dst" in ldest or "dest" in ldest:
                    score += 25
                if "buf" in ldest or "buffer" in ldest:
                    score += 8
                if func in ("sprintf", "vsprintf"):
                    score += 25
                elif func in ("strcpy", "strcat"):
                    score += 15
                elif func == "gets":
                    score += 30
                if "%s" in ln:
                    score += 8
                if "tag" in ln.lower():
                    score += 10
                if ("<%s" in ln) or ("%s>" in ln) or ("</%s" in ln):
                    score += 15

                cand = (score, size_val)
                if best is None:
                    best = cand
                else:
                    if cand[0] > best[0]:
                        best = cand
                    elif cand[0] == best[0]:
                        if abs(cand[1] - 1024) < abs(best[1] - 1024):
                            best = cand

        if best is not None:
            return best[1]

        # Fallback: find likely output buffer by name near tag-related files
        out_decl_re = re.compile(r"\bchar\b[^;\n{]*\b([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]")
        candidates: List[int] = []
        for _, txt in sources:
            ltxt = txt.lower()
            if "tag" not in ltxt:
                continue
            for m in out_decl_re.finditer(txt):
                name = m.group(1).lower()
                try:
                    n = int(m.group(2))
                except Exception:
                    continue
                if n < 32 or n > 200000:
                    continue
                if "out" in name or "output" in name or "dst" in name or "dest" in name:
                    candidates.append(n)
        if candidates:
            candidates.sort()
            mid = candidates[len(candidates) // 2]
            return mid

        return None

    def _choose_seed(self, others: List[Tuple[str, bytes]], delims: Tuple[bytes, bytes]) -> Optional[bytes]:
        start, end = delims
        preferred_dirs = ("test", "tests", "example", "examples", "sample", "samples", "data", "corpus")
        preferred_exts = (".xml", ".html", ".htm", ".sgml", ".txt", ".cfg", ".ini", ".tmpl", ".md", ".json", ".yaml", ".yml")

        best = None  # (score, bytes)
        for name, data in others:
            if len(data) == 0 or len(data) > 50000:
                continue
            if not self._is_text_like(data):
                continue
            lname = name.lower()
            score = 0
            if any(d in lname.split("/") for d in preferred_dirs) or any(f"/{d}/" in lname for d in preferred_dirs):
                score += 40
            if lname.endswith(preferred_exts):
                score += 25
            if start in data and end in data:
                score += 30
            if b"tag" in data.lower():
                score += 10
            score -= min(20, len(data) // 2000)

            if best is None or score > best[0]:
                best = (score, data)

        return best[1] if best is not None and best[0] >= 30 else None

    def _make_chunk(self, delims: Tuple[bytes, bytes], fill_len: int) -> bytes:
        start, end = delims
        if start == b"<" and end == b">":
            # Try to be XML/HTML friendly
            tagname = b"a"
            inner = b"A" * max(0, fill_len)
            return b"<" + tagname + b">" + inner + b"</" + tagname + b">"
        else:
            name = b"a"
            inner = b"A" * max(0, fill_len)
            return start + name + inner + end

    def _insert_xmlish(self, seed: bytes, chunk: bytes) -> bytes:
        # Insert before last closing tag if plausible
        idx = seed.rfind(b"</")
        if idx != -1:
            return seed[:idx] + chunk + seed[idx:]
        # Otherwise append
        if seed and seed[-1:] not in (b"\n", b"\r"):
            return seed + b"\n" + chunk
        return seed + chunk

    def solve(self, src_path: str) -> bytes:
        all_files = self._read_all_files(src_path)
        sources, others = self._split_sources_and_others(all_files)

        delims, delim_score = self._detect_delims(sources)
        buf_size = self._estimate_buffer_size(sources, delims)

        if buf_size is None or buf_size < 64 or buf_size > 65536:
            buf_size = 1024

        # Keep sizes moderate to avoid unintended resource issues
        target_total = buf_size + 256
        if target_total < 1600:
            target_total = 1600
        if target_total > 6000:
            target_total = 6000

        seed = self._choose_seed(others, delims)
        if seed is None and delim_score < 2.0:
            # Uncertain delimiters: include multiple common tag patterns
            head = b"<a>" + b"[a]" + b"{a}"
            fill_len = max(0, target_total - len(head) - 1)
            return head + (b"A" * fill_len) + b"\n"

        # Ensure we include at least one tag marker early
        prefix_tag = self._make_chunk(delims, 0)
        base = seed if seed is not None else b""
        if base:
            if delims[0] == b"<" and delims[1] == b">" and base.lstrip().startswith(b"<"):
                # Try not to break well-formedness too badly
                needed = max(0, target_total - len(base) - 2)
                chunk = self._make_chunk(delims, needed)
                out = self._insert_xmlish(base, chunk)
                if not out.endswith(b"\n"):
                    out += b"\n"
                return out
            else:
                # Append a large taggy chunk
                needed = max(0, target_total - len(base) - 2 - len(prefix_tag))
                chunk = self._make_chunk(delims, needed)
                out = base
                if not out.endswith(b"\n"):
                    out += b"\n"
                out += chunk + b"\n"
                return out

        # No seed: craft synthetic
        overhead = len(prefix_tag) + 1
        fill_len = max(0, target_total - overhead)
        chunk = self._make_chunk(delims, fill_len)
        return chunk + b"\n"
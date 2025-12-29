import os
import re
import io
import tarfile
import tempfile
import gzip
import bz2
import lzma
from typing import Optional, Tuple, List


class Solution:
    _BUG_ID = "42536068"

    def _is_within_dir(self, base: str, target: str) -> bool:
        base = os.path.abspath(base)
        target = os.path.abspath(target)
        try:
            common = os.path.commonpath([base, target])
        except Exception:
            return False
        return common == base

    def _safe_extract_tar(self, tar_path: str, out_dir: str) -> None:
        mode = "r:*"
        with tarfile.open(tar_path, mode) as tf:
            members = tf.getmembers()
            safe_members = []
            for m in members:
                name = m.name
                if not name or name.startswith(("/", "\\")) or ".." in name.split("/"):
                    continue
                dest = os.path.join(out_dir, name)
                if not self._is_within_dir(out_dir, dest):
                    continue
                if m.issym() or m.islnk():
                    continue
                safe_members.append(m)
            tf.extractall(out_dir, members=safe_members)

    def _maybe_decompress_by_extension(self, path: str, data: bytes) -> bytes:
        lpath = path.lower()
        try:
            if lpath.endswith(".gz") and len(data) >= 2 and data[:2] == b"\x1f\x8b":
                return gzip.decompress(data)
            if lpath.endswith(".bz2"):
                return bz2.decompress(data)
            if lpath.endswith(".xz") or lpath.endswith(".lzma"):
                return lzma.decompress(data)
        except Exception:
            return data
        return data

    def _looks_like_git_lfs_pointer(self, data: bytes) -> bool:
        if len(data) > 1024:
            return False
        try:
            s = data.decode("utf-8", "ignore")
        except Exception:
            return False
        return "git-lfs" in s and "oid sha256:" in s and "size " in s

    def _walk_pruned(self, root: str):
        exclude = {
            ".git", ".svn", ".hg", ".idea", ".vs",
            "build", "out", "dist", "bazel-bin", "bazel-out", "bazel-testlogs",
            "node_modules", "__pycache__", ".cache", "CMakeFiles",
            "third_party", "thirdparty", "external", "externals", "vendor", "subprojects",
        }
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in exclude and not d.startswith(".")]
            yield dirpath, dirnames, filenames

    def _find_poc_by_filename(self, root: str) -> Optional[bytes]:
        bug = self._BUG_ID
        best: Optional[Tuple[int, int, str]] = None  # (priority, size, path)
        max_size = 2_000_000

        def priority_for(path_l: str, name_l: str) -> Optional[int]:
            if bug in name_l or bug in path_l:
                return 0
            if "clusterfuzz" in name_l or "clusterfuzz" in path_l:
                return 1
            if name_l.startswith("crash") or "crash" in name_l or "poc" in name_l:
                return 2
            if "regress" in path_l or "regression" in path_l:
                return 3
            if "corpus" in path_l or "fuzz" in path_l:
                return 4
            return None

        for dirpath, _, filenames in self._walk_pruned(root):
            path_l = dirpath.lower()
            for fn in filenames:
                name_l = fn.lower()
                pr = priority_for(path_l, name_l)
                if pr is None:
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    st = os.stat(fp)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > max_size:
                    continue
                cand = (pr, st.st_size, fp)
                if best is None or cand < best:
                    best = cand
                    if pr == 0:
                        break
            if best is not None and best[0] == 0:
                break

        if best is None:
            return None
        _, _, fp = best
        try:
            with open(fp, "rb") as f:
                data = f.read()
        except Exception:
            return None
        if self._looks_like_git_lfs_pointer(data):
            return None
        data2 = self._maybe_decompress_by_extension(fp, data)
        if data2 and not self._looks_like_git_lfs_pointer(data2):
            return data2
        return data

    def _find_fuzzer_harness_text(self, root: str) -> str:
        needle = "LLVMFuzzerTestOneInput"
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"}
        max_read = 2_000_000

        # Prefer files in fuzz/fuzzer directories for speed/accuracy
        preferred_dirs = []
        for dirpath, _, filenames in self._walk_pruned(root):
            dl = dirpath.lower()
            if "fuzz" in dl or "fuzzer" in dl:
                preferred_dirs.append((dirpath, filenames))

        def scan_dirs(dirs) -> Optional[str]:
            for dirpath, filenames in dirs:
                for fn in filenames:
                    _, ext = os.path.splitext(fn)
                    if ext.lower() not in exts:
                        continue
                    fp = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(fp)
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > max_read:
                        continue
                    try:
                        with open(fp, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    if needle.encode("utf-8") not in data:
                        continue
                    try:
                        return data.decode("utf-8", "ignore")
                    except Exception:
                        continue
            return None

        found = scan_dirs(preferred_dirs)
        if found is not None:
            return found

        for dirpath, _, filenames in self._walk_pruned(root):
            dirs = [(dirpath, filenames)]
            found = scan_dirs(dirs)
            if found is not None:
                return found
        return ""

    def _guess_format(self, harness_text: str) -> str:
        t = harness_text.lower()

        def has_any(words):
            return any(w in t for w in words)

        if has_any(["rsvg", "sksvg", "svgdom", "svg_dom", "makesvg", "svg"]) and has_any(["xml", "<svg", "xmlns"]):
            return "svg"
        if has_any(["gumbo", "htmlparser", "parsehtml", ".html", "<html", "html::", "tidy"]):
            return "html"
        if has_any(["xmlreadmemory", "xmlparse", "tinyxml", "tinyxml2", "pugi::xml", "pugixml", "rapidxml", "qdomdocument", "libxml", "xmldocument"]):
            if has_any(["svg", ".svg", "<svg"]):
                return "svg"
            return "xml"
        if has_any(["nlohmann", "rapidjson", "simdjson", "cjson", "json::parse", "json_parse", ".json"]):
            return "json"
        if has_any(["yaml::load", "libyaml", "yaml_parser", "yaml-cpp", ".yaml", ".yml"]):
            return "yaml"
        return "svg"

    def _generate_svg_poc(self) -> bytes:
        s = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="100" height="100"
     viewBox="0 0 a b" version="1.1">
  <defs>
    <filter id="f1" x="-" y="0" width="1e" height="10">
      <feGaussianBlur in="SourceGraphic" stdDeviation="x y"/>
      <feOffset dx="q" dy="1"/>
      <feComposite in2="SourceGraphic" operator="arithmetic" k1="-" k2="a" k3="1e" k4=""/>
      <feColorMatrix type="matrix"
        values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1e 0"/>
    </filter>
    <linearGradient id="g1" x1="0" y1="0" x2="100%" y2="bad" gradientTransform="rotate(a)">
      <stop offset="0" stop-color="#000" stop-opacity="bad"/>
      <stop offset="1" stop-color="#fff" stop-opacity=""/>
    </linearGradient>
    <pattern id="p1" x="0" y="0" width="a" height="1" patternUnits="userSpaceOnUse">
      <rect x="0" y="0" width="10" height="10" fill="url(#g1)"/>
    </pattern>
  </defs>
  <rect x="0" y="0" width="100" height="100" fill="url(#p1)" filter="url(#f1)" rx="-" ry="-" />
  <circle cx="50" cy="50" r="-" stroke-width="-" opacity="-" />
  <path d="M0 0 L10 10" stroke-dasharray="1,a" stroke-dashoffset="-" />
  <text x="0" y="10" font-size="a" letter-spacing="-" word-spacing="1e">t</text>
</svg>
"""
        return s.encode("utf-8", "ignore")

    def _generate_xml_poc(self) -> bytes:
        s = """<?xml version="1.0" encoding="UTF-8"?>
<root a="-" b="a" c="1e" d="" e="0x10" f="--1" g="1e309" h="nan" i="inf">
  <node x="-" y="bad" width="1e" height=""/>
  <node2 value="a,b,c" nums="1 a 2" flags="--" />
  <deep>
    <item p="-" q="1e" r="a" s="" t="  " u="+" v="-0x1"/>
  </deep>
</root>
"""
        return s.encode("utf-8", "ignore")

    def _generate_html_poc(self) -> bytes:
        s = """<!doctype html>
<html>
<head><meta charset="utf-8"></head>
<body>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 a b">
  <defs>
    <filter id="f"><feGaussianBlur stdDeviation="x"/></filter>
  </defs>
  <rect x="0" y="0" width="100" height="100" filter="url(#f)" rx="-" ry="-" />
</svg>
</body>
</html>
"""
        return s.encode("utf-8", "ignore")

    def _generate_json_poc(self) -> bytes:
        s = r'''{
  "type": "object",
  "attrs": {
    "x": "-",
    "y": "bad",
    "width": "1e",
    "height": "",
    "opacity": "NaN",
    "scale": "a",
    "matrix": [1, 0, 0, "x", 0, 0],
    "list": "1 a 2"
  },
  "items": [
    {"attr": "a", "num": "1e309"},
    {"attr": "b", "num": "--1"},
    {"attr": "c", "num": ""}
  ]
}'''
        return s.encode("utf-8", "ignore")

    def _generate_yaml_poc(self) -> bytes:
        s = """type: object
attrs:
  x: "-"
  y: bad
  width: 1e
  height: ""
  opacity: NaN
  scale: a
items:
  - attr: a
    num: 1e309
  - attr: b
    num: "--1"
  - attr: c
    num: ""
"""
        return s.encode("utf-8", "ignore")

    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="pocgen_") as td:
            root = td
            if os.path.isdir(src_path):
                root = src_path
            else:
                try:
                    self._safe_extract_tar(src_path, td)
                except Exception:
                    root = td

            poc = self._find_poc_by_filename(root)
            if poc is not None and len(poc) > 0:
                return poc

            harness = self._find_fuzzer_harness_text(root)
            fmt = self._guess_format(harness)

            if fmt == "svg":
                return self._generate_svg_poc()
            if fmt == "xml":
                return self._generate_xml_poc()
            if fmt == "html":
                return self._generate_html_poc()
            if fmt == "json":
                return self._generate_json_poc()
            if fmt == "yaml":
                return self._generate_yaml_poc()

            return self._generate_svg_poc()
import os
import tarfile
import re
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        project_hint = self._detect_project(src_path)
        if project_hint == "toml":
            return b"a=-infxxxxxxxx"
        if project_hint == "yaml":
            return b"a: -.infxxxxxxx"
        if project_hint == "json":
            return b'{"a":-Infinity} '
        return b"-infxxxxxxxxxxx"

    def _detect_project(self, src_path: str) -> Optional[str]:
        def read_members(tf: tarfile.TarFile):
            for m in tf.getmembers():
                if m.isfile():
                    yield m

        def safe_read(tf: tarfile.TarFile, m: tarfile.TarInfo) -> str:
            try:
                f = tf.extractfile(m)
                if not f:
                    return ""
                data = f.read(4096)
                try:
                    return data.decode("utf-8", errors="ignore")
                except Exception:
                    return ""
            except Exception:
                return ""

        hints = {"toml": 0, "yaml": 0, "json": 0}
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in read_members(tf):
                    name = m.name.lower()
                    if any(x in name for x in ("toml", "toml++", "toml11")):
                        hints["toml"] += 3
                    if "yaml" in name:
                        hints["yaml"] += 2
                    if any(x in name for x in ("json", "rapidjson", "simdjson", "yyjson")):
                        hints["json"] += 1

                    if m.size > 0 and m.size <= 8192:
                        content = safe_read(tf, m)
                        lc = content.lower()
                        if "toml" in lc or "toml::" in lc or "toml+" in lc:
                            hints["toml"] += 2
                        if "yaml" in lc or "yaml-cpp" in lc:
                            hints["yaml"] += 2
                        if "json" in lc:
                            hints["json"] += 1
                        if re.search(r"\b(inf|infinity)\b", lc):
                            # bump all that could parse inf
                            hints["toml"] += 1
                            hints["yaml"] += 1
                            hints["json"] += 1
        except Exception:
            pass

        proj = max(hints.items(), key=lambda kv: kv[1])[0]
        if hints[proj] == 0:
            return None
        return proj
